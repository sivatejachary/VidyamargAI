"""
VidyaMarg AI — Job Discovery Manager
Orchestrates all connectors, handles rate limiting and health monitoring.
"""
import logging
import time
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.job_models import JobSource

logger = logging.getLogger("app.services.job_discovery")


class JobDiscoveryManager:
    """
    Manages all job discovery connectors.
    Selects active, healthy connectors and aggregates results.
    """

    def __init__(self, db: Session):
        self.db = db

    def discover_jobs(
        self,
        roles: List[str],
        locations: List[str],
        skills: List[str],
        candidate_id: int,
        max_per_source: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Run discovery across all active connectors.
        Returns deduplicated list of raw job dicts.
        """
        all_jobs: List[Dict[str, Any]] = []
        seen_ids: set = set()

        # Get active sources ordered by priority
        sources = (
            self.db.query(JobSource)
            .filter(JobSource.is_active == True, JobSource.consecutive_failures < 5)
            .order_by(JobSource.priority.asc())
            .all()
        )

        for source in sources:
            try:
                connector = self._get_connector(source.name)
                if not connector:
                    continue

                logger.info(f"[Discovery] Running connector: {source.name}")
                t0 = time.time()

                jobs = connector.search(
                    roles=roles[:5],
                    locations=locations[:3],
                    skills=skills[:10],
                    max_results=max_per_source,
                )

                # Dedup by external_id
                new_jobs = []
                for job in jobs:
                    ext_id = job.get("external_id")
                    if ext_id and ext_id in seen_ids:
                        continue
                    if ext_id:
                        seen_ids.add(ext_id)
                    job["source_name"] = source.name
                    new_jobs.append(job)

                all_jobs.extend(new_jobs)
                elapsed = int((time.time() - t0) * 1000)

                # Update source health
                source.last_success_at = datetime.utcnow()
                source.consecutive_failures = 0
                source.total_jobs_discovered = (source.total_jobs_discovered or 0) + len(new_jobs)
                self.db.commit()

                logger.info(f"[Discovery] {source.name}: {len(new_jobs)} jobs in {elapsed}ms")

            except Exception as e:
                logger.error(f"[Discovery] Connector {source.name} failed: {e}")
                source.last_failure_at = datetime.utcnow()
                source.consecutive_failures = (source.consecutive_failures or 0) + 1
                source.health_score = max(0.0, (source.health_score or 1.0) - 0.1)
                self.db.commit()

        logger.info(f"[Discovery] Total discovered: {len(all_jobs)} raw jobs")
        return all_jobs

    def _get_connector(self, source_name: str):
        """Factory — returns connector instance for a source."""
        from app.services.job_discovery.serper_connector import SerperJobsConnector
        from app.services.job_discovery.remoteok_connector import RemoteOKConnector
        from app.services.job_discovery.telegram_connector import TelegramJobsConnector

        connectors = {
            "serper_jobs": SerperJobsConnector,
            "remoteok": RemoteOKConnector,
            "telegram": TelegramJobsConnector,
        }
        cls = connectors.get(source_name)
        if cls:
            return cls()
        return None
