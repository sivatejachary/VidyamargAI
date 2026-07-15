"""
Autonomous Scheduler — periodically runs background agents and workers
using APScheduler. Decouples background processes from web request flows.
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("app.scheduler")

scheduler = AsyncIOScheduler()



async def run_hourly_recommendation_updates():
    """
    Hourly updates of recommendations for active candidates.
    """
    from app.core.database import SessionLocal
    from app.models.job_models import CandidateAgent
    from app.agents.career_supervisor import career_supervisor
    
    logger.info("Scheduler: Triggering hourly recommendation updates...")
    with SessionLocal() as db:
        active_agents = db.query(CandidateAgent).filter(CandidateAgent.status == "active").all()
        for agent in active_agents:
            try:
                logger.info(f"Scheduler: Re-running matching engine for Candidate ID {agent.candidate_id}")
                career_supervisor.run(
                    db=db,
                    candidate_id=agent.candidate_id,
                    run_type="matching",
                    trigger="scheduled"
                )
            except Exception as e:
                logger.error(f"Scheduler: Hourly matching update failed for candidate {agent.candidate_id}: {e}")


async def run_periodic_alerts():
    """
    Checks for unread agent notifications.
    """
    from app.core.database import SessionLocal
    from app.models.job_models import AgentNotification
    
    logger.info("Scheduler: Processing notifications/alerts...")
    with SessionLocal() as db:
        unread = db.query(AgentNotification).filter(AgentNotification.is_read == False).limit(100).all()
        if unread:
            logger.info(f"Scheduler: Found {len(unread)} unread notifications.")



def start_scheduler():
    """Starts the background scheduler and registers cron/interval jobs."""
    try:
        # 1. Recommendation updates (hourly)
        scheduler.add_job(
            run_hourly_recommendation_updates,
            'interval',
            hours=1,
            id='run_hourly_recommendation_updates',
            replace_existing=True
        )

        # 2. Notification alerts check (every 15 minutes)
        scheduler.add_job(
            run_periodic_alerts,
            'interval',
            minutes=15,
            id='run_periodic_alerts',
            replace_existing=True
        )

        scheduler.start()
        logger.info("APScheduler AsyncIOScheduler started successfully with recommendation & alert jobs registered.")
    except Exception as e:
        logger.error(f"Failed to start APScheduler: {e}")


def shutdown_scheduler():
    """Gracefully shuts down the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler AsyncIOScheduler shut down")
