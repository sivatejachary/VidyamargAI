"""
VidyaMarg AI — Cleanup Worker
==============================
Maintains data hygiene across PostgreSQL and Qdrant:

  • archive_expired_jobs      — marks old jobs ARCHIVED in PG and removes their
                               vectors from Qdrant to reclaim memory.
  • sync_missing_qdrant_embeddings — re-queues any job that slipped through
                               without a Qdrant vector (qdrant_sync_pending=True).

Both tasks are scheduled via Celery Beat at off-peak hours (02:00 / 03:00 UTC).
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List

from app.job_discovery.workers.celery_app import celery_app
from app.job_discovery import config as cfg

logger = logging.getLogger("jd.workers.cleanup")

# Batch size constants
_ARCHIVE_BATCH_SIZE = 1_000
_EMBED_BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Async helpers
# ---------------------------------------------------------------------------

def _run_async(coro) -> Any:
    """Run an async coroutine synchronously inside a Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _do_archive_expired_jobs() -> Dict[str, Any]:
    """
    Core async logic for archiving expired jobs:
      1. Fetch all expired job IDs from PostgreSQL.
      2. Process in batches of 1 000:
         a. Archive batch in PostgreSQL.
         b. Delete corresponding Qdrant vectors.
      3. Return {archived_count, qdrant_deleted_count}.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from app.job_discovery.infrastructure.database.repository import JobRepository
    from app.job_discovery.infrastructure.database.models import JobORM
    from app.job_discovery.infrastructure.qdrant.client import QdrantVectorStore

    engine = create_async_engine(cfg.DATABASE_URL, pool_pre_ping=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    qdrant = QdrantVectorStore()
    try:
        await qdrant.connect()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[cleanup] Qdrant unavailable — will skip vector deletes: %s", exc)
        qdrant = None

    archived_total = 0
    qdrant_deleted_total = 0

    async with async_session() as session:
        repo = JobRepository(session)

        # 1. Fetch expired job IDs
        job_ids: List[int] = await repo.get_expired_jobs(days=cfg.JOB_EXPIRY_DAYS)
        logger.info(
            "[cleanup] archive_expired_jobs — found %d expired jobs (expiry=%d days)",
            len(job_ids),
            cfg.JOB_EXPIRY_DAYS,
        )

        if not job_ids:
            return {"archived_count": 0, "qdrant_deleted_count": 0}

        # Resolve embedding_ids for Qdrant deletion before we mark them archived
        embedding_id_map: Dict[int, str] = {}
        if qdrant is not None:
            from sqlalchemy import select as sa_select
            result = await session.execute(
                sa_select(JobORM.id, JobORM.embedding_id).where(
                    JobORM.id.in_(job_ids), JobORM.embedding_id.isnot(None)
                )
            )
            embedding_id_map = {row[0]: row[1] for row in result.fetchall()}

        # 2. Process in batches of _ARCHIVE_BATCH_SIZE
        for batch_start in range(0, len(job_ids), _ARCHIVE_BATCH_SIZE):
            batch = job_ids[batch_start: batch_start + _ARCHIVE_BATCH_SIZE]

            # 2a. Archive in PostgreSQL
            archived = await repo.archive_jobs(batch)
            await session.commit()
            archived_total += archived
            logger.debug(
                "[cleanup] Archived batch [%d:%d] — %d rows",
                batch_start,
                batch_start + len(batch),
                archived,
            )

            # 2b. Delete vectors from Qdrant
            if qdrant is not None:
                embedding_ids = [
                    embedding_id_map[jid]
                    for jid in batch
                    if jid in embedding_id_map
                ]
                if embedding_ids:
                    try:
                        await qdrant.delete_points(embedding_ids)
                        qdrant_deleted_total += len(embedding_ids)
                        logger.debug(
                            "[cleanup] Deleted %d Qdrant vectors for batch [%d:%d]",
                            len(embedding_ids),
                            batch_start,
                            batch_start + len(batch),
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            "[cleanup] Qdrant delete failed for batch [%d:%d]: %s",
                            batch_start,
                            batch_start + len(batch),
                            exc,
                        )

    return {
        "archived_count": archived_total,
        "qdrant_deleted_count": qdrant_deleted_total,
    }


async def _do_sync_missing_qdrant_embeddings() -> Dict[str, Any]:
    """
    Core async logic for re-queuing jobs with qdrant_sync_pending=True.
    Dispatches embed_job_batch tasks in batches of _EMBED_BATCH_SIZE.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select, and_
    from app.job_discovery.infrastructure.database.models import JobORM

    engine = create_async_engine(cfg.DATABASE_URL, pool_pre_ping=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(
            select(JobORM.id).where(
                and_(
                    JobORM.qdrant_sync_pending == True,  # noqa: E712
                    JobORM.is_active == True,
                )
            )
        )
        pending_ids: List[int] = [row[0] for row in result.fetchall()]

    return pending_ids


# ---------------------------------------------------------------------------
# Celery Tasks
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    name="app.workers.cleanup.archive_expired_jobs",
    max_retries=2,
    default_retry_delay=300,  # 5 minutes between retries
)
def archive_expired_jobs(self) -> Dict[str, Any]:
    """
    Archives expired jobs from PostgreSQL and removes their Qdrant vectors.

    Steps:
      1. Call JobRepository.get_expired_jobs(days=cfg.JOB_EXPIRY_DAYS).
      2. For each batch of 1 000 job IDs:
         a. Call JobRepository.archive_jobs(batch) — marks ARCHIVED in PG.
         b. Call QdrantVectorStore.delete_points(embedding_ids).
      3. Return {archived_count, qdrant_deleted_count, duration_ms}.

    Retry policy: 2 retries, 5-minute delay.
    """
    logger.info("[cleanup] archive_expired_jobs — task started")
    t0 = time.monotonic()

    try:
        result = _run_async(_do_archive_expired_jobs())
    except Exception as exc:
        retry_num = self.request.retries
        delay = 300 * (2 ** retry_num)  # 300 s → 600 s
        logger.error(
            "[cleanup] archive_expired_jobs failed (attempt %d/%d): %s. Retrying in %ds.",
            retry_num + 1,
            self.max_retries + 1,
            exc,
            delay,
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=delay)

    duration_ms = int((time.monotonic() - t0) * 1000)
    result["duration_ms"] = duration_ms

    logger.info(
        "[cleanup] archive_expired_jobs complete — archived=%d qdrant_deleted=%d duration_ms=%d",
        result.get("archived_count", 0),
        result.get("qdrant_deleted_count", 0),
        duration_ms,
    )
    return result


