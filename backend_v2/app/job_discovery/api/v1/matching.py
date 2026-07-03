"""
VidyaMarg AI — FastAPI Matching & Recommendation Endpoints
==========================================================
These Tool APIs allow Tush AI to access recommendations and matches
for a given candidate without any direct DB access.

Endpoints:
  POST /api/v1/matching/{candidate_id}/recommendations  — Get top recommendations
  GET  /api/v1/matching/{candidate_id}/matches          — Get all matches
  POST /api/v1/matching/{candidate_id}/find-remote-jobs — Remote-optimized search
  POST /api/v1/matching/{candidate_id}/find-salary-jobs — Salary-range search
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.job_discovery.api.dependency import get_db_session, verify_api_key
from app.job_discovery.infrastructure.database.models import (
    CandidateMatchORM,
    RecommendationORM,
)
from app.job_discovery.infrastructure.database.repository import (
    MatchRepository,
    RecommendationRepository,
)

logger = logging.getLogger("jd.api.matching")
router = APIRouter(prefix="/matching", tags=["Matching & Recommendations Tool API"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MatchResult(BaseModel):
    match_id: int
    job_id: int
    overall_score: float
    semantic_score: float
    skill_score: float
    match_reasons: List[str]
    missing_skills: List[str]
    skill_gap_severity: str
    status: str


class RecommendationResult(BaseModel):
    recommendation_id: int
    job_id: int
    score: float
    reason: Optional[str]
    is_seen: bool
    is_actioned: bool
    match_details: Optional[MatchResult] = None


class RecommendationResponse(BaseModel):
    candidate_id: int
    total: int
    recommendations: List[RecommendationResult]


class SalarySearchRequest(BaseModel):
    candidate_id: int
    salary_min: float = Field(..., description="Minimum desired salary")
    salary_max: Optional[float] = Field(default=None)
    currency: str = Field(default="INR")
    limit: int = Field(default=10, ge=1, le=50)


class RemoteJobSearchRequest(BaseModel):
    candidate_id: int
    skills: List[str] = Field(default=[])
    limit: int = Field(default=10, ge=1, le=50)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _match_to_schema(m: CandidateMatchORM) -> MatchResult:
    return MatchResult(
        match_id=m.id,
        job_id=m.job_id,
        overall_score=m.overall_score,
        semantic_score=m.semantic_score,
        skill_score=m.skill_score,
        match_reasons=m.match_reasons or [],
        missing_skills=m.missing_skills or [],
        skill_gap_severity=m.skill_gap_severity or "none",
        status=m.status,
    )


def _rec_to_schema(r: RecommendationORM) -> RecommendationResult:
    return RecommendationResult(
        recommendation_id=r.id,
        job_id=r.job_id,
        score=r.score,
        reason=r.reason,
        is_seen=r.is_seen,
        is_actioned=r.is_actioned,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{candidate_id}/recommendations",
    response_model=RecommendationResponse,
    summary="Get personalized job recommendations (Tush AI Tool)",
    description=(
        "Returns AI-generated job recommendations ranked by match score. "
        "Tush AI calls this to present jobs to candidates."
    ),
)
async def get_recommendations(
    candidate_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    _: str = Depends(verify_api_key),
    session=Depends(get_db_session),
) -> RecommendationResponse:
    """Retrieves top unseen recommendations for a candidate."""
    rec_repo = RecommendationRepository(session)
    recs = await rec_repo.get_unseen(candidate_id=candidate_id, limit=limit)

    if not recs:
        # Trigger async generation if none exist
        try:
            from app.job_discovery.workers.recommendation import generate_recommendations
            generate_recommendations.delay(candidate_id=candidate_id)
        except Exception as exc:
            logger.warning(f"Could not trigger recommendation generation: {exc}")

    return RecommendationResponse(
        candidate_id=candidate_id,
        total=len(recs),
        recommendations=[_rec_to_schema(r) for r in recs],
    )


@router.get(
    "/{candidate_id}/matches",
    response_model=List[MatchResult],
    summary="Get all job matches for a candidate",
)
async def get_matches(
    candidate_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    _: str = Depends(verify_api_key),
    session=Depends(get_db_session),
) -> List[MatchResult]:
    """Returns all candidate-job matches sorted by overall score."""
    match_repo = MatchRepository(session)
    matches = await match_repo.get_top_matches(candidate_id=candidate_id, limit=limit)
    return [_match_to_schema(m) for m in matches]


@router.post(
    "/find-remote-jobs",
    summary="Find remote-only jobs (Tush AI Tool: find_remote_jobs)",
    description="Searches exclusively for remote/distributed jobs matching candidate skills.",
)
async def find_remote_jobs(
    request: RemoteJobSearchRequest,
    _: str = Depends(verify_api_key),
    session=Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Tush AI Tool: find_remote_jobs()
    Returns active remote jobs filtered by candidate skills.
    """
    from app.job_discovery.infrastructure.database.repository import JobRepository
    job_repo = JobRepository(session)
    jobs = await job_repo.get_active_jobs(
        limit=request.limit,
        filters={"is_remote": True},
    )
    results = []
    for job in jobs:
        # Skill overlap filter
        if request.skills:
            job_skills = set((job.required_skills or []) + (job.preferred_skills or []))
            if not any(s.lower() in job_skills for s in request.skills):
                continue
        results.append({
            "job_id": job.id,
            "title": job.title,
            "company_name": job.company_name,
            "location": "Remote",
            "apply_url": job.apply_url,
            "required_skills": job.required_skills or [],
        })

    return {
        "candidate_id": request.candidate_id,
        "total": len(results),
        "jobs": results[:request.limit],
    }


@router.post(
    "/find-salary-jobs",
    summary="Find jobs by salary range (Tush AI Tool: find_salary_jobs)",
    description="Searches jobs within a specified salary range.",
)
async def find_salary_jobs(
    request: SalarySearchRequest,
    _: str = Depends(verify_api_key),
    session=Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Tush AI Tool: find_salary_jobs()
    Returns jobs whose salary_min is at or above the candidate's minimum expectation.
    """
    from app.job_discovery.infrastructure.database.repository import JobRepository
    job_repo = JobRepository(session)
    jobs = await job_repo.get_active_jobs(
        limit=request.limit,
        filters={"salary_min": request.salary_min},
    )
    results = [
        {
            "job_id": job.id,
            "title": job.title,
            "company_name": job.company_name,
            "salary_range": f"{job.salary_currency} {job.salary_min or 0:,.0f} - {job.salary_max or 0:,.0f}",
            "location": job.location,
            "apply_url": job.apply_url,
        }
        for job in jobs
        if job.salary_min and job.salary_min >= request.salary_min
    ]

    return {
        "candidate_id": request.candidate_id,
        "salary_filter": f"{request.currency} {request.salary_min:,.0f}",
        "total": len(results),
        "jobs": results,
    }
