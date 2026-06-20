from fastapi import APIRouter
from app.api.routers import (
    auth, profile, resume, jobs, matching, learning, mentor,
    chat, interview, assessments, notifications, admin, offers, haq, auto_apply
)

# Backward compatibility exports
from app.api.helpers import _LIVE_JOB_STORE
from app.api.routers.jobs import (
    calculate_years_from_experience,
    extract_and_seed_external_jobs
)
from app.api.routers.learning import _build_curriculum_payload
from app.api.routers.mentor import call_llm_with_fallback
from app.api.routers.resume import delete_candidate_resume



router = APIRouter()

router.include_router(auth.router)
router.include_router(auto_apply.router)
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
