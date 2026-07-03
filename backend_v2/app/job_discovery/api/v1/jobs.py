"""
VidyaMarg AI — FastAPI Tool API Endpoints (Jobs)
=================================================
These are the ONLY endpoints through which Tush AI accesses job data.
Zero direct database access from the AI OS — everything flows through here.

Endpoints:
  POST /api/v1/jobs/search    — Semantic + filtered job search
  GET  /api/v1/jobs/{job_id}  — Full job details
  GET  /api/v1/jobs/          — Paginated job listing with filters
  POST /api/v1/jobs/discover  — Manual trigger for discovery run
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.job_discovery import config as cfg
from app.job_discovery.api.dependency import (
    get_db_session,
    get_qdrant,
    verify_api_key,
)
from app.job_discovery.infrastructure.database.models import JobORM
from app.job_discovery.infrastructure.database.repository import JobRepository
from app.job_discovery.infrastructure.database.session import get_async_session
from app.job_discovery.infrastructure.qdrant.client import QdrantVectorStore

logger = logging.getLogger("jd.api.jobs")
router = APIRouter(prefix="/jobs", tags=["Jobs Tool API"])


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class JobSearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query", example="Senior Python Backend Engineer with FastAPI")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Structured metadata filters")
    limit: int = Field(default=10, ge=1, le=50)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Senior Software Architect with FastAPI and Kubernetes",
                "filters": {"location": "Bangalore", "is_remote": True, "salary_min": 2500000},
                "limit": 10,
            }
        }


class JobSummary(BaseModel):
    job_id: int
    title: str
    company_name: str
    location: Optional[str]
    is_remote: bool
    seniority: Optional[str]
    salary_min: Optional[float]
    salary_max: Optional[float]
    salary_currency: str
    apply_url: Optional[str]
    match_score: Optional[float] = None
    posted_at: Optional[str]
    source_name: Optional[str]


class JobDetail(JobSummary):
    description: Optional[str]
    description_summary: Optional[str]
    required_skills: List[str]
    preferred_skills: List[str]
    experience_min_years: Optional[float]
    experience_max_years: Optional[float]
    role_category: Optional[str]
    employment_type: Optional[str]
    trust_score: float
    quality_score: float
    lifecycle_status: str
    discovered_at: str


class SearchResponse(BaseModel):
    status: str = "success"
    query: str
    total: int
    results: List[JobSummary]


class DiscoverRequest(BaseModel):
    roles: List[str] = Field(default=["software engineer"])
    locations: List[str] = Field(default=["India", "Remote"])
    skills: List[str] = Field(default=["python"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _job_to_summary(job: JobORM, score: Optional[float] = None) -> JobSummary:
    return JobSummary(
        job_id=job.id,
        title=job.title,
        company_name=job.company_name,
        location=job.location,
        is_remote=job.is_remote,
        seniority=job.seniority,
        salary_min=float(job.salary_min) if job.salary_min else None,
        salary_max=float(job.salary_max) if job.salary_max else None,
        salary_currency=job.salary_currency or "INR",
        apply_url=job.apply_url,
        match_score=round(score * 100, 1) if score else None,
        posted_at=job.posted_at.isoformat() if job.posted_at else None,
        source_name=job.source.name if job.source else None,
    )


def _job_to_detail(job: JobORM) -> JobDetail:
    return JobDetail(
        job_id=job.id,
        title=job.title,
        company_name=job.company_name,
        location=job.location,
        is_remote=job.is_remote,
        seniority=job.seniority,
        salary_min=float(job.salary_min) if job.salary_min else None,
        salary_max=float(job.salary_max) if job.salary_max else None,
        salary_currency=job.salary_currency or "INR",
        apply_url=job.apply_url,
        posted_at=job.posted_at.isoformat() if job.posted_at else None,
        source_name=job.source.name if job.source else None,
        description=job.description,
        description_summary=job.description_summary,
        required_skills=job.required_skills or [],
        preferred_skills=job.preferred_skills or [],
        experience_min_years=job.experience_min_years,
        experience_max_years=job.experience_max_years,
        role_category=job.role_category,
        employment_type=job.employment_type,
        trust_score=job.trust_score or 0.5,
        quality_score=job.quality_score or 0.5,
        lifecycle_status=job.lifecycle_status or "unknown",
        discovered_at=job.discovered_at.isoformat() if job.discovered_at else "",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Semantic job search (Tush AI Tool)",
    description=(
        "Performs hybrid semantic + metadata-filtered job search. "
        "Used exclusively by Tush AI — never call the database directly."
    ),
)
async def search_jobs(
    request: JobSearchRequest,
    _: str = Depends(verify_api_key),
    qdrant: QdrantVectorStore = Depends(get_qdrant),
    session=Depends(get_db_session),
) -> SearchResponse:
    """
    Semantic job search via Qdrant + PostgreSQL metadata filters.
    Falls back to keyword search if Qdrant is unavailable.
    """
    job_repo = JobRepository(session)
    results: List[JobSummary] = []

    try:
        # Generate query embedding
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=cfg.OPENAI_API_KEY)
        embed_response = await client.embeddings.create(
            model=cfg.EMBEDDING_MODEL,
            input=[request.query],
        )
        query_vector = embed_response.data[0].embedding

        # Semantic search in Qdrant
        vector_results = await qdrant.similarity_search(
            query_vector=query_vector,
            limit=request.limit * 2,
            score_threshold=0.55,
            filters=request.filters,
        )

        # Fetch full job details from PostgreSQL
        job_ids = [int(point_id) for point_id, _, _ in vector_results if str(point_id).isdigit()]
        score_map = {int(point_id): score for point_id, score, _ in vector_results}

        for job_id in job_ids[: request.limit]:
            job = await job_repo.get_by_id(job_id)
            if job and job.is_active:
                results.append(_job_to_summary(job, score_map.get(job_id)))

    except Exception as exc:
        logger.warning(f"Vector search failed ({exc}), falling back to DB keyword search")
        # Fallback: keyword search in PostgreSQL
        db_jobs = await job_repo.get_active_jobs(limit=request.limit, filters=request.filters)
        results = [_job_to_summary(j) for j in db_jobs]

    return SearchResponse(
        query=request.query,
        total=len(results),
        results=results,
    )


@router.get(
    "/{job_id}",
    response_model=JobDetail,
    summary="Get full job details (Tush AI Tool)",
)
async def get_job_details(
    job_id: int,
    _: str = Depends(verify_api_key),
    session=Depends(get_db_session),
) -> JobDetail:
    """Returns complete job record including description, skills, and quality scores."""
    job_repo = JobRepository(session)
    job = await job_repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found")
    return _job_to_detail(job)


@router.get(
    "/",
    response_model=SearchResponse,
    summary="List active jobs with filters",
)
async def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    country: Optional[str] = Query(default=None),
    is_remote: Optional[bool] = Query(default=None),
    role_category: Optional[str] = Query(default=None),
    seniority: Optional[str] = Query(default=None),
    salary_min: Optional[float] = Query(default=None),
    _: str = Depends(verify_api_key),
    session=Depends(get_db_session),
) -> SearchResponse:
    """Paginated listing of active jobs with structured metadata filters."""
    job_repo = JobRepository(session)
    filters = {
        "country": country,
        "is_remote": is_remote,
        "role_category": role_category,
        "seniority": seniority,
        "salary_min": salary_min,
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    jobs = await job_repo.get_active_jobs(limit=limit, offset=offset, filters=filters)
    return SearchResponse(
        query="",
        total=len(jobs),
        results=[_job_to_summary(j) for j in jobs],
    )


@router.post(
    "/discover",
    summary="Trigger manual discovery run",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_discovery(
    request: DiscoverRequest,
    _: str = Depends(verify_api_key),
) -> Dict[str, Any]:
    """
    Manually triggers a discovery run. Returns immediately with task_id.
    The pipeline runs asynchronously in the background via Celery.
    """
    try:
        from app.job_discovery.workers.discovery import run_discovery_pipeline
        task = run_discovery_pipeline.delay(
            query_params={
                "roles": request.roles,
                "locations": request.locations,
                "skills": request.skills,
            }
        )
        return {
            "status": "accepted",
            "task_id": task.id,
            "message": "Discovery run queued successfully",
        }
    except Exception as exc:
        logger.error(f"Failed to queue discovery task: {exc}")
        raise HTTPException(status_code=500, detail="Failed to queue discovery task")
