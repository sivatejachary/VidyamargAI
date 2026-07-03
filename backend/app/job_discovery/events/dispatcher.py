from typing import Dict, Any
from app.core.event_bus import event_bus
import logging

logger = logging.getLogger("app.job_discovery.events.dispatcher")

class JobEventDispatcher:
    async def publish_persisted(self, job_id: int, title: str, company: str):
        """
        Dispatches the jobs.persisted.v1 event.
        """
        event = {
            "job_id": job_id,
            "title": title,
            "company": company,
            "lifecycle_status": "persisted"
        }
        await event_bus.publish("jobs.persisted.v1", event)
        logger.debug(f"Dispatched jobs.persisted.v1 for Job ID {job_id}")

    async def publish_embedded(self, job_id: int):
        """
        Dispatches the jobs.embedded.v1 event.
        """
        event = {
            "job_id": job_id,
            "embedding_id": f"job_{job_id}",
            "lifecycle_status": "embedded"
        }
        await event_bus.publish("jobs.embedded.v1", event)
        logger.debug(f"Dispatched jobs.embedded.v1 for Job ID {job_id}")

    async def publish_matched(self, job_id: int, matches: list):
        """
        Dispatches the jobs.matched.v1 event.
        """
        event = {
            "job_id": job_id,
            "matches": matches,
            "lifecycle_status": "matched"
        }
        await event_bus.publish("jobs.matched.v1", event)
        logger.debug(f"Dispatched jobs.matched.v1 for Job ID {job_id}")

    async def publish_recommendation_created(self, candidate_id: int, recommendations: list):
        """
        Dispatches the recommendations.created.v1 event.
        """
        event = {
            "candidate_id": candidate_id,
            "recommendations": recommendations
        }
        await event_bus.publish("recommendations.created.v1", event)
        logger.debug(f"Dispatched recommendations.created.v1 for Candidate ID {candidate_id}")
