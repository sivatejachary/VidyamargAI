"""
VidyaMarg AI — Embedding Worker
=================================
Generates OpenAI text-embedding-3-small vectors for persisted jobs and
upserts them to the Qdrant collection for semantic search.

Pipeline per batch:
  1. Load job rows from PostgreSQL (title + description)
  2. Build embedding text: "{title}. {description[:2000]}"
  3. Batch-call OpenAI Embeddings API (single request for the whole batch)
  4. Upsert point structs to Qdrant with metadata payload
  5. Update job.embedding_id + lifecycle_status='embedded' in PostgreSQL
  6. Publish jobs.embedded.v1 event per job

Fallback: if Qdrant is unavailable, mark qdrant_sync_pending=True on the job
so the sync_pending_embeddings beat task can retry later.

Retry policy: exponential backoff — 60 → 120 → 240 s.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List

from app.job_discovery.workers.celery_app import celery_app

logger = logging.getLogger("jd.workers.embedding")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _embed_batch_async(job_ids: List[int]) -> Dict[str, Any]:
    """
    Core async logic for embed_job_batch.
    Separated so asyncio.run() wraps a single coroutine entry-point.
    """
    import openai

    from app.job_discovery import config as cfg
    from app.job_discovery.domain.events import JobEmbeddedEvent
    from app.job_discovery.domain.models import JobLifecycle
    from app.job_discovery.infrastructure.database.repository import JobRepository
    from app.job_discovery.infrastructure.database.session import get_async_session
    from app.job_discovery.infrastructure.qdrant.client import (
        QdrantUnavailableError,
        get_qdrant_store,
    )
    from app.job_discovery.infrastructure.redis.stream import get_event_broker
    from sqlalchemy import update
    from datetime import datetime

    from app.job_discovery.infrastructure.database.models import JobORM

    embedded_count = 0
    failed_count = 0
    start_ts = time.monotonic()

    if not job_ids:
        return {"embedded_count": 0, "failed_count": 0, "duration_ms": 0}

    # ------------------------------------------------------------------
    # Step 1: Load jobs from PostgreSQL
    # ------------------------------------------------------------------
    async with get_async_session() as session:
        job_repo = JobRepository(session)

        jobs = []
        for jid in job_ids:
            job = await job_repo.get_by_id(jid)
            if job is None:
                logger.warning(f"[embedding] job_id={jid} not found in DB — skipping")
                failed_count += 1
            else:
                jobs.append(job)

        if not jobs:
            return {
                "embedded_count": 0,
                "failed_count": failed_count,
                "duration_ms": int((time.monotonic() - start_ts) * 1000),
            }

        # ------------------------------------------------------------------
        # Step 2: Build embedding texts
        # ------------------------------------------------------------------
        texts = [
            f"{job.title}. {(job.description or '')[:2000]}"
            for job in jobs
        ]

        # ------------------------------------------------------------------
        # Step 3: Batch call OpenAI Embeddings API
        # ------------------------------------------------------------------
        try:
            oai_client = openai.AsyncOpenAI(api_key=cfg.OPENAI_API_KEY)
            response = await oai_client.embeddings.create(
                model=cfg.EMBEDDING_MODEL,
                input=texts,
            )
            vectors = [item.embedding for item in response.data]
            logger.info(
                f"[embedding] OpenAI returned {len(vectors)} embeddings "
                f"(dim={len(vectors[0]) if vectors else 0})"
            )
        except Exception as exc:
            logger.error(f"[embedding] OpenAI API call failed: {exc}")
            raise  # Let the caller handle retry

        # ------------------------------------------------------------------
        # Step 4: Upsert to Qdrant + Step 5: Mark embedded in DB
        # ------------------------------------------------------------------
        qdrant = get_qdrant_store()
        await qdrant.connect()

        broker = get_event_broker()
        await broker.connect()

        for job, vector in zip(jobs, vectors):
            vector_id = str(uuid.uuid4())
            point = {
                "id": vector_id,
                "vector": vector,
                "payload": {
                    "job_id": job.id,
                    "country": job.country or "IN",
                    "is_remote": bool(job.is_remote),
                    "seniority": job.seniority or "",
                    "role_category": job.role_category or "",
                },
            }

            try:
                await qdrant.upsert_embeddings([point])

                # Update job record — embedding_id + lifecycle
                await job_repo.mark_embedded(job.id, vector_id)

                # Publish per-job event
                event = JobEmbeddedEvent.create(
                    job_id=job.id,
                    vector_id=vector_id,
                    dimensions=len(vector),
                )
                await broker.publish(event)

                embedded_count += 1
                logger.debug(
                    f"[embedding] job_id={job.id} embedded → vector_id={vector_id}"
                )

            except QdrantUnavailableError:
                # Graceful degradation: flag for later sync
                logger.warning(
                    f"[embedding] Qdrant unavailable for job_id={job.id}. "
                    f"Setting qdrant_sync_pending=True."
                )
                from sqlalchemy import update
                stmt = (
                    update(JobORM)
                    .where(JobORM.id == job.id)
                    .values(
                        qdrant_sync_pending=True,
                        updated_at=datetime.utcnow(),
                    )
                )
                await session.execute(stmt)
                failed_count += 1

            except Exception as exc:
                logger.error(
                    f"[embedding] Failed to embed job_id={job.id}: {exc}"
                )
                failed_count += 1

    duration_ms = int((time.monotonic() - start_ts) * 1000)
    return {
        "embedded_count": embedded_count,
        "failed_count": failed_count,
        "duration_ms": duration_ms,
    }


# ---------------------------------------------------------------------------
# Primary Task — Embed a Batch of Jobs
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    name="app.workers.embedding.embed_job_batch",
    max_retries=3,
    default_retry_delay=60,
)
def embed_job_batch(self, job_ids: List[int]) -> Dict[str, Any]:
    """
    Generates OpenAI embeddings for a list of job IDs and upserts them to Qdrant.

    Args:
        job_ids: List of PostgreSQL job IDs to embed.

    Returns:
        {"embedded_count": int, "failed_count": int, "duration_ms": int}
    """
    task_id = self.request.id
    logger.info(
        f"[embedding] Starting batch | task_id={task_id} "
        f"job_count={len(job_ids)} retry={self.request.retries}/{self.max_retries}"
    )

    try:
        result = asyncio.run(_embed_batch_async(job_ids))
        logger.info(
            f"[embedding] Batch complete | embedded={result['embedded_count']} "
            f"failed={result['failed_count']} duration_ms={result['duration_ms']}"
        )
        return result

    except Exception as exc:
        countdown = 2 ** self.request.retries * 60  # 60 → 120 → 240 s
        logger.exception(
            f"[embedding] Batch failed (attempt {self.request.retries + 1}/"
            f"{self.max_retries + 1}): {exc}"
        )

        if self.request.retries < self.max_retries:
            logger.info(f"[embedding] Retrying in {countdown}s …")
            raise self.retry(exc=exc, countdown=countdown)

        logger.error(
            f"[embedding] All {self.max_retries} retries exhausted for "
            f"job_ids={job_ids}. Jobs remain in qdrant_sync_pending state."
        )
        return {
            "embedded_count": 0,
            "failed_count": len(job_ids),
            "duration_ms": 0,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Beat Task — Re-sync Pending Embeddings
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.workers.embedding.sync_pending_embeddings",
)
def sync_pending_embeddings() -> Dict[str, Any]:
    """
    Fetches all jobs flagged with qdrant_sync_pending=True and dispatches
    embed_job_batch.delay() for them in configurable batch chunks.

    Called by Celery Beat to recover from transient Qdrant outages.

    Returns:
        {"dispatched_batches": int, "total_jobs": int}
    """
    logger.info("[embedding] Scanning for qdrant_sync_pending jobs …")

    async def _fetch_pending() -> List[int]:
        from app.job_discovery.infrastructure.database.repository import JobRepository
        from app.job_discovery.infrastructure.database.session import get_async_session

        async with get_async_session() as session:
            repo = JobRepository(session)
            jobs = await repo.get_pending_embeddings(limit=1000)
            return [j.id for j in jobs]

    try:
        pending_ids = asyncio.run(_fetch_pending())
    except Exception as exc:
        logger.error(f"[embedding] Failed to fetch pending jobs: {exc}")
        return {"dispatched_batches": 0, "total_jobs": 0, "error": str(exc)}

    if not pending_ids:
        logger.info("[embedding] No pending embeddings found.")
        return {"dispatched_batches": 0, "total_jobs": 0}

    from app.job_discovery import config as cfg

    batch_size = cfg.EMBEDDING_BATCH_SIZE
    batches = [
        pending_ids[i : i + batch_size]
        for i in range(0, len(pending_ids), batch_size)
    ]

    for batch in batches:
        embed_job_batch.delay(batch)

    logger.info(
        f"[embedding] Dispatched {len(batches)} embed batches "
        f"for {len(pending_ids)} pending jobs"
    )
    return {"dispatched_batches": len(batches), "total_jobs": len(pending_ids)}
