"""
Autonomous Scheduler — periodically runs background agents and workers
using APScheduler. Decouples background processes from web request flows.
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("app.scheduler")

scheduler = AsyncIOScheduler()


async def run_periodic_job_sync():
    """
    Runs the native Telegram Job crawler to discover jobs and save them.
    """
    from app.job_agent.agent import run_telegram_crawler
    
    logger.info("Scheduler: Triggering periodic Telegram job crawling...")
    try:
        await run_telegram_crawler()
        logger.info("Scheduler: Job crawling cycle complete.")
    except Exception as e:
        logger.error(f"Scheduler: Job crawling failed: {e}")


async def run_hourly_recommendation_updates():
    """
    Hourly updates of recommendations for active candidates.
    """
    import asyncio
    from app.core.database import SessionLocal
    from app.models.job_models import CandidateAgent
    from app.agents.career_supervisor import career_supervisor
    
    logger.info("Scheduler: Triggering hourly recommendation updates...")
    with SessionLocal() as db:
        active_agents = db.query(CandidateAgent).filter(CandidateAgent.status == "active").all()
        candidate_ids = [agent.candidate_id for agent in active_agents]

    loop = asyncio.get_running_loop()
    for cid in candidate_ids:
        try:
            logger.info(f"Scheduler: Re-running matching engine for Candidate ID {cid}")
            def _run_worker(candidate_id=cid):
                with SessionLocal() as worker_db:
                    career_supervisor.run(
                        db=worker_db,
                        candidate_id=candidate_id,
                        run_type="matching",
                        trigger="scheduled"
                    )
            await loop.run_in_executor(None, _run_worker)
        except Exception as e:
            logger.error(f"Scheduler: Hourly matching update failed for candidate {cid}: {e}")


async def run_periodic_alerts():
    """
    Checks for unread agent notifications.
    """
    import asyncio
    from app.core.database import SessionLocal
    from app.models.job_models import AgentNotification
    
    logger.info("Scheduler: Processing notifications/alerts...")
    def _run():
        with SessionLocal() as db:
            unread = db.query(AgentNotification).filter(AgentNotification.is_read == False).limit(100).all()
            if unread:
                logger.info(f"Scheduler: Found {len(unread)} unread notifications.")
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _run)
    except Exception as e:
        logger.error(f"Scheduler: Alerts check failed: {e}")



async def run_expire_old_telegram_jobs():
    """
    Nightly job: marks Telegram-sourced job posts older than 3 days as
    is_active=FALSE and lifecycle_status='expired' in the main jobs table.
    """
    import sys, os, asyncio
    job_agent_dir = os.path.join(os.path.dirname(__file__), "..", "job_agent")
    if job_agent_dir not in sys.path:
        sys.path.insert(0, os.path.abspath(job_agent_dir))

    logger.info("Scheduler: Running nightly Telegram job expiry (7-day window)...")
    try:
        import db as crawler_db
        loop = asyncio.get_running_loop()
        expired = await loop.run_in_executor(None, lambda: crawler_db.expire_old_telegram_jobs(days=7))
        logger.info(f"Scheduler: Expired {expired} old Telegram job(s).")
    except Exception as e:
        logger.error(f"Scheduler: Telegram job expiry failed: {e}")


def start_scheduler():
    """Starts the background scheduler and registers cron/interval jobs."""
    try:
        # 1. Job Sync Agent (every 10 minutes)
        scheduler.add_job(
            run_periodic_job_sync,
            'interval',
            minutes=10,
            id='run_periodic_job_sync',
            replace_existing=True
        )

        # 2. Recommendation updates (hourly)
        scheduler.add_job(
            run_hourly_recommendation_updates,
            'interval',
            hours=1,
            id='run_hourly_recommendation_updates',
            replace_existing=True
        )

        # 3. Notification alerts check (every 15 minutes)
        scheduler.add_job(
            run_periodic_alerts,
            'interval',
            minutes=15,
            id='run_periodic_alerts',
            replace_existing=True
        )

        # 4. Nightly expiry: remove Telegram jobs older than 3 days (runs at 02:00 UTC)
        scheduler.add_job(
            run_expire_old_telegram_jobs,
            'cron',
            hour=2,
            minute=0,
            id='run_expire_old_telegram_jobs',
            replace_existing=True
        )

        scheduler.start()
        logger.info("APScheduler AsyncIOScheduler started successfully with job sync, recommendation, alert & expiry jobs registered.")
    except Exception as e:
        logger.error(f"Failed to start APScheduler: {e}")


def shutdown_scheduler():
    """Gracefully shuts down the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler AsyncIOScheduler shut down")
