"""
VidyaMarg AI — Matching Worker
================================
Computes multi-signal weighted match scores between candidates and jobs.

IMPORTANT: This worker NEVER generates embeddings. It only queries existing
           Qdrant vectors via QdrantVectorStore.similarity_search().

Scoring formula (weights must sum to 1.0):
    overall = (
        semantic           * 0.35 +   # cosine similarity via Qdrant
        skill              * 0.25 +   # Jaccard similarity of skill sets
        experience         * 0.15 +   # years-range overlap
        salary             * 0.10 +   # salary band overlap
        location           * 0.08 +   # city / country match
        remote_preference  * 0.04 +   # remote-pref alignment
        company_preference * 0.02 +   # preferred/excluded company list
        freshness          * 0.01     # freshness_score from job record
    ) * 100  → [0, 100]

Pipeline per job_id:
  1. Load job from PostgreSQL (embedding_id, skills, salary, location, seniority)
  2. Guard: no embedding_id → log warning and return (embedding not ready)
  3. Load all active candidates from DB
  4. For each candidate:
       a. Load candidate resume embedding from DB
       b. Query Qdrant similarity_search(candidate embedding) → semantic_score
       c. Compute sub-scores (skill, experience, salary, location, remote, company, freshness)
       d. Compute overall_score with weights from cfg.MATCHING_WEIGHTS
       e. If overall_score >= candidate.min_match_score → build CandidateMatch record
  5. Bulk insert all matches via MatchRepository
  6. Publish jobs.matched.v1 event
  7. Return summary dict

Retry policy: exponential backoff — 60 → 120 → 240 s.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set

from app.job_discovery.workers.celery_app import celery_app

logger = logging.getLogger("jd.workers.matching")


# ---------------------------------------------------------------------------
# Score Helpers
# ---------------------------------------------------------------------------

def _jaccard(set_a: Set[str], set_b: Set[str]) -> float:
    """Jaccard similarity coefficient for two skill sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def _experience_score(
    job_min: Optional[float],
    job_max: Optional[float],
    candidate_years: Optional[float],
) -> float:
    """
    Scores experience overlap.
    - candidate within job range           → 1.0
    - candidate slightly under (≤1 year)   → 0.5
    - outside range                        → 0.0
    """
    if candidate_years is None:
        return 0.5  # Unknown → neutral

    # If job has no requirement, full score
    if job_min is None and job_max is None:
        return 1.0

    lo = job_min or 0.0
    hi = job_max or float("inf")

    if lo <= candidate_years <= hi:
        return 1.0
    if candidate_years < lo and (lo - candidate_years) <= 1.0:
        return 0.5
    return 0.0


def _salary_score(
    job_min: Optional[float],
    job_max: Optional[float],
    cand_min: Optional[float],
    cand_max: Optional[float],
) -> float:
    """
    Scores salary band overlap.
    Full overlap → 1.0, partial overlap → 0.5, no overlap → 0.0.
    """
    if job_min is None and job_max is None:
        return 0.5  # Undisclosed → neutral

    if cand_min is None and cand_max is None:
        return 0.5  # Candidate has no preference → neutral

    j_lo = float(job_min or 0)
    j_hi = float(job_max or j_lo * 1.5 or 1_000_000)
    c_lo = float(cand_min or 0)
    c_hi = float(cand_max or c_lo * 1.5 or 1_000_000)

    # Overlap check
    overlap_lo = max(j_lo, c_lo)
    overlap_hi = min(j_hi, c_hi)

    if overlap_lo > overlap_hi:
        return 0.0  # No overlap

    overlap_range = overlap_hi - overlap_lo
    j_range = j_hi - j_lo or 1.0
    ratio = overlap_range / j_range
    return min(1.0, ratio)


def _location_score(
    job_country: str,
    job_city: str,
    job_is_remote: bool,
    candidate_locations: List[str],
    candidate_work_mode: str,
) -> float:
    """
    Scores location compatibility.
    - Remote job + remote-preference candidate          → 1.0
    - Same city or country in candidate target list     → 1.0
    - Partial match (country only)                      → 0.5
    - No match                                          → 0.0
    """
    if job_is_remote:
        return 1.0  # Remote jobs match any location

    if not candidate_locations:
        return 0.5  # No preference → neutral

    normalized_locs = {loc.lower().strip() for loc in candidate_locations}

    if job_city and job_city.lower() in normalized_locs:
        return 1.0
    if job_country and job_country.lower() in normalized_locs:
        return 0.5
    return 0.0


def _remote_preference_score(
    job_is_remote: bool,
    candidate_work_mode: str,
) -> float:
    """1.0 if remote preference aligns with job remote status, else 0.3."""
    candidate_wants_remote = candidate_work_mode.lower() in ("remote", "hybrid")
    if job_is_remote == candidate_wants_remote:
        return 1.0
    return 0.3