@celery_app.task(
    bind=True,
    name="app.workers.cleanup.sync_missing_qdrant_embeddings",
    max_retries=2,
    default_retry_delay=300,
)
def sync_missing_qdrant_embeddings(self) -> Dict[str, Any]:
    """
    Re-queues embedding tasks for any job with qdrant_sync_pending=True.

    Steps:
      1. Query jobs where qdrant_sync_pending=True.
      2. Dispatch embed_job_batch.delay(job_ids) for batches of 100.
      3. Return {dispatched_batches, job_count, duration_ms}.

    Retry policy: 2 retries, 5-minute delay.
    """
    logger.info("[cleanup] sync_missing_qdrant_embeddings — task started")
    t0 = time.monotonic()

    try:
        pending_ids: List[int] = _run_async(_do_sync_missing_qdrant_embeddings())
    except Exception as exc:
        retry_num = self.request.retries
        delay = 300 * (2 ** retry_num)
        logger.error(
            "[cleanup] sync_missing_qdrant_embeddings failed (attempt %d/%d): %s. Retrying in %ds.",
            retry_num + 1,
            self.max_retries + 1,
            exc,
            delay,
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=delay)

    job_count = len(pending_ids)
    dispatched_batches = 0

    if job_count > 0:
        # Lazy import to avoid circular deps at module load time
        from app.job_discovery.workers.embedding import embed_job_batch  # type: ignore[import]

        for batch_start in range(0, job_count, _EMBED_BATCH_SIZE):
            batch = pending_ids[batch_start: batch_start + _EMBED_BATCH_SIZE]
            try:
                embed_job_batch.delay(batch)
                dispatched_batches += 1
                logger.debug(
                    "[cleanup] Dispatched embed_job_batch for %d jobs (batch %d)",
                    len(batch),
                    dispatched_batches,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "[cleanup] Failed to dispatch embed_job_batch for batch %d: %s",
                    dispatched_batches + 1,
                    exc,
                )

    duration_ms = int((time.monotonic() - t0) * 1000)

    logger.info(
        "[cleanup] sync_missing_qdrant_embeddings complete — "
        "job_count=%d dispatched_batches=%d duration_ms=%d",
        job_count,
        dispatched_batches,
        duration_ms,
    )
    return {
        "dispatched_batches": dispatched_batches,
        "job_count": job_count,
        "duration_ms": duration_ms,
    }
