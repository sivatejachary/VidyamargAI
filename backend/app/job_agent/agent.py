import time
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.job_agent.sync_service import JobSyncService

logger = logging.getLogger("app.job_agent.agent")

class JobSyncAgent:
    """
    Subagent in the Career Intelligence Supervisor pipeline.
    Synchronizes new job postings from the Job Agent database (hayabusa:13794)
    into the local database to make them available for matching and recommendations.
    """
    NAME = "JobSyncAgent"

    def run(self, state: dict, db: Session) -> dict:
        t0 = time.time()
        logger.info(f"[{self.NAME}] Starting job synchronization agent...")
        
        try:
            sync_service = JobSyncService(db)
            # Sync the latest 100 jobs matching the candidate's interests or generic
            synced_count = sync_service.sync_jobs(limit=100)
            
            # Fetch actual jobs from the DB to populate state["discovered_jobs"] if needed
            # For simplicity, we just log the action and count
            state["agent_actions"].append({
                "agent": self.NAME,
                "action": "sync_jobs",
                "status": "completed",
                "duration_ms": int((time.time() - t0) * 1000),
                "output": f"Synchronized {synced_count} jobs from Job Agent database",
            })
            
        except Exception as e:
            logger.error(f"[{self.NAME}] Error: {e}", exc_info=True)
            state["errors"].append(f"{self.NAME}: {str(e)}")
            
        return state
