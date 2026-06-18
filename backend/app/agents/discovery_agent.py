import logging
import asyncio
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.core.events import publish_event_sync

logger = logging.getLogger("app.agents.discovery")


class DiscoveryAgent:
    def __init__(self):
        self.connectors = []

    async def discover_jobs(self, user_id: int, query: str, skills: List[str], db: Session, log_cb=None) -> List[Dict[str, Any]]:
        """Scans all registered connectors for new job opportunities."""
        if log_cb:
            log_cb(f"Starting real job discovery scan for query: '{query}'", "info")

        from app.agents.search import SearchAgent
        from app.agents.telegram import TelegramCommunityAgent

        search_agent = SearchAgent([query], skills, 1.0)
        telegram_agent = TelegramCommunityAgent(db)

        loop = asyncio.get_event_loop()

        def run_portal():
            try:
                # search_agent.execute_search returns List[LiveJob]
                return search_agent.execute_search(lambda m, s="info": log_cb(f"[Portal] {m}", s) if log_cb else None)
            except Exception as e:
                logger.error(f"Portal search crawler failed: {e}")
                return []

        def run_telegram():
            try:
                return telegram_agent.collect_jobs(lambda m, s="info": log_cb(f"[Telegram] {m}", s) if log_cb else None)
            except Exception as e:
                logger.error(f"Telegram collector failed: {e}")
                return []

        portal_jobs, tg_jobs = await asyncio.gather(
            loop.run_in_executor(None, run_portal),
            loop.run_in_executor(None, run_telegram)
        )

        raw_jobs = []
        for j in (portal_jobs + tg_jobs):
            if hasattr(j, "title"):
                raw_jobs.append({
                    "title": j.title,
                    "company": j.company,
                    "location": j.location,
                    "experience": j.experience,
                    "skills": j.skills,
                    "apply_url": j.apply_url,
                    "source": j.source,
                    "description": j.description
                })
            else:
                raw_jobs.append(j)

        if log_cb:
            log_cb(f"Aggregated {len(raw_jobs)} raw jobs from portals & Telegram. Starting deduplication...", "info")

        # Call Deduplicator Tool (in-process)
        deduplicated = self._deduplicate_jobs(raw_jobs)

        # Call Quality and Fraud Filter Tools
        final_jobs = []
        for job in deduplicated:
            # Simple in-process deduplication and fraud checks
            is_fraud = self._check_fraud(job)
            quality_score = self._calculate_quality(job)
            
            job["fraud_flag"] = is_fraud
            job["quality_score"] = quality_score
            
            if not is_fraud and quality_score >= 40:
                final_jobs.append(job)

        if log_cb:
            log_cb(f"Approved {len(final_jobs)} jobs after filtering. Persisting...", "success")

        # Save to database and publish events
        for job in final_jobs:
            self._persist_job(user_id, job, db)
            publish_event_sync("job_discovered", {"user_id": user_id, "job": job})

        return final_jobs

    def _deduplicate_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicates jobs based on title and company hash."""
        seen = set()
        unique_jobs = []
        for j in jobs:
            key = f"{j['title'].lower().strip()}:{j['company'].lower().strip()}"
            if key not in seen:
                seen.add(key)
                unique_jobs.append(j)
        return unique_jobs

    def _check_fraud(self, job: Dict[str, Any]) -> bool:
        """Fraud-detector tool logic: flags suspicious company domains or keywords."""
        desc = job.get("description", "").lower()
        company = job.get("company", "").lower()
        if "wire transfer" in desc or "deposit money" in desc or "anonymous" in company:
            return True
        return False

    def _calculate_quality(self, job: Dict[str, Any]) -> int:
        """Quality-filter tool logic: scores jobs based on details provided."""
        score = 50
        desc = job.get("description", "")
        if len(desc) > 300:
            score += 20
        if job.get("skills"):
            score += 15
        if job.get("location"):
            score += 15
        return min(100, score)

    def _persist_job(self, user_id: int, job_data: Dict[str, Any], db: Session):
        """Saves jobs using mcp-server-jobs direct interface."""
        from app.mcp.gateway import gateway
        # Call store_job tool
        arguments = {
            "title": job_data["title"],
            "description": job_data["description"],
            "required_skills": ", ".join(job_data["skills"]),
            "company_name": job_data["company"],
            "location": job_data["location"]
        }
        # In-process gateway call bypasses permissions since it is called by trusted agent
        try:
            from app.mcp.servers import JobsServer
            JobsServer().store_job(user_id, arguments, db)
        except Exception as e:
            logger.error(f"Failed to persist discovered job: {e}")
