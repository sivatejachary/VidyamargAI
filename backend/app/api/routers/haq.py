from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union, Tuple
from datetime import datetime, timedelta
import json
import logging
import os
import uuid
import time
import asyncio

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user, get_current_admin
from app.schemas import schemas
from app.models.models import *

from app.api.helpers import *
from app.api.helpers import _check_resume_upload_rate_limit, _LIVE_JOB_STORE, _RESUME_UPLOAD_TIMESTAMPS

logger = logging.getLogger(__name__)

router = APIRouter()

# ─────────────── HUMAN ACTION QUEUE ───────────────

@router.get("/haq/pending")
async def get_pending_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns all pending Human Action Queue items for the current user."""
    from app.services.human_action_queue import haq_service
    items = haq_service.get_pending(current_user.id, db)
    return [
        {
            "id": item.id,
            "action_type": item.action_type,
            "title": item.title,
            "description": item.description,
            "status": item.status,
            "callback_key": item.callback_key,
            "created_at": item.created_at.isoformat(),
            "expires_at": item.expires_at.isoformat() if item.expires_at else None,
        }
        for item in items
    ]


@router.post("/haq/{callback_key}/complete")
async def complete_haq_item(
    callback_key: str,
    payload: dict = {},
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """User completes a required action (OTP, CAPTCHA, etc)."""
    from app.services.human_action_queue import haq_service
    item = haq_service.complete(callback_key, payload, db)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    return {"status": "completed", "callback_key": callback_key}


@router.post("/haq/{callback_key}/dismiss")
async def dismiss_haq_item(
    callback_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """User dismisses a pending action."""
    from app.services.human_action_queue import haq_service
    item = haq_service.dismiss(callback_key, db)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    return {"status": "dismissed", "callback_key": callback_key}


# ─────────────── AUTO APPLY PIPELINE ───────────────

@router.post("/candidate/agent/auto-apply/{job_id}")
async def auto_apply_job_endpoint(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Queues an autonomous application for a specific job."""
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
        
    db_job_id = ensure_job_in_db(db, job_id, create_if_missing=True)
    if not db_job_id:
         raise HTTPException(status_code=404, detail="Job not found")
         
    # Check if application already exists
    app = db.query(Application).filter(
        Application.candidate_id == candidate.id,
        Application.job_id == db_job_id
    ).first()
    
    # Get latest resume version
    resumes = db.query(CandidateResume).filter(
        CandidateResume.candidate_id == candidate.id
    ).order_by(CandidateResume.uploaded_at.desc()).all()
    
    resume_id = resumes[0].id if resumes else None
    
    if not app:
        app = Application(
            candidate_id=candidate.id,
            job_id=db_job_id,
            resume_id=resume_id,
            status="queued"
        )
        db.add(app)
        db.commit()
        db.refresh(app)
    else:
        # If already applied or in progress
        if app.status in ("queued", "applying", "applied"):
            return {"status": app.status, "message": f"Application status: {app.status}"}
        # Reset status to queued
        app.status = "queued"
        app.resume_id = resume_id
        db.commit()
        
    from app.core.queue import enqueue_auto_apply
    try:
        enqueue_auto_apply(candidate.id, db_job_id)
    except Exception as e:
        app.status = "failed"
        db.commit()
        raise HTTPException(status_code=503, detail=str(e))
        
    return {"status": "queued", "message": "Auto-apply task enqueued successfully"}


@router.get("/candidate/agent/auto-apply/status/{job_id}")
async def get_auto_apply_status_endpoint(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves status of an auto-apply task for a specific job."""
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
        
    db_job_id = ensure_job_in_db(db, job_id, create_if_missing=False)
    if not db_job_id:
        return {"status": "not_started", "message": "No application has been initiated for this job."}
        
    app = db.query(Application).filter(
        Application.candidate_id == candidate.id,
        Application.job_id == db_job_id
    ).first()
    
    if not app:
        return {"status": "not_started", "message": "No application has been initiated for this job."}
        
    return {
        "status": app.status,
        "message": f"Job application status is '{app.status}'."
    }


