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

# ----------------- TARA AI INTERVIEWS -----------------

@router.get("/interviews/{app_id}", response_model=schemas.InterviewResponse)
def get_interview_session(app_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    interview = db.query(Interview).filter(Interview.application_id == app_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not scheduled yet")
    return interview

@router.post("/interviews/{interview_id}/answer")
async def answer_interview_question(interview_id: int, qa: schemas.InterviewQuestionAnswer, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    next_action = await orchestrator.run_tara_interview_agent(db, interview_id, qa.answer)
    return {"next_question": next_action}

@router.get("/interviews/{interview_id}/analysis", response_model=schemas.InterviewResultResponse)
def get_interview_analysis(interview_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = db.query(InterviewResult).filter(InterviewResult.interview_id == interview_id).first()
    if not res:
        raise HTTPException(status_code=404, detail="Analysis reports are pending")
    return res


