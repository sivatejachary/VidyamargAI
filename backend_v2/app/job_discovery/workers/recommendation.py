"""
VidyaMarg AI — Recommendation Worker
======================================
Generates personalized job recommendations from computed candidate-job matches.

Pipeline per candidate_id:
  1. Load top CandidateMatch records for this candidate where:
       status = 'new' AND overall_score >= 70
     Ordered by overall_score DESC, limited by `limit` param.
  2. For each match:
       a. Build match_explanation from match_reasons list
       b. Construct a Recommendation domain object
  3. Bulk insert Recommendation records via RecommendationRepository
  4. Publish recommendations.created.v1 per recommendation
  5. Return summary dict

generate_hourly_recs:
  Beat task that loads all active candidate_ids from DB and dispatches
  generate_recommendations.delay(candidate_id) for each.

Retry policy: exponential backoff — 60 → 120 → 240 s.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from app.job_discovery.workers.celery_app import celery_app

logger = logging.getLogger("jd.workers.recommendation")


# ---------------------------------------------------------------------------
# Core Async Logic
# ---------------------------------------------------------------------------

async def _generate_recommendations_async(
    candidate_id: int,
    limit: int,
) -> Dict[str, Any]:
    """
    Core async recommendation generation for a single candidate.
    """
    from app.job_discovery.domain.events import RecommendationCreatedEvent
    from app.job_discovery.infrastructure.database.repository import (
        MatchRepository,
        RecommendationRepository,
    )
    from app.job_discovery.infrastructure.database.session import get_async_session
    from app.job_discovery.infrastructure.redis.stream import get_event_broker

    start_ts = time.monotonic()
    created_count = 0

    async with get_async_session() as session:
        match_repo = MatchRepository(session)
        rec_repo = RecommendationRepository(session)

        # ------------------------------------------------------------------
        # Step 1: Load top matches for candidate (status='new', score >= 70)
        # ------------------------------------------------------------------
        raw_matches = await match_repo.get_top_matches(candidate_id, limit=limit)
        qualifying_matches = [
            m for m in raw_matches
            if m.overall_score >= 70.0 and m.status == "new"
        ]

        if not qualifying_matches:
            logger.info(
                f"[recommendation] No qualifying matches for candidate_id={candidate_id}"
            )
            return {
                "created_count": 0,
                "candidate_id": candidate_id,
                "duration_ms": int((time.monotonic() - start_ts) * 1000),
            }

        logger.info(
            f"[recommendation] Found {len(qualifying_matches)} qualifying matches "
            f"for candidate_id={candidate_id}"
        )

        # ------------------------------------------------------------------
        # Step 2: Build Recommendation records
        # ------------------------------------------------------------------
        rec_mappings: List[Dict[str, Any]] = []

        for match in qualifying_matches:
            # Build explanation from match_reasons list
            reasons: List[str] = match.match_reasons or []
            if match.match_explanation:
                # Use the pre-computed explanation if available
                explanation = match.match_explanation
            elif reasons:
                explanation = ". ".join(reasons)
            else:
                explanation = (
                    f"Strong overall match score of {match.overall_score:.1f}/100 "
                    f"based on skills, experience, and location alignment."
                )

            rec_mappings.append({
                "candidate_id": candidate_id,
                "match_id": match.id,
                "job_id": match.job_id,
                "score": match.overall_score,
                "reason": explanation,
                "is_seen": False,
                "is_actioned": False,
            })

        # ------------------------------------------------------------------
        # Step 3: Bulk insert Recommendation records
        # ------------------------------------------------------------------
        inserted_ids = await rec_repo.bulk_insert(rec_mappings)
        created_count = len(inserted_ids)

        logger.info(
            f"[recommendation] Inserted {created_count} recommendations "
            f"for candidate_id={candidate_id}"
        )

        # ------------------------------------------------------------------
        # Step 4: Publish recommendations.created.v1 per recommendation
        # ------------------------------------------------------------------
        broker = get_event_broker()
        await broker.connect()

        for rec_id, match in zip(inserted_ids, qualifying_matches):
            event = RecommendationCreatedEvent.create(
                candidate_id=candidate_id,
                recommendation_id=rec_id,
                job_id=match.job_id,
                score=match.overall_score,
            )
            await broker.publish(event)
            logger.debug(
                f"[recommendation] Published recommendations.created.v1 "
                f"rec_id={rec_id} job_id={match.job_id}"
            )

    duration_ms = int((time.monotonic() - start_ts) * 1000)
    return {
        "created_count": created_count,
        "candidate_id": candidate_id,
        "duration_ms": duration_ms,
    }


# ---------------------------------------------------------------------------
# Primary Task — Generate Recommendations for One Candidate
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    name="app.workers.recommendation.generate_recommendations",
    max_retries=3,
    default_retry_delay=60,
)
def generate_recommendations(
    self,
    candidate_id: int,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Generates personalized job recommendations for a single candidate.

    Args:
        candidate_id:  PostgreSQL candidate ID.
        limit:         Maximum number of top matches to convert to recommendations.

    Returns:
        {"created_count": int, "candidate_id": int, "duration_ms": int}
    """
    task_id = self.request.id
    logger.info(
        f"[recommendation] Starting | task_id={task_id} candidate_id={candidate_id} "
        f"limit={limit} retry={self.request.retries}/{self.max_retries}"
    )

    try:
        result = asyncio.run(_generate_recommendations_async(candidate_id, limit))
        logger.info(
            f"[recommendation] Complete | candidate_id={candidate_id} "
            f"created={result['created_count']} duration_ms={result['duration_ms']}"
        )
        return result

    except Exception as exc:
        countdown = 2 ** self.request.retries * 60  # 60 → 120 → 240 s
        logger.exception(
            f"[recommendation] Failed for candidate_id={candidate_id} "
            f"(attempt {self.request.retries + 1}/{self.max_retries + 1}): {exc}"
        )

        if self.request.retries < self.max_retries:
            logger.info(f"[recommendation] Retrying in {countdown}s …")
            raise self.retry(exc=exc, countdown=countdown)

        logger.error(
            f"[recommendation] All {self.max_retries} retries exhausted "
            f"for candidate_id={candidate_id}."
        )
        return {
            "created_count": 0,
            "candidate_id": candidate_id,
            "duration_ms": 0,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Beat Task — Hourly Batch Dispatcher
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.workers.recommendation.generate_hourly_recs",
)
def generate_hourly_recs() -> Dict[str, Any]:
    """
    Beat task that dispatches generate_recommendations.delay(candidate_id)
    for every active candidate in the system.

    Runs every SCHEDULE_RECOMMENDATION_INTERVAL_MIN (default: 60 minutes).

    Returns:
        {"dispatched_count": int}
    """
    logger.info("[recommendation] Fetching active candidates for hourly recs …")

    async def _fetch_active_candidate_ids() -> List[int]:
        from sqlalchemy import text
        from app.job_discovery.infrastructure.database.session import get_async_session

        async with get_async_session() as session:
            try:
                result = await session.execute(
                    text(
                        "SELECT id FROM candidate_profiles WHERE is_active = TRUE"
                    )
                )
                return [row[0] for row in result.fetchall()]
            except Exception as exc:
                logger.warning(
                    f"[recommendation] Could not query candidate_profiles: {exc}. "
                    f"Table may not exist yet."
                )
                return []

    try:
        candidate_ids = asyncio.run(_fetch_active_candidate_ids())
    except Exception as exc:
        logger.error(f"[recommendation] Failed to fetch candidates: {exc}")
        return {"dispatched_count": 0, "error": str(exc)}

    if not candidate_ids:
        logger.info("[recommendation] No active candidates found. Nothing dispatched.")
        return {"dispatched_count": 0}

    dispatched = 0
    for cid in candidate_ids:
        try:
            generate_recommendations.delay(cid)
            dispatched += 1
        except Exception as exc:
            logger.error(
                f"[recommendation] Failed to dispatch task for candidate_id={cid}: {exc}"
            )

    logger.info(
        f"[recommendation] Dispatched {dispatched}/{len(candidate_ids)} "
        f"recommendation tasks"
    )
    return {"dispatched_count": dispatched}
