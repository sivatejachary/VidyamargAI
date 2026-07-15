"""
Discovery Orchestrator — Full async parallel rewrite.

Key fixes vs legacy:
  1. run_discovery() is now a true async method (was sync, blocking the thread)
  2. All connectors run concurrently via asyncio.gather — no serial source loop
  3. dispatch_persisted is properly awaited (was fire-and-forget with no await)
  4. A single shared httpx.AsyncClient is passed down to every connector
  5. DB writes use a context-managed session, rolled back on error per source
  6. Source health telemetry is updated atomically after each connector batch
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

import httpx
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.job_models import JobSource
from app.job_discovery.connectors.serper import SerperJobsConnector
from app.job_discovery.connectors.linkedin import LinkedInConnector
from app.job_discovery.connectors.linkedin_posts import LinkedInPostsConnector
from app.job_discovery.connectors.naukri import NaukriConnector
from app.job_discovery.connectors.telegram import TelegramJobsConnector
from app.job_discovery.connectors.base import BaseConnector
from app.job_discovery.normalizer.normalizer import JobNormalizer
from app.job_discovery.validator.validator import JobValidator
from app.job_discovery.deduplicator.deduplicator import JobDeduplicator
from app.job_discovery.persistence.manager import JobPersistenceManager
from app.job_discovery.events.dispatcher import JobEventDispatcher

logger = logging.getLogger("app.job_discovery.crawler.orchestrator")

# Registry: source name → connector class
_CONNECTOR_REGISTRY: Dict[str, type[BaseConnector]] = {
    "serper_jobs": SerperJobsConnector,
    "linkedin": LinkedInConnector,
    "linkedin_posts": LinkedInPostsConnector,
    "naukri": NaukriConnector,
    "telegram": TelegramJobsConnector,
}




class DiscoveryOrchestrator:
    """
    Orchestrates the entire Job Discovery bounded context pipeline.

    Usage (from scheduler / startup):
        orchestrator = DiscoveryOrchestrator()
        job_ids = await orchestrator.run_discovery(roles, locations, skills)
    """

    def __init__(self) -> None:
        self.normalizer = JobNormalizer()
        self.validator = JobValidator()
        self.deduplicator = JobDeduplicator()
        self.persistence = JobPersistenceManager()
        self.dispatcher = JobEventDispatcher()

    # ─── Public API ───────────────────────────────────────────────────────────

    async def run_discovery(
        self,
        roles: List[str],
        locations: List[str],
        skills: List[str],
        max_per_source: int = 50,
    ) -> List[int]:
        """
        Run all active connectors in parallel and persist new jobs.
        Returns a list of newly created Job IDs.
        """
        with SessionLocal() as db:
            sources = (
                db.query(JobSource)
                .filter(
                    JobSource.is_active == True,  # noqa: E712
                    JobSource.consecutive_failures < 5,
                )
                .order_by(JobSource.priority.asc())
                .all()
            )
            # Snapshot source data so we don't hold the session open across I/O
            source_snapshots = [
                {"id": s.id, "name": s.name}
                for s in sources
                if s.name in _CONNECTOR_REGISTRY
            ]

        if not source_snapshots:
            logger.info("[Orchestrator] No active/healthy sources found.")
            return []

        logger.info(
            f"[Orchestrator] Starting discovery across {len(source_snapshots)} sources: "
            f"{[s['name'] for s in source_snapshots]}"
        )

        # Single shared httpx client for all connectors
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
        ) as shared_client:
            tasks = [
                self._run_source(
                    source_name=snap["name"],
                    source_id=snap["id"],
                    roles=roles,
                    locations=locations,
                    skills=skills,
                    max_per_source=max_per_source,
                    client=shared_client,
                )
                for snap in source_snapshots
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        all_ids: List[int] = []
        for snap, result in zip(source_snapshots, results):
            if isinstance(result, Exception):
                logger.error(
                    f"[Orchestrator] Source '{snap['name']}' raised unhandled exception: {result}"
                )
                await self._record_failure(snap["id"])
            else:
                all_ids.extend(result)

        logger.info(
            f"[Orchestrator] Discovery complete. Total new jobs persisted: {len(all_ids)}"
        )
        return all_ids

    # ─── Per-source runner ────────────────────────────────────────────────────

    async def _run_source(
        self,
        source_name: str,
        source_id: int,
        roles: List[str],
        locations: List[str],
        skills: List[str],
        max_per_source: int,
        client: httpx.AsyncClient,
    ) -> List[int]:
        connector_cls = _CONNECTOR_REGISTRY.get(source_name)
        if not connector_cls:
            logger.warning(f"[Orchestrator] No connector registered for '{source_name}'")
            return []

        connector: BaseConnector = connector_cls()
        t0 = time.monotonic()

        try:
            raw_jobs = await connector.async_search(
                roles=roles[:5],
                locations=locations[:3],
                skills=skills[:10],
                max_results=max_per_source,
                client=client,
            )
        except Exception as exc:
            logger.error(f"[Orchestrator] Connector '{source_name}' search error: {exc}")
            await self._record_failure(source_id)
            return []

        persisted_ids: List[int] = []
        accepted = rejected = 0

        with SessionLocal() as db:
            for raw_job in raw_jobs:
                try:
                    norm_job = self.normalizer.normalize(raw_job)
                    norm_job["source_name"] = source_name

                    rejection_reason = self.validator.validate(norm_job)
                    if rejection_reason:
                        rejected += 1
                        continue

                    if self.deduplicator.is_duplicate(norm_job, db):
                        continue

                    job_record = self.persistence.persist_job(norm_job, db)
                    db.commit()
                    persisted_ids.append(job_record.id)
                    accepted += 1

                except Exception as exc:
                    logger.error(
                        f"[Orchestrator] Failed to persist job "
                        f"'{raw_job.get('title', '?')}' from '{source_name}': {exc}"
                    )
                    db.rollback()

            # Update source health telemetry
            await self._record_success(
                source_id=source_id,
                db=db,
                discovered=len(raw_jobs),
                accepted=accepted,
                rejected=rejected,
            )

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            f"[Orchestrator] '{source_name}' completed in {elapsed_ms}ms — "
            f"raw={len(raw_jobs)}, accepted={accepted}, rejected={rejected}"
        )

        # Dispatch persisted events for all new jobs (all awaited properly)
        await asyncio.gather(
            *(
                self.dispatcher.publish_persisted(
                    job_id=jid,
                    title="",   # title not held in memory — worker fetches from DB
                    company="",
                )
                for jid in persisted_ids
            ),
            return_exceptions=True,
        )

        return persisted_ids

    # ─── Telemetry helpers ────────────────────────────────────────────────────

    async def _record_success(
        self,
        source_id: int,
        db: Session,
        discovered: int,
        accepted: int,
        rejected: int,
    ) -> None:
        try:
            source = db.query(JobSource).filter(JobSource.id == source_id).first()
            if source:
                source.last_success_at = datetime.utcnow()
                source.consecutive_failures = 0
                source.health_score = min(1.0, (source.health_score or 0.9) + 0.02)
                source.total_jobs_discovered = (source.total_jobs_discovered or 0) + discovered
                source.total_jobs_accepted = (source.total_jobs_accepted or 0) + accepted
                source.total_jobs_rejected = (source.total_jobs_rejected or 0) + rejected
                db.commit()
        except Exception as exc:
            logger.error(f"[Orchestrator] Failed to update source health: {exc}")

    async def _record_failure(self, source_id: int) -> None:
        try:
            with SessionLocal() as db:
                source = db.query(JobSource).filter(JobSource.id == source_id).first()
                if source:
                    source.last_failure_at = datetime.utcnow()
                    source.consecutive_failures = (source.consecutive_failures or 0) + 1
                    source.health_score = max(0.0, (source.health_score or 1.0) - 0.15)
                    db.commit()
        except Exception as exc:
            logger.error(f"[Orchestrator] Could not record failure for source {source_id}: {exc}")
