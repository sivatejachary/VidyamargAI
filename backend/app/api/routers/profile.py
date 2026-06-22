from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.orm import Session, joinedload
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

# ----------------- CANDIDATE PROFILE & RESUME -----------------

@router.get("/candidates/profile", response_model=schemas.CandidateResponse)
def get_candidate_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    candidate = db.query(Candidate).options(joinedload(Candidate.user)).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    
    # Attach experience_years from CandidateProfile
    profile = db.query(CandidateProfile).filter(CandidateProfile.candidate_id == candidate.id).order_by(CandidateProfile.created_at.desc()).first()
    candidate.experience_years = profile.experience_years if profile else 0.0
    return candidate

@router.put("/candidates/profile", response_model=schemas.CandidateResponse)
async def update_candidate_profile(
    profile_in: schemas.CandidateProfileUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).options(joinedload(Candidate.user)).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    for k, v in profile_in.dict(exclude_unset=True).items():
        setattr(candidate, k, v)
        
    if profile_in.parsed_name is not None and candidate.user:
        candidate.user.full_name = profile_in.parsed_name
        
    candidate.status = "Profile Completed"
    candidate.current_step = "Resume"
    db.commit()
    
    # Rebuild candidate profile to update experience_years, domain, etc.
    try:
        from app.services.orchestrator import orchestrator
        await orchestrator.rebuild_candidate_profile_data(db, candidate)
    except Exception as e:
        logger.error(f"Failed to rebuild profile after update: {e}")
        
    # Clear existing matches and trigger async recalculation of matches to prevent stale scores
    try:
        from app.models.pool_models import JobPoolMatch
        db.query(JobPoolMatch).filter(JobPoolMatch.candidate_id == candidate.id).delete()
        db.commit()

        async def run_matching_bg(cand_id: int):
            from app.core.database import SessionLocal
            from app.workers.discovery_worker import match_pool_jobs_for_candidate
            db_session = SessionLocal()
            try:
                cand = db_session.query(Candidate).filter(Candidate.id == cand_id).first()
                if cand:
                    skills_list = [s.strip() for s in (cand.skills or "").split(",") if s.strip()]
                    await match_pool_jobs_for_candidate(cand, db_session, skills_list)
            except Exception as bg_match_err:
                logger.error(f"Background profile match recalculation failed: {bg_match_err}")
            finally:
                db_session.close()

        background_tasks.add_task(run_matching_bg, candidate.id)
        logger.info(f"Enqueued background match recalculation for candidate {candidate.id}")
    except Exception as match_err:
        logger.error(f"Failed to trigger matching recalculation after profile update: {match_err}")

    from app.services.resume_cache import invalidate_resume_analysis
    invalidate_resume_analysis(candidate.id)
    try:
        from app.services.mentor_cache import invalidate_mentor_profile
        invalidate_mentor_profile(candidate.user_id)
        logger.info(f"Invalidated AI Mentor profile cache for user {candidate.user_id}")
    except Exception as cache_err:
        logger.warning(f"Failed to invalidate AI Mentor profile cache: {cache_err}")
    db.refresh(candidate)
    
    # Attach experience_years from CandidateProfile
    profile = db.query(CandidateProfile).filter(CandidateProfile.candidate_id == candidate.id).order_by(CandidateProfile.created_at.desc()).first()
    candidate.experience_years = profile.experience_years if profile else 0.0
    return candidate

