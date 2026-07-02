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

logger = logging.getLogger(__name__)

router = APIRouter()

# ----------------- NOTIFICATIONS -----------------

@router.get("/notifications", response_model=List[schemas.NotificationResponse])
def get_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).all()

@router.put("/notifications/{notif_id}/read")
def read_notification(notif_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read = True
    db.commit()
    return {"status": "updated"}


# ----------------- EMAIL NOTIFICATIONS -----------------

@router.get("/candidates/emails", response_model=List[schemas.EmailNotificationResponse])
def get_candidate_emails(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Find candidate associated with this user
    cand = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not cand:
        return []
    return db.query(EmailNotification).filter(EmailNotification.candidate_id == cand.id).order_by(EmailNotification.sent_at.desc()).all()

@router.put("/candidates/emails/{email_id}/read")
def read_candidate_email(email_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cand = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    email_notif = db.query(EmailNotification).filter(EmailNotification.id == email_id, EmailNotification.candidate_id == cand.id).first()
    if not email_notif:
        raise HTTPException(status_code=404, detail="Email notification not found")
        
    email_notif.read = True
    db.commit()
    return {"status": "updated"}


# ─────────────── AGENT ACTIVITY FEED ───────────────

@router.get("/agent/activity")
async def get_agent_activity(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns the agent activity feed for the current user."""
    from app.services.agent_activity_feed import get_feed
    return get_feed(current_user.id, limit, db)