def _company_preference_score(
    company_name: str,
    preferred_companies: List[str],
    excluded_companies: List[str],
) -> float:
    """
    1.0 → preferred company
    0.0 → excluded company
    0.5 → neutral
    """
    name_lower = company_name.lower() if company_name else ""
    if any(name_lower == p.lower() for p in excluded_companies):
        return 0.0
    if any(name_lower == p.lower() for p in preferred_companies):
        return 1.0
    return 0.5


def _compute_match_reasons(
    semantic_score: float,
    skill_score: float,
    experience_score: float,
    salary_score: float,
    location_score: float,
    matched_skills: List[str],
    missing_skills: List[str],
) -> List[str]:
    """Builds a human-readable list of match rationale strings."""
    reasons = []
    if semantic_score >= 0.75:
        reasons.append("Strong semantic alignment between resume and job description")
    elif semantic_score >= 0.50:
        reasons.append("Moderate semantic alignment with job description")

    if matched_skills:
        reasons.append(f"Matching skills: {', '.join(matched_skills[:5])}")

    if skill_score >= 0.8:
        reasons.append("Excellent skill overlap")
    elif skill_score >= 0.5:
        reasons.append("Good skill overlap")

    if experience_score >= 1.0:
        reasons.append("Experience within job requirements")

    if salary_score >= 0.8:
        reasons.append("Salary expectations aligned")

    if location_score >= 1.0:
        reasons.append("Location preference matched")

    if missing_skills:
        reasons.append(f"Skill gaps: {', '.join(missing_skills[:3])}")

    return reasons


def _compute_overall_score(
    weights: Any,
    semantic: float,
    skill: float,
    experience: float,
    salary: float,
    location: float,
    remote_pref: float,
    company_pref: float,
    freshness: float,
) -> float:
    """
    Applies weighted sum and scales to [0, 100].
    Uses weights from cfg.MATCHING_WEIGHTS (MatchingWeights dataclass).
    """
    raw = (
        semantic * weights.semantic
        + skill * weights.skill
        + experience * weights.experience
        + salary * weights.salary
        + location * weights.location
        + remote_pref * weights.remote_preference
        + company_pref * weights.company_preference
        + freshness * weights.freshness
    )
    return round(raw * 100, 4)


# ---------------------------------------------------------------------------
# Core Async Logic
# ---------------------------------------------------------------------------

