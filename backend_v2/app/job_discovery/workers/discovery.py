"""
VidyaMarg AI — Discovery Worker
================================
Celery task that triggers the full autonomous job discovery pipeline.

Pipeline Summary:
  run_discovery_pipeline  →  DiscoveryOrchestrator.run()
                             ├── Phase 1: Run all connectors in parallel
                             ├── Phase 2: Pull from Redis buffer
                             ├── Phase 3-5: Normalize → Validate → Enrich
                             ├── Phase 6: Deduplicate (async DB checks)
                             ├── Phase 7-8: Bulk persist companies + jobs
                             └── Phase 9-10: Record history + publish event

run_all_connectors  →  Convenience task that fires run_discovery_pipeline.delay()
                       and returns the enqueued task_id.

Retry policy: exponential backoff — 60s, 120s, 240s.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from app.job_discovery.workers.celery_app import celery_app

logger = logging.getLogger("jd.workers.discovery")


# ---------------------------------------------------------------------------
# Primary Task — Full Discovery Pipeline
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    name="app.workers.discovery.run_discovery_pipeline",
    max_retries=3,
    default_retry_delay=60,
)
def run_discovery_pipeline(
    self,
    query_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Executes the full discovery pipeline end-to-end via DiscoveryOrchestrator.run().

    Returns a summary dict:
        {
            "run_id": str,
            "jobs_persisted": int,
            "duration_ms": int,
            "error": str | None,
        }

    On failure, retries with exponential backoff (60 → 120 → 240 seconds).
    After max_retries, logs the final error and returns a graceful error dict.
    """
    task_id = self.request.id
    logger.info(
        f"[discovery] Starting pipeline | task_id={task_id} "
        f"retry={self.request.retries}/{self.max_retries}"
    )

    start_ts = time.monotonic()

    async def _run() -> Dict[str, Any]:
        # Late import to avoid circular imports at module load time
        from app.job_discovery.application.orchestrator import DiscoveryOrchestrator

        orchestrator = DiscoveryOrchestrator()
        report = await orchestrator.run(query_params=query_params)

        return {
            "run_id": report.run_id,
            "jobs_persisted": report.jobs_persisted,
            "duration_ms": report.duration_ms,
            "connectors_run": report.connectors_run,
            "connectors_succeeded": report.connectors_succeeded,
            "connectors_failed": report.connectors_failed,
            "raw_jobs_discovered": report.raw_jobs_discovered,
            "jobs_normalized": report.jobs_normalized,
            "jobs_validated": report.jobs_validated,
            "jobs_deduplicated": report.jobs_deduplicated,
            "jobs_rejected": report.jobs_rejected,
            "companies_created": report.companies_created,
            "error": report.error,
        }

    try:
        result = asyncio.run(_run())
        elapsed = int((time.monotonic() - start_ts) * 1000)
        logger.info(
            f"[discovery] Pipeline complete | run_id={result.get('run_id')} "
            f"jobs_persisted={result.get('jobs_persisted')} "
            f"wall_ms={elapsed}"
        )
        return result

    except Exception as exc:
        elapsed = int((time.monotonic() - start_ts) * 1000)
        countdown = 2 ** self.request.retries * 60  # 60 → 120 → 240 s

        logger.exception(
            f"[discovery] Pipeline failed after {elapsed}ms "
            f"(attempt {self.request.retries + 1}/{self.max_retries + 1}): {exc}"
        )

        if self.request.retries < self.max_retries:
            logger.info(f"[discovery] Retrying in {countdown}s …")
            raise self.retry(exc=exc, countdown=countdown)

        # All retries exhausted — return a graceful error dict instead of
        # raising so the task doesn't land in the dead-letter queue as a crash.
        logger.error(
            f"[discovery] All {self.max_retries} retries exhausted. "
            f"Pipeline will be rescheduled by the beat scheduler."
        )
        return {
            "run_id": None,
            "jobs_persisted": 0,
            "duration_ms": elapsed,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Convenience Task — Fire-and-Forget Dispatcher
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.workers.discovery.run_all_connectors",
)
def run_all_connectors() -> Dict[str, Any]:
    """
    Convenience task that enqueues a full discovery pipeline run.

    Called by the Celery Beat scheduler every SCHEDULE_DISCOVERY_INTERVAL_MIN.
    Returns the enqueued Celery task_id so callers can track progress.

    Returns:
        {"task_id": str, "status": "dispatched"}
    """
    logger.info("[discovery] Dispatching run_discovery_pipeline task …")
    task = run_discovery_pipeline.delay()
    logger.info(f"[discovery] Dispatched run_discovery_pipeline | task_id={task.id}")
    return {"task_id": task.id, "status": "dispatched"}
