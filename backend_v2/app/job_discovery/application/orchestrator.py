"""
VidyaMarg AI — Discovery Orchestrator
=======================================
The central pipeline coordinator for the autonomous job discovery system.

Pipeline flow:
  1. Generate run_id
  2. Run ALL connectors in parallel (asyncio.gather)
  3. Write raw payloads to Redis Collector Buffer
  4. After ALL connectors complete: pull from buffer
  5. Normalize → Validate → Deduplicate → Enrich
  6. ONE bulk insert into PostgreSQL (never row-by-row)
  7. Publish jobs.persisted.v1 event to Redis Stream
  8. Record crawl history per connector

The orchestrator does NOT handle embedding or matching.
Those are triggered via domain events consumed by dedicated workers.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.job_discovery import config as cfg
from app.job_discovery.application.services.deduplicator import JobDeduplicator
from app.job_discovery.application.services.enricher import JobEnricher
from app.job_discovery.application.services.normalizer import JobNormalizer
from app.job_discovery.application.services.validator import JobValidator
from app.job_discovery.connectors.registry import get_registry
from app.job_discovery.domain.events import JobsPersistedEvent
from app.job_discovery.domain.models import EnrichedJob, JobLifecycle, RawJob
from app.job_discovery.infrastructure.database.repository import (
    CompanyRepository,
    CrawlHistoryRepository,
    JobEventRepository,
    JobRepository,
    JobSourceRepository,
)
from app.job_discovery.infrastructure.database.session import get_async_session
from app.job_discovery.infrastructure.redis.buffer import get_collector_buffer
from app.job_discovery.infrastructure.redis.stream import get_event_broker

logger = logging.getLogger("jd.orchestrator")


@dataclass
class PipelineRunReport:
    """Summary of a complete pipeline execution."""
    run_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    connectors_run: int = 0
    connectors_succeeded: int = 0
    connectors_failed: int = 0
    raw_jobs_discovered: int = 0
    jobs_normalized: int = 0
    jobs_validated: int = 0
    jobs_deduplicated: int = 0
    jobs_rejected: int = 0
    jobs_persisted: int = 0
    companies_created: int = 0
    duration_ms: int = 0
    error: Optional[str] = None

    def finalize(self) -> None:
        self.completed_at = datetime.utcnow()
        self.duration_ms = int(
            (self.completed_at - self.started_at).total_seconds() * 1000
        )


class DiscoveryOrchestrator:
    """
    Orchestrates the full discovery pipeline from crawling to persistence.
    Designed to be called by the Celery Discovery Worker every 30 minutes.
    """

    def __init__(self) -> None:
        self._normalizer = JobNormalizer()
        self._validator = JobValidator()
        self._deduplicator = JobDeduplicator()
        self._enricher = JobEnricher(openai_api_key=cfg.OPENAI_API_KEY)
        self._registry = get_registry()
        self._buffer = get_collector_buffer()
        self._broker = get_event_broker()

    async def run(
        self,
        query_params: Optional[Dict[str, Any]] = None,
    ) -> PipelineRunReport:
        """
        Executes a full discovery → normalization → persistence pipeline run.
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        report = PipelineRunReport(run_id=run_id)
        correlation_id = str(uuid.uuid4())

        logger.info(f"=== Discovery Run START: {run_id} ===")

        default_params = {
            "roles": ["software engineer", "backend engineer", "data engineer", "ml engineer"],
            "locations": ["India", "Remote"],
            "skills": ["python", "javascript", "go"],
        }
        params = {**default_params, **(query_params or {})}

        # ------------------------------------------------------------------
        # Phase 1: Run ALL connectors in parallel
        # ------------------------------------------------------------------
        connectors = self._registry.get_enabled_connectors()
        report.connectors_run = len(connectors)

        if not connectors:
            logger.warning("No active connectors available. Run aborted.")
            report.error = "no_active_connectors"
            report.finalize()
            return report

        logger.info(f"Running {len(connectors)} connectors in parallel for run {run_id}")

        connector_tasks = [
            self._run_single_connector(connector, params, run_id, correlation_id)
            for connector in connectors
        ]
        connector_results = await asyncio.gather(*connector_tasks, return_exceptions=True)

        for i, result in enumerate(connector_results):
            connector_name = connectors[i].name
            if isinstance(result, Exception):
                logger.error(f"[{connector_name}] Fatal error: {result}")
                self._registry.record_failure(connector_name)
                report.connectors_failed += 1
            elif result:
                report.connectors_succeeded += 1
                report.raw_jobs_discovered += result
            else:
                report.connectors_failed += 1

        logger.info(
            f"Connector phase complete: {report.connectors_succeeded} succeeded, "
            f"{report.connectors_failed} failed, "
            f"{report.raw_jobs_discovered} raw jobs buffered"
        )

        # ------------------------------------------------------------------
        # Phase 2: Pull from Redis Buffer and process the batch
        # ------------------------------------------------------------------
        raw_payloads = await self._buffer.get_all_raw(run_id)
        if not raw_payloads:
            logger.info(f"No jobs in buffer for run {run_id}. Pipeline complete.")
            report.finalize()
            return report

        # Reconstruct RawJob objects from buffer payloads
        from datetime import datetime
        raw_jobs: List[RawJob] = []
        for payload in raw_payloads:
            try:
                fields = {
                    k: v for k, v in payload.items()
                    if k in RawJob.__dataclass_fields__
                }
                if isinstance(fields.get("discovered_at"), str):
                    try:
                        fields["discovered_at"] = datetime.fromisoformat(fields["discovered_at"])
                    except ValueError:
                        pass
                if isinstance(fields.get("posted_at"), str) and fields["posted_at"]:
                    try:
                        # Clean up timezone suffixes if present (replace Z with +00:00)
                        val = fields["posted_at"].replace("Z", "+00:00")
                        fields["posted_at"] = datetime.fromisoformat(val)
                    except ValueError:
                        pass
                raw_jobs.append(RawJob(**fields))
            except Exception as exc:
                logger.warning(f"Failed to reconstruct RawJob from buffer: {exc}")

        logger.info(f"Processing {len(raw_jobs)} raw jobs from buffer")

        # ------------------------------------------------------------------
        # Phase 3: Normalize
        # ------------------------------------------------------------------
        normalized = self._normalizer.normalize_batch(raw_jobs)
        report.jobs_normalized = len(normalized)

        # ------------------------------------------------------------------
        # Phase 4: Validate
        # ------------------------------------------------------------------
        validated, rejected = self._validator.validate_batch(normalized)
        report.jobs_validated = len(validated)
        report.jobs_rejected += len(rejected)

        if not validated:
            logger.info("No valid jobs after validation. Pipeline complete.")
            report.finalize()
            return report

        # ------------------------------------------------------------------
        # Phase 5: Enrich (AI metadata, freshness, skill graphs)
        # ------------------------------------------------------------------
        enriched = await self._enricher.enrich_batch(validated)

        # ------------------------------------------------------------------
        # Phase 6: Deduplicate (async DB checks)
        # ------------------------------------------------------------------
        async with get_async_session() as session:
            job_repo = JobRepository(session)
            source_repo = JobSourceRepository(session)
            company_repo = CompanyRepository(session)
            crawl_repo = CrawlHistoryRepository(session)
            event_repo = JobEventRepository(session)

            # Build source_id_map for deduplication
            source_id_map: Dict[str, int] = {}
            for job in enriched:
                if job.source_name not in source_id_map:
                    source_id = await source_repo.get_or_create(
                        name=job.source_name,
                        display_name=job.source_name.title(),
                        source_type="scraper",
                    )
                    source_id_map[job.source_name] = source_id

            unique_jobs, dupe_log = await self._deduplicator.deduplicate(
                enriched, job_repo, source_id_map
            )
            report.jobs_deduplicated = len(dupe_log)
            report.jobs_rejected += len(dupe_log)

            if not unique_jobs:
                logger.info(f"All jobs were duplicates for run {run_id}.")
                report.finalize()
                return report

            # ------------------------------------------------------------------
            # Phase 7: Bulk Persist Companies
            # ------------------------------------------------------------------
            company_dicts = []
            seen_companies = set()
            for job in unique_jobs:
                if job.company_normalized not in seen_companies:
                    seen_companies.add(job.company_normalized)
                    company_dicts.append({
                        "name": job.company_name,
                        "normalized_name": job.company_normalized,
                        "industry": job.industry or "",
                        "trust_score": job.trust_score,
                    })

            company_id_map = await company_repo.bulk_upsert_companies(company_dicts)
            report.companies_created = len(company_id_map)

            # ------------------------------------------------------------------
            # Phase 8: Build job mappings and bulk insert
            # ------------------------------------------------------------------
            job_mappings = [
                self._to_job_mapping(job, company_id_map, source_id_map)
                for job in unique_jobs
            ]
            inserted_ids = await job_repo.bulk_insert_jobs(job_mappings)
            report.jobs_persisted = len(inserted_ids)

            # ------------------------------------------------------------------
            # Phase 9: Record crawl history
            # ------------------------------------------------------------------
            for connector_name, source_id in source_id_map.items():
                count = sum(1 for j in unique_jobs if j.source_name == connector_name)
                await crawl_repo.complete_run(
                    run_id=run_id,
                    source_name=connector_name,
                    status="success",
                    jobs_found=count,
                    jobs_saved=count,
                    jobs_deduplicated=len(dupe_log),
                    jobs_rejected=len(rejected),
                    execution_ms=0,
                )

            # ------------------------------------------------------------------
            # Phase 10: Publish jobs.persisted.v1 event
            # ------------------------------------------------------------------
            event = JobsPersistedEvent.create(
                run_id=run_id,
                job_ids=inserted_ids,
                companies_created=report.companies_created,
                correlation_id=correlation_id,
            )
            await self._broker.publish(event)
            await event_repo.append(event.to_dict())

        report.finalize()
        logger.info(
            f"=== Discovery Run COMPLETE: {run_id} | "
            f"{report.jobs_persisted} jobs persisted | "
            f"{report.duration_ms}ms ==="
        )
        return report

    async def _run_single_connector(
        self,
        connector: Any,
        query_params: Dict[str, Any],
        run_id: str,
        correlation_id: str,
    ) -> int:
        """
        Runs a single connector, writes results to the buffer, records stats.
        Returns the number of raw jobs buffered, or 0 on failure.
        Catches all exceptions — never propagates failures to the orchestrator.
        """
        connector_name = connector.name
        start_time = asyncio.get_event_loop().time()

        try:
            # Health check first
            is_healthy = await asyncio.wait_for(
                connector.health_check(),
                timeout=10.0,
            )
            if not is_healthy:
                logger.warning(f"[{connector_name}] Failed health check. Skipping.")
                self._registry.record_failure(connector_name)
                return 0

            # Authenticate
            await asyncio.wait_for(connector.authenticate(), timeout=15.0)

            # Discover jobs with overall timeout
            result = await asyncio.wait_for(
                connector.discover_jobs(query_params),
                timeout=cfg.CONNECTOR_TIMEOUT_SECONDS,
            )

            elapsed_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

            if not result.success:
                logger.warning(
                    f"[{connector_name}] discovery failed: {result.error_message}"
                )
                self._registry.record_failure(connector_name)
                return 0

            # Write to buffer
            if result.jobs:
                raw_dicts = [vars(job) for job in result.jobs]
                await self._buffer.push_raw_jobs(run_id, connector_name, raw_dicts)

            self._registry.record_success(connector_name)
            logger.info(
                f"[{connector_name}] ✓ {result.jobs_found} jobs | {elapsed_ms}ms"
            )
            return result.jobs_found

        except asyncio.TimeoutError:
            logger.error(f"[{connector_name}] Timeout after {cfg.CONNECTOR_TIMEOUT_SECONDS}s")
            self._registry.record_failure(connector_name)
            return 0
        except Exception as exc:
            logger.error(f"[{connector_name}] Unexpected error: {exc}")
            self._registry.record_failure(connector_name)
            return 0

    def _to_job_mapping(
        self,
        job: EnrichedJob,
        company_id_map: Dict[str, int],
        source_id_map: Dict[str, int],
    ) -> Dict[str, Any]:
        """Converts an EnrichedJob domain object to a DB column mapping dict."""
        return {
            "external_id": job.external_id,
            "source_id": source_id_map.get(job.source_name),
            "company_id": company_id_map.get(job.company_normalized),
            "title": job.title,
            "title_normalized": job.title_normalized,
            "company_name": job.company_name,
            "description": job.description,
            "description_summary": job.description_summary,
            "apply_url": job.apply_url,
            "job_url": job.job_url,
            "location": job.location,
            "city": job.city,
            "state": job.state,
            "country": job.country,
            "is_remote": job.is_remote,
            "is_hybrid": job.is_hybrid,
            "work_mode": job.work_mode.value,
            "employment_type": job.employment_type.value,
            "seniority": job.seniority.value,
            "role_category": job.role_category,
            "role_sub_category": job.role_sub_category,
            "industry": job.industry,
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
            "skill_graph": job.skill_graph,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_currency": job.salary_currency,
            "salary_period": job.salary_period,
            "salary_raw": job.salary_raw,
            "experience_min_years": job.experience_min_years,
            "experience_max_years": job.experience_max_years,
            "trust_score": job.trust_score,
            "quality_score": job.quality_score,
            "freshness_score": job.freshness_score,
            "spam_score": job.spam_score,
            "is_active": True,
            "is_verified": True,
            "lifecycle_status": JobLifecycle.PERSISTED.value,
            "posted_at": job.posted_at,
            "qdrant_sync_pending": True,   # Embedding worker picks this up
            "discovered_at": job.discovered_at,
        }
