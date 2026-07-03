import logging
import time
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import asyncio

from app.models.job_models import JobSource
from app.job_discovery.connectors.serper import SerperJobsConnector
from app.job_discovery.connectors.remoteok import RemoteOKConnector
from app.job_discovery.connectors.telegram import TelegramJobsConnector

from app.job_discovery.normalizer.normalizer import JobNormalizer
from app.job_discovery.validator.validator import JobValidator
from app.job_discovery.deduplicator.deduplicator import JobDeduplicator
from app.job_discovery.persistence.manager import JobPersistenceManager
from app.job_discovery.events.dispatcher import JobEventDispatcher

logger = logging.getLogger("app.job_discovery.crawler.orchestrator")

class DiscoveryOrchestrator:
    """
    Orchestrates the entire Job Discovery bounded context pipeline.
    Runs connectors, normalizes, validates, deduplicates, persists,
    and publishes versioned event streams.
    """

    def __init__(self, db: Session):
        self.db = db
        self.normalizer = JobNormalizer()
        self.validator = JobValidator()
        self.deduplicator = JobDeduplicator()
        self.persistence = JobPersistenceManager()
        self.dispatcher = JobEventDispatcher()

    def run_discovery(
        self,
        roles: List[str],
        locations: List[str],
        skills: List[str],
        max_per_source: int = 50,
    ) -> List[int]:
        """
        Runs job discovery and triggers the event-driven processing pipeline.
        Returns a list of persisted Job database IDs.
        """
        persisted_ids = []
        
        # 1. Fetch active, healthy job sources
        sources = (
            self.db.query(JobSource)
            .filter(JobSource.is_active == True, JobSource.consecutive_failures < 5)
            .order_by(JobSource.priority.asc())
            .all()
        )

        logger.info(f"DiscoveryOrchestrator: Starting run across {len(sources)} active sources.")

        for source in sources:
            try:
                connector = self._get_connector(source.name)
                if not connector:
                    continue

                logger.info(f"DiscoveryOrchestrator: Running source '{source.name}'")
                t0 = time.time()

                # 2. Search raw listings
                raw_jobs = connector.search(
                    roles=roles[:5],
                    locations=locations[:3],
                    skills=skills[:10],
                    max_results=max_per_source,
                )

                source_persisted_count = 0
                source_rejected_count = 0

                for raw_job in raw_jobs:
                    # 3. Normalization
                    norm_job = self.normalizer.normalize(raw_job)
                    norm_job["source_name"] = source.name

                    # 4. Validation
                    rejection_reason = self.validator.validate(norm_job)
                    if rejection_reason:
                        source_rejected_count += 1
                        continue

                    # 5. Deduplication
                    if self.deduplicator.is_duplicate(norm_job, self.db):
                        continue

                    # 6. Persistence (lifecycle_status = "persisted")
                    try:
                        job_record = self.persistence.persist_job(norm_job, self.db)
                        self.db.commit()
                        
                        source_persisted_count += 1
                        persisted_ids.append(job_record.id)

                        # 7. Event Dispatching (jobs.persisted.v1)
                        # Launch as a non-blocking background task
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(
                                self.dispatcher.publish_persisted(
                                    job_id=job_record.id,
                                    title=job_record.title,
                                    company=job_record.company_name
                                )
                            )
                        except RuntimeError:
                            # Fallback if no running event loop
                            asyncio.run(
                                self.dispatcher.publish_persisted(
                                    job_id=job_record.id,
                                    title=job_record.title,
                                    company=job_record.company_name
                                )
                            )

                    except Exception as e:
                        logger.error(f"Failed to persist job '{norm_job.get('title')}': {e}")
                        self.db.rollback()

                # Update connector health
                elapsed = int((time.time() - t0) * 1000)
                source.last_success_at = datetime.utcnow()
                source.consecutive_failures = 0
                source.total_jobs_discovered = (source.total_jobs_discovered or 0) + len(raw_jobs)
                source.total_jobs_accepted = (source.total_jobs_accepted or 0) + source_persisted_count
                source.total_jobs_rejected = (source.total_jobs_rejected or 0) + source_rejected_count
                self.db.commit()

                logger.info(f"DiscoveryOrchestrator: Completed '{source.name}' in {elapsed}ms. Persisted: {source_persisted_count}, Rejected: {source_rejected_count}")

            except Exception as e:
                logger.error(f"DiscoveryOrchestrator: Connector '{source.name}' failed: {e}")
                source.last_failure_at = datetime.utcnow()
                source.consecutive_failures = (source.consecutive_failures or 0) + 1
                source.health_score = max(0.0, (source.health_score or 1.0) - 0.1)
                self.db.commit()

        logger.info(f"DiscoveryOrchestrator: Run completed. Total persisted jobs: {len(persisted_ids)}")
        return persisted_ids

    def _get_connector(self, source_name: str):
        connectors = {
            "serper_jobs": SerperJobsConnector,
            "remoteok": RemoteOKConnector,
            "telegram": TelegramJobsConnector,
        }
        cls = connectors.get(source_name)
        return cls() if cls else None
