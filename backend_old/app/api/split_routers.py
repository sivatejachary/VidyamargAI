import os

def split():
    endpoints_path = "backend/app/api/endpoints.py"
    routers_dir = "backend/app/api/routers"
    
    # 1. Create routers directory
    os.makedirs(routers_dir, exist_ok=True)
    with open(os.path.join(routers_dir, "__init__.py"), "w") as f:
        pass

    # 2. Read endpoints.py lines
    with open(endpoints_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    def find_line(pattern, start_from=0):
        for idx in range(start_from, len(lines)):
            if pattern in lines[idx]:
                return idx
        return -1

    # 3. Dynamic header detection
    test_resend_start = find_line('@router.get("/auth/test-resend-directly")')
    test_resend_end = find_line('# Import new real-time job services')
    
    h_auth = find_line("# ----------------- AUTHENTICATION -----------------")
    h_auth_helpers = find_line("def parse_date", h_auth)
    if h_auth_helpers == -1:
        h_auth_helpers = find_line("def calculate_years_from_experience", h_auth)
        
    h_jobs = find_line("# ----------------- JOBS -----------------")
    h_profile = find_line("# ----------------- CANDIDATE PROFILE & RESUME -----------------")
    h_resume = find_line('@router.post("/candidates/resume")', h_profile)
    h_apps = find_line("# ----------------- APPLICATIONS & PIPELINE -----------------")
    h_assessments = find_line("# ----------------- ASSESSMENTS -----------------")
    h_interviews = find_line("# ----------------- TARA AI INTERVIEWS -----------------")
    h_offers = find_line("# ----------------- OFFERS & ONBOARDING -----------------")
    h_admin = find_line("# ----------------- ADMIN DASHBOARD & RANKINGS -----------------")
    h_notifications = find_line("# ----------------- NOTIFICATIONS -----------------")
    h_storage = find_line("# ----------------- STORAGE SERVING & LISTING -----------------")
    h_copilot = find_line("# ----------------- AI CAREER COPILOT (NVIDIA/GEMINI) -----------------")
    h_haq = find_line("# ─────────────── HUMAN ACTION QUEUE ───────────────")
    h_activity = find_line("# ─────────────── AGENT ACTIVITY FEED ───────────────")
    h_messages = find_line("# ----------------- MESSAGES & LIVE CHAT -----------------")
    h_learning = find_line("# ----------------- SKILL LAB COURSES & LMS ENDPOINTS -----------------")
    h_upgraded_lms = find_line("# ----------------- UPGRADED LMS & ANALYTICS ENDPOINTS -----------------")
    
    h_mentor_start = find_line("def generate_study_plan_background", h_upgraded_lms) - 4

    # 4. Write helpers.py
    helpers_lines = lines[0 : test_resend_start] + lines[test_resend_end : h_auth] + lines[h_auth_helpers : h_jobs]
    helpers_content = "".join(helpers_lines)
    helpers_content = "from fastapi import APIRouter\nrouter = APIRouter()\n" + helpers_content
    
    with open("backend/app/api/helpers.py", "w", encoding="utf-8") as f:
        f.write(helpers_content)

    # 5. Extract test_resend_directly code for auth.py
    test_resend_code = "".join(lines[test_resend_start : test_resend_end])

    # Helper to generate subfile content
    def make_router_file(filename, file_lines):
        header = """from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
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
"""
        content = header + "\n" + "".join(file_lines)
        with open(os.path.join(routers_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)

    # 6. Construct chunks using dynamic boundaries
    router_chunks = {
        "auth.py": [test_resend_code, "".join(lines[h_auth : h_auth_helpers])],
        "jobs.py": ["".join(lines[h_jobs : h_profile])],
        "profile.py": ["".join(lines[h_profile : h_resume])],
        "resume.py": ["".join(lines[h_resume : h_apps])],
        "matching.py": ["".join(lines[h_apps : h_assessments])],
        "assessments.py": ["".join(lines[h_assessments : h_interviews])],
        "interview.py": ["".join(lines[h_interviews : h_offers])],
        "offers.py": ["".join(lines[h_offers : h_admin])],
        "admin.py": ["".join(lines[h_admin : h_notifications]), "".join(lines[h_storage : h_copilot])],
        "notifications.py": ["".join(lines[h_notifications : h_storage]), "".join(lines[h_activity : h_messages])],
        "chat.py": ["".join(lines[h_copilot : h_haq]), "".join(lines[h_messages : h_learning])],
        "haq.py": ["".join(lines[h_haq : h_activity])],
        "learning.py": ["".join(lines[h_learning : h_mentor_start])],
        "mentor.py": ["".join(lines[h_mentor_start :])]
    }

    for filename, chunks in router_chunks.items():
        make_router_file(filename, chunks)

    # 7. Replace endpoints.py with clean router registrations
    endpoints_new_content = """from fastapi import APIRouter
from app.api.routers import (
    auth, profile, resume, jobs, matching, learning, mentor,
    chat, interview, assessments, notifications, admin, offers, haq
)

# Backward compatibility exports
from app.api.helpers import (
    _LIVE_JOB_STORE,
    calculate_years_from_experience,
    extract_and_seed_external_jobs,
    _build_curriculum_payload
)

router = APIRouter()

router.include_router(auth.router)
router.include_router(profile.router)
router.include_router(resume.router)
router.include_router(jobs.router)
router.include_router(matching.router)
router.include_router(learning.router)
router.include_router(mentor.router)
router.include_router(chat.router)
router.include_router(interview.router)
router.include_router(assessments.router)
router.include_router(notifications.router)
router.include_router(admin.router)
router.include_router(offers.router)
router.include_router(haq.router)
"""
    with open(endpoints_path, "w", encoding="utf-8") as f:
        f.write(endpoints_new_content)

    print("Dynamic endpoints split completed successfully!")

if __name__ == "__main__":
    split()
