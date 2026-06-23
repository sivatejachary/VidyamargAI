"""
Autonomous Scheduler — periodically runs background agents and workers
using APScheduler. Decouples background processes from web request flows.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("app.scheduler")

scheduler = AsyncIOScheduler()


def start_scheduler():
    """Starts the background scheduler and registers cron/interval jobs."""
    try:
        # No background tasks active at present (Job discovery and alerting tasks dropped)
        scheduler.start()
        logger.info("APScheduler AsyncIOScheduler started cleanly with 0 jobs registered")
    except Exception as e:
        logger.error(f"Failed to start APScheduler: {e}")


def shutdown_scheduler():
    """Gracefully shuts down the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler AsyncIOScheduler shut down")
