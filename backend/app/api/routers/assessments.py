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

# ----------------- ASSESSMENTS -----------------

@router.get("/assessments/attempt/{app_id}", response_model=schemas.AssessmentResponse)
def get_assigned_assessment(app_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    assess = db.query(Assessment).filter(Assessment.job_id == app.job_id).first()
    if not assess:
        raise HTTPException(status_code=404, detail="No assessment assigned yet")
    return assess

@router.post("/assessments/attempt/{app_id}/submit")
async def submit_assessment(app_id: int, attempt_in: schemas.AssessmentAttemptCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    assess = db.query(Assessment).filter(Assessment.job_id == app.job_id).first()
    attempt = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.application_id == app_id, 
        AssessmentAttempt.assessment_id == assess.id
    ).first()
    
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt session not registered")
        
    attempt.answers = attempt_in.answers
    db.commit()
    
    # Trigger Evaluation
    await orchestrator.run_assessment_evaluation_agent(db, attempt.id)
    return {"message": "Assessment submitted successfully", "score": attempt.score, "passed": attempt.passed}

@router.post("/assessments/proctor/log/{app_id}")
async def log_proctoring_event(app_id: int, fraud_in: schemas.FraudLogCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    assess = db.query(Assessment).filter(Assessment.job_id == app.job_id).first()
    attempt = db.query(AssessmentAttempt).filter(
        AssessmentAttempt.application_id == app_id, 
        AssessmentAttempt.assessment_id == assess.id
    ).first()
    
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not active")
        
    f_log = FraudLog(
        attempt_id=attempt.id,
        event_type=fraud_in.event_type,
        details=fraud_in.details,
        fraud_score=fraud_in.fraud_score or 0.0
    )
    db.add(f_log)
    db.commit()
    
    # Push WS update to admins
    await manager.broadcast_to_admins({
        "type": "proctor_alert",
        "data": {
            "application_id": app_id,
            "candidate_name": current_user.full_name,
            "event_type": fraud_in.event_type,
            "details": fraud_in.details,
            "timestamp": str(datetime.utcnow())
        }
    })
    return {"status": "logged"}