async def _match_job_async(job_id: int) -> Dict[str, Any]:
    """
    Full async matching pipeline for a single job against all active candidates.
    """
    from sqlalchemy import select

    from app.job_discovery import config as cfg
    from app.job_discovery.domain.events import JobsMatchedEvent
    from app.job_discovery.domain.models import CandidatePreference, MatchStatus
    from app.job_discovery.infrastructure.database.models import (
        CandidateMatchORM,
        JobORM,
    )
    from app.job_discovery.infrastructure.database.repository import (
        JobRepository,
        MatchRepository,
    )
    from app.job_discovery.infrastructure.database.session import get_async_session
    from app.job_discovery.infrastructure.qdrant.client import (
        QdrantUnavailableError,
        get_qdrant_store,
    )
    from app.job_discovery.infrastructure.redis.stream import get_event_broker

    start_ts = time.monotonic()
    matched_candidates = 0
    skipped = 0

    async with get_async_session() as session:
        # ------------------------------------------------------------------
        # Step 1: Load job
        # ------------------------------------------------------------------
        job_repo = JobRepository(session)
        job = await job_repo.get_by_id(job_id)

        if job is None:
            logger.warning(f"[matching] job_id={job_id} not found in DB — skipping")
            return {"matched_candidates": 0, "skipped": 1, "duration_ms": 0}

        # ------------------------------------------------------------------
        # Step 2: Guard — embedding must exist
        # ------------------------------------------------------------------
        if not job.embedding_id:
            logger.warning(
                f"[matching] job_id={job_id} has no embedding_id. "
                f"Embedding worker must run first. Skipping."
            )
            return {
                "matched_candidates": 0,
                "skipped": 1,
                "duration_ms": 0,
                "reason": "embedding_not_ready",
            }

        # ------------------------------------------------------------------
        # Step 3: Load ALL active candidates from DB
        # The CandidatePreference is stored per-candidate in the main AI OS.
        # Here we read a denormalized view from the jobs DB.
        # We query the candidate_preferences table (if it exists) or the users table.
        # For a clean boundary, we use a raw select on the ORM models available in
        # this module and construct CandidatePreference domain objects.
        # ------------------------------------------------------------------
        from sqlalchemy import text

        # Attempt to load from a candidate_profiles view or a joined table.
        # If this schema doesn't exist yet, gracefully skip matching.
        try:
            candidate_rows = await session.execute(
                text(
                    """
                    SELECT
                        id AS candidate_id,
                        target_roles,
                        required_skills,
                        target_locations,
                        target_salary_min,
                        target_salary_max,
                        target_salary_currency,
                        work_mode_preference,
                        employment_type_preference,
                        experience_years,
                        preferred_companies,
                        excluded_companies,
                        min_match_score,
                        resume_embedding,
                        resume_embedding_id
                    FROM candidate_profiles
                    WHERE is_active = TRUE
                    LIMIT 10000
                    """
                )
            )
            candidates_data = candidate_rows.mappings().all()
        except Exception as exc:
            logger.warning(
                f"[matching] Could not load candidate_profiles (table may not exist yet): {exc}"
            )
            return {
                "matched_candidates": 0,
                "skipped": 0,
                "duration_ms": int((time.monotonic() - start_ts) * 1000),
                "reason": "candidate_table_unavailable",
            }

        if not candidates_data:
            logger.info(f"[matching] No active candidates found for job_id={job_id}")
            return {
                "matched_candidates": 0,
                "skipped": 0,
                "duration_ms": int((time.monotonic() - start_ts) * 1000),
            }

        logger.info(
            f"[matching] Evaluating job_id={job_id} against "
            f"{len(candidates_data)} candidates"
        )

        # ------------------------------------------------------------------
        # Prepare Qdrant + broker clients
        # ------------------------------------------------------------------
        qdrant = get_qdrant_store()
        await qdrant.connect()
        broker = get_event_broker()
        await broker.connect()

        weights = cfg.MATCHING_WEIGHTS
        job_skills: Set[str] = set(job.required_skills or []) | set(job.preferred_skills or [])
        job_skills_lower = {s.lower() for s in job_skills}

        match_mappings: List[Dict[str, Any]] = []

        # ------------------------------------------------------------------
        # Step 4: Score each candidate
        # ------------------------------------------------------------------
        for row in candidates_data:
            cand_id = row["candidate_id"]
            resume_embedding: Optional[List[float]] = row.get("resume_embedding")

            # ------------------------------------------------------------------
            # Step 4a+4b: Semantic score via Qdrant similarity search
            # ------------------------------------------------------------------
            semantic_score = 0.0
            if resume_embedding:
                try:
                    search_results = await qdrant.similarity_search(
                        query_vector=resume_embedding,
                        limit=50,
                        score_threshold=0.0,
                    )
                    # Check if this specific job's vector appears in results
                    for point_id, score, _payload in search_results:
                        if point_id == job.embedding_id:
                            semantic_score = float(score)
                            break
                except QdrantUnavailableError:
                    logger.warning(
                        f"[matching] Qdrant unavailable for candidate_id={cand_id}. "
                        f"Semantic score defaulting to 0."
                    )
                except Exception as exc:
                    logger.error(
                        f"[matching] Qdrant search error for candidate_id={cand_id}: {exc}"
                    )
            else:
                logger.debug(
                    f"[matching] candidate_id={cand_id} has no resume embedding — "
                    f"semantic_score=0"
                )
                skipped += 1
                continue  # Skip candidates without embeddings

            # ------------------------------------------------------------------
            # Step 4c: Sub-signal scores
            # ------------------------------------------------------------------
            cand_skills = set(row.get("required_skills") or [])
            cand_skills_lower = {s.lower() for s in cand_skills}
            matched_skills_lower = job_skills_lower & cand_skills_lower
            missing_skills_lower = job_skills_lower - cand_skills_lower

            skill_score = _jaccard(job_skills_lower, cand_skills_lower)

            experience_score = _experience_score(
                job_min=job.experience_min_years,
                job_max=job.experience_max_years,
                candidate_years=row.get("experience_years"),
            )

            salary_score = _salary_score(
                job_min=float(job.salary_min) if job.salary_min else None,
                job_max=float(job.salary_max) if job.salary_max else None,
                cand_min=row.get("target_salary_min"),
                cand_max=row.get("target_salary_max"),
            )

            location_score = _location_score(
                job_country=job.country or "",
                job_city=job.city or "",
                job_is_remote=bool(job.is_remote),
                candidate_locations=list(row.get("target_locations") or []),
                candidate_work_mode=str(row.get("work_mode_preference") or ""),
            )

            remote_pref_score = _remote_preference_score(
                job_is_remote=bool(job.is_remote),
                candidate_work_mode=str(row.get("work_mode_preference") or ""),
            )

            company_pref_score = _company_preference_score(
                company_name=job.company_name or "",
                preferred_companies=list(row.get("preferred_companies") or []),
                excluded_companies=list(row.get("excluded_companies") or []),
            )

            freshness = float(job.freshness_score or 1.0)

            # ------------------------------------------------------------------
            # Step 4e: Weighted overall score
            # ------------------------------------------------------------------
            overall_score = _compute_overall_score(
                weights=weights,
                semantic=semantic_score,
                skill=skill_score,
                experience=experience_score,
                salary=salary_score,
                location=location_score,
                remote_pref=remote_pref_score,
                company_pref=company_pref_score,
                freshness=freshness,
            )

            min_score = float(row.get("min_match_score") or 60.0)

            if overall_score < min_score:
                skipped += 1
                continue

            # ------------------------------------------------------------------
            # Step 4f: Build CandidateMatch record
            # ------------------------------------------------------------------
            matched_skills = list(matched_skills_lower)[:20]
            missing_skills = list(missing_skills_lower)[:20]

            reasons = _compute_match_reasons(
                semantic_score=semantic_score,
                skill_score=skill_score,
                experience_score=experience_score,
                salary_score=salary_score,
                location_score=location_score,
                matched_skills=matched_skills,
                missing_skills=missing_skills,
            )

            explanation = ". ".join(reasons)

            # Determine skill gap severity
            gap_ratio = len(missing_skills) / max(len(job_skills_lower), 1)
            if gap_ratio == 0:
                severity = "none"
            elif gap_ratio < 0.25:
                severity = "minor"
            elif gap_ratio < 0.60:
                severity = "moderate"
            else:
                severity = "major"

            match_mappings.append({
                "candidate_id": cand_id,
                "job_id": job_id,
                "overall_score": overall_score,
                "semantic_score": semantic_score,
                "skill_score": skill_score,
                "experience_score": experience_score,
                "salary_score": salary_score,
                "location_score": location_score,
                "remote_preference_score": remote_pref_score,
                "company_preference_score": company_pref_score,
                "freshness_score": freshness,
                "match_reasons": reasons,
                "missing_skills": missing_skills,
                "skill_gap_severity": severity,
                "match_explanation": explanation,
                "status": MatchStatus.NEW.value,
            })
            matched_candidates += 1

        # ------------------------------------------------------------------
        # Step 5: Bulk insert matches
        # ------------------------------------------------------------------
        match_repo = MatchRepository(session)
        if match_mappings:
            inserted_ids = await match_repo.bulk_insert_matches(match_mappings)
            logger.info(
                f"[matching] Inserted {len(inserted_ids)} matches for job_id={job_id}"
            )
        else:
            logger.info(f"[matching] No qualifying matches for job_id={job_id}")

        # ------------------------------------------------------------------
        # Step 6: Publish jobs.matched.v1 event
        # ------------------------------------------------------------------
        event = JobsMatchedEvent.create(
            job_id=job_id,
            matched_candidates_count=matched_candidates,
        )
        await broker.publish(event)

    duration_ms = int((time.monotonic() - start_ts) * 1000)
    return {
        "matched_candidates": matched_candidates,
        "skipped": skipped,
        "duration_ms": duration_ms,
    }


