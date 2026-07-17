import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from .schemas import ProfileResponse, CandidateCreate, CandidateResponse
from .service import CandidateService
from .repository import CandidateRepository
from packages.core_lib.database import DatabaseManager

logger = logging.getLogger("services.candidate_service.app.router")

# Router definitions
router = APIRouter(prefix="/candidates", tags=["candidates"])

# Dependency inject placeholder
import os
raw_db_url = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:CDVByqTUKjxAlWjBkyOIjXTAlcAaakUf@hayabusa.proxy.rlwy.net:42919/railway"
)
if raw_db_url.startswith("postgresql://"):
    db_url = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    db_url = raw_db_url
db_manager = DatabaseManager(database_url=db_url)

async def get_db() -> AsyncSession:
    async for session in db_manager.get_session():
        yield session

@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate_account(
    payload: CandidateCreate,
    db: AsyncSession = Depends(get_db)
):
    """Exposes REST endpoint to initialize candidate credentials."""
    repo = CandidateRepository(db)
    existing = await repo.get_candidate_by_id(payload.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate account already exists."
        )
    candidate = await repo.create_candidate(payload.id, payload.name, payload.email)
    return candidate

@router.get("/profile/{candidate_id}", response_model=ProfileResponse)
async def get_candidate_profile(
    candidate_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Exposes REST endpoint to retrieve parsed profile details."""
    repo = CandidateRepository(db)
    profile = await repo.get_profile_by_candidate_id(candidate_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile record not found."
        )
    
    return ProfileResponse(
        id=profile.id,
        candidate_id=profile.candidate_id,
        summary=profile.summary,
        skills_graph=profile.skills_graph,
        experience_graph=profile.experience_graph,
        education_graph=profile.education_graph,
        created_at=profile.created_at
    )
