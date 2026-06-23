from fastapi import APIRouter
from app.api.routers import (
    auth, profile, resume, learning, mentor,
    chat, notifications, admin
)

# Backward compatibility exports
from app.api.routers.learning import _build_curriculum_payload
from app.api.routers.mentor import call_llm_with_fallback
from app.api.routers.resume import delete_candidate_resume

router = APIRouter()

router.include_router(auth.router)
router.include_router(profile.router)
router.include_router(resume.router)
router.include_router(learning.router)
router.include_router(mentor.router)
router.include_router(chat.router)
router.include_router(notifications.router)
router.include_router(admin.router)
