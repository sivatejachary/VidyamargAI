"""
VidyaMarg AI — Notification Worker
====================================
Dispatches user-facing job-match notifications.

Delivery channels (v1 — stub logging; real delivery in v2):
  • WebSocket push (via FastAPI WebSocket manager)
  • Email (via SendGrid / SES)
  • Telegram bot message

Each notification is correlated to a Recommendation row so the UI can
mark it 'seen' once the candidate clicks the action URL.

Event published: notifications.created.v1
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.job_discovery.workers.celery_app import celery_app
from app.job_discovery import config as cfg

logger = logging.getLogger("jd.workers.notification")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_async(coro) -> Any:
    """Run an async coroutine from a synchronous Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _load_recommendation_and_job(
    recommendation_id: int, job_id: int
) -> Optional[tuple]:
    """
    Load a Recommendation + Job from PostgreSQL.

    Returns (recommendation_orm, job_orm) or None when either is missing.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from app.job_discovery.infrastructure.database.models import RecommendationORM, JobORM

    engine = create_async_engine(cfg.DATABASE_URL, pool_pre_ping=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        rec_result = await session.execute(
            select(RecommendationORM).where(RecommendationORM.id == recommendation_id)
        )
        rec = rec_result.scalar_one_or_none()
        if rec is None:
            logger.warning(
                "[notification] Recommendation %d not found — skipping.", recommendation_id
            )
            return None

        job_result = await session.execute(
            select(JobORM).where(JobORM.id == job_id)
        )
        job = job_result.scalar_one_or_none()
        if job is None:
            logger.warning(
                "[notification] Job %d not found — skipping.", job_id
            )
            return None

        # Detach from session before returning
        session.expunge(rec)
        session.expunge(job)
        return rec, job


async def _publish_notification_event(
    candidate_id: int,
    notification_id: int,
    channel: str,
) -> None:
    """Append a NotificationCreatedEvent to the Redis event stream."""
    try:
        from app.job_discovery.infrastructure.redis.stream import EventStreamBroker
        from app.job_discovery.domain.events import NotificationCreatedEvent

        broker = EventStreamBroker()
        await broker.connect()
        event = NotificationCreatedEvent.create(
            notification_id=notification_id,
            candidate_id=candidate_id,
            channel=channel,
            status="sent",
        )
        await broker.publish("notifications.created.v1", event)
        logger.debug(
            "[notification] Event notifications.created.v1 published — "
            "notification_id=%d candidate_id=%d",
            notification_id,
            candidate_id,
        )
    except Exception as exc:  # noqa: BLE001
        # Non-critical: event loss is acceptable if delivery succeeded
        logger.warning("[notification] Failed to publish event: %s", exc)


async def _fetch_unseen_recommendations() -> List[Dict[str, Any]]:
    """
    Scan all candidates and return a flat list of unseen recommendations.

    Returns a list of dicts: {candidate_id, recommendation_id, job_id}
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from app.job_discovery.infrastructure.database.models import RecommendationORM

    engine = create_async_engine(cfg.DATABASE_URL, pool_pre_ping=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        stmt = (
            select(
                RecommendationORM.candidate_id,
                RecommendationORM.id,
                RecommendationORM.job_id,
            )
            .where(RecommendationORM.is_seen == False)  # noqa: E712
            .order_by(RecommendationORM.score.desc())
        )
        result = await session.execute(stmt)
        rows = result.fetchall()

    return [
        {"candidate_id": row[0], "recommendation_id": row[1], "job_id": row[2]}
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Celery Tasks
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    name="app.workers.notification.send_recommendation_notification",
    max_retries=3,
    default_retry_delay=60,  # seconds; doubled on each retry
)
def send_recommendation_notification(
    self,
    candidate_id: int,
    recommendation_id: int,
    job_id: int,
) -> Dict[str, Any]:
    """
    Builds and dispatches a single job-match notification for one candidate.

    Steps:
      1. Load the Recommendation from DB (score, reason).
      2. Load the Job details (title, company, apply_url).
      3. Build notification payload.
      4. Log the notification (stub; real WebSocket/email dispatch in v2).
      5. Publish notifications.created.v1 event.
      6. Return a result envelope.

    Retry policy: 3 retries with exponential backoff (60 s → 120 s → 240 s).
    """
    logger.info(
        "[notification] send_recommendation_notification start — "
        "candidate_id=%d recommendation_id=%d job_id=%d",
        candidate_id,
        recommendation_id,
        job_id,
    )

    try:
        result = _run_async(
            _load_recommendation_and_job(recommendation_id, job_id)
        )
        if result is None:
            # DB record missing — no point retrying
            return {
                "candidate_id": candidate_id,
                "notification_id": None,
                "channel": "websocket",
                "status": "skipped",
                "reason": "recommendation_or_job_not_found",
            }

        rec, job = result

        # ----------------------------------------------------------------
        # 3. Build notification payload
        # ----------------------------------------------------------------
        job_title: str = getattr(job, "title", "Untitled Position")
        company: str = getattr(job, "company_name", "Unknown Company")
        apply_url: str = getattr(job, "apply_url", "") or ""
        score: float = getattr(rec, "score", 0.0)
        reason: str = getattr(rec, "reason", "Strong profile match")

        notification_title = f"🎯 New Job Match: {job_title} at {company}"
        notification_body = f"{reason}\nMatch Score: {score:.0f}%"

        payload = {
            "title": notification_title,
            "body": notification_body,
            "action_url": apply_url,
            "score": score,
            "candidate_id": candidate_id,
            "recommendation_id": recommendation_id,
            "job_id": job_id,
        }

        # ----------------------------------------------------------------
        # 4. Log notification (real WebSocket/email/Telegram delivery in v2)
        # ----------------------------------------------------------------
        notification_id: int = hash(
            f"{candidate_id}-{recommendation_id}-{datetime.utcnow().isoformat()}"
        ) & 0xFFFFFF  # deterministic pseudo-ID until a NotificationORM is added

        logger.info(
            "[notification] SEND — channel=websocket | %s | %s | url=%s",
            notification_title,
            notification_body,
            apply_url,
        )

        # ----------------------------------------------------------------
        # 5. Publish domain event
        # ----------------------------------------------------------------
        _run_async(
            _publish_notification_event(
                candidate_id=candidate_id,
                notification_id=notification_id,
                channel="websocket",
            )
        )

        logger.info(
            "[notification] Notification dispatched — "
            "candidate_id=%d notification_id=%d status=sent",
            candidate_id,
            notification_id,
        )

        # ----------------------------------------------------------------
        # 6. Return result envelope
        # ----------------------------------------------------------------
        return {
            "candidate_id": candidate_id,
            "notification_id": notification_id,
            "channel": "websocket",
            "status": "sent",
        }

    except Exception as exc:
        retry_num = self.request.retries
        delay = 60 * (2 ** retry_num)  # 60 s, 120 s, 240 s
        logger.error(
            "[notification] Task failed (attempt %d/%d) — %s. Retrying in %ds.",
            retry_num + 1,
            self.max_retries + 1,
            exc,
            delay,
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=delay)


@celery_app.task(name="app.workers.notification.flush_notifications")
def flush_notifications() -> Dict[str, Any]:
    """
    Sweeps the database for all unseen Recommendation rows and fans out an
    individual send_recommendation_notification task for each one.

    Designed to run every 15 minutes via Celery Beat.
    Returns {dispatched_count}.
    """
    logger.info("[notification] flush_notifications — starting sweep")

    try:
        unseen: List[Dict[str, Any]] = _run_async(_fetch_unseen_recommendations())
    except Exception as exc:  # noqa: BLE001
        logger.error("[notification] flush_notifications DB error: %s", exc, exc_info=True)
        return {"dispatched_count": 0, "error": str(exc)}

    dispatched = 0
    for entry in unseen:
        try:
            send_recommendation_notification.delay(
                entry["candidate_id"],
                entry["recommendation_id"],
                entry["job_id"],
            )
            dispatched += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[notification] Failed to dispatch for recommendation_id=%d: %s",
                entry["recommendation_id"],
                exc,
            )

    logger.info(
        "[notification] flush_notifications complete — dispatched=%d", dispatched
    )
    return {"dispatched_count": dispatched}
