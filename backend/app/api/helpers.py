from fastapi import APIRouter
router = APIRouter()
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, get_current_admin
)
from app.core.ws import manager
from app.models.models import (
    User, Candidate, CandidateResume, CandidateProfile,
    Notification, AuditLog, EmailNotification, Message,
    CourseProgress, LearningEvent,
    VideoAnalytics, CourseAnalytics, OTP,
    AIMentorSession, AIMentorMessage, AIMentorStudyPlan, AIMentorInsight, AIMentorArtifact, AIMentorUsage, UserCareerProfile, UserConsent,
    MCPChatSession, MCPChatMessage
)
from fastapi.responses import StreamingResponse
from app.services.mentor_profile import (
    get_learning_health, get_risk_analysis, get_smart_recommendations, trigger_background_insights
)
from app.services.mentor_cache import (
    get_cached_mentor_profile, set_cached_mentor_profile, invalidate_mentor_profile
)

logger = logging.getLogger(__name__)
from app.schemas import schemas
from app.services.orchestrator import orchestrator, call_nvidia, call_gemini
from app.services.storage import storage_service

router = APIRouter()

# Per-user resume upload rate limiting: {user_id: [timestamp, ...]}
# Max 3 resume uploads per hour per user
import time as _time
_RESUME_UPLOAD_TIMESTAMPS: dict = {}
_RESUME_UPLOAD_MAX = 3
_RESUME_UPLOAD_WINDOW = 3600  # 1 hour in seconds

def _check_resume_upload_rate_limit(user_id: int) -> None:
    """Raises HTTPException(429) if the user has exceeded the upload rate limit."""
    now = _time.time()
    window_start = now - _RESUME_UPLOAD_WINDOW
    timestamps = _RESUME_UPLOAD_TIMESTAMPS.get(user_id, [])
    timestamps = [ts for ts in timestamps if ts > window_start]
    if len(timestamps) >= _RESUME_UPLOAD_MAX:
        oldest = timestamps[0]
        retry_in = int(_RESUME_UPLOAD_WINDOW - (now - oldest))
        raise HTTPException(
            status_code=429,
            detail=f"Resume upload rate limit exceeded. You can upload at most {_RESUME_UPLOAD_MAX} resumes per hour. Please retry in {retry_in // 60} min {retry_in % 60} sec."
        )
    timestamps.append(now)
    _RESUME_UPLOAD_TIMESTAMPS[user_id] = timestamps


def parse_candidate_experience_level(candidate) -> str:
    if not candidate:
        return "Mid-Level"
    skills_text = (candidate.skills or "").lower()
    summary_text = (candidate.summary or "").lower()
    exp_text = (candidate.experience or "").lower()

    full_text = f"{skills_text} {summary_text} {exp_text}"

    import re
    match = re.search(r'(\d+)\+?\s*(?:years|yrs)\b', full_text, re.IGNORECASE)
    years = 0
    if match:
        years = int(match.group(1))
    else:
        try:
            exp_list = json.loads(candidate.experience) if candidate.experience else []
            if isinstance(exp_list, list):
                years = len(exp_list) * 2
        except Exception:
            pass

    if years >= 5 or any(k in full_text for k in ["senior", "lead", "principal", "manager", "architect"]):
        return "Senior"
    elif years >= 2 or "mid" in full_text or "associate" in full_text:
        return "Mid-Level"
    else:
        return "Entry-Level"