# ---------------------------------------------------------------------------
# Primary Task — Match a Job Against All Candidates
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    name="app.workers.matching.match_job_to_candidates",
    max_retries=3,
    default_retry_delay=60,
)
def match_job_to_candidates(self, job_id: int) -> Dict[str, Any]:
    """
    Computes weighted match scores between one job and all active candidates.

    NEVER generates embeddings — only queries existing Qdrant vectors.

    Args:
        job_id: PostgreSQL ID of the job to match.

    Returns:
        {"matched_candidates": int, "skipped": int, "duration_ms": int}
    """
    task_id = self.request.id
    logger.info(
        f"[matching] Starting | task_id={task_id} job_id={job_id} "
        f"retry={self.request.retries}/{self.max_retries}"
    )

    try:
        result = asyncio.run(_match_job_async(job_id))
        logger.info(
            f"[matching] Complete | job_id={job_id} "
            f"matched={result.get('matched_candidates')} "
            f"skipped={result.get('skipped')} "
            f"duration_ms={result.get('duration_ms')}"
        )
        return result

    except Exception as exc:
        countdown = 2 ** self.request.retries * 60  # 60 → 120 → 240 s
        logger.exception(
            f"[matching] Failed for job_id={job_id} "
            f"(attempt {self.request.retries + 1}/{self.max_retries + 1}): {exc}"
        )

        if self.request.retries < self.max_retries:
            logger.info(f"[matching] Retrying in {countdown}s …")
            raise self.retry(exc=exc, countdown=countdown)

        logger.error(
            f"[matching] All {self.max_retries} retries exhausted for job_id={job_id}."
        )
        return {
            "matched_candidates": 0,
            "skipped": 0,
            "duration_ms": 0,
            "error": str(exc),
        }
