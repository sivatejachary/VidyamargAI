"""
Autonomous Scheduler — periodically runs background agents and workers
using APScheduler. Decouples background processes from web request flows.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.workers.discovery_worker import run_discovery_all_candidates

logger = logging.getLogger("app.scheduler")

scheduler = AsyncIOScheduler()


def start_scheduler():
    """Starts the background scheduler and registers cron/interval jobs."""
    try:
        # Run job discovery every 10 minutes
        scheduler.add_job(
            run_discovery_all_candidates,
            "interval",
            minutes=10,
            id="job_discovery_worker",
            replace_existing=True
        )
        scheduler.start()
        logger.info("APScheduler AsyncIOScheduler started and discovery worker registered")
    except Exception as e:
        logger.error(f"Failed to start APScheduler: {e}")


def shutdown_scheduler():
    """Gracefully shuts down the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler AsyncIOScheduler shut down")
