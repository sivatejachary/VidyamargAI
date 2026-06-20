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

# ----------------- APPLICATIONS & PIPELINE -----------------

@router.post("/applications")
async def apply_to_job(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
        
    resumes = db.query(CandidateResume).filter(CandidateResume.candidate_id == candidate.id).all()
    if not resumes:
        raise HTTPException(status_code=400, detail="Please upload your resume before applying")
        
    active_resume = resumes[-1]
    
    # Intercept dynamic live jobs (IDs >= 10000) and persist to database on apply
    if job_id >= 10000:
        if job_id not in LIVE_JOBS_CACHE:
            raise HTTPException(status_code=404, detail="Job posting expired. Please refresh the page.")
        
        j_data = LIVE_JOBS_CACHE[job_id]
        
        # Check if already in DB
        existing_job = db.query(Job).filter(
            Job.title == j_data["title"],
            Job.department == j_data["department"]
        ).first()
        
        if not existing_job:
            new_job = Job(
                title=j_data["title"],
                description=j_data["description"],
                required_skills=j_data["required_skills"],
                experience_level=j_data["experience_level"],
                salary_range=j_data["salary_range"],
                location=j_data["location"],
                department=j_data["department"],
                status="active"
            )
            db.add(new_job)
            db.commit()
            db.refresh(new_job)
            persisted_job_id = new_job.id
        else:
            persisted_job_id = existing_job.id
            
        job_id = persisted_job_id
    
    # Check if duplicate application
    existing = db.query(Application).filter(Application.candidate_id == candidate.id, Application.job_id == job_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already applied to this job")
        
    app = Application(
        candidate_id=candidate.id,
        job_id=job_id,
        resume_id=active_resume.id,
        status="screening"
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    
    candidate.status = "Applied - Screening"
    candidate.current_step = "Screening"
    db.commit()
    
    # Trigger Screening Agent
    await orchestrator.run_resume_screening_agent(db, app.id)
    
    return {"message": "Application submitted", "application_id": app.id, "status": app.status}

@router.get("/applications", response_model=List[schemas.ApplicationResponse])
def get_applications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role in ["admin", "super_admin"]:
        return db.query(Application).all()
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        return []
    return db.query(Application).filter(Application.candidate_id == candidate.id).all()


