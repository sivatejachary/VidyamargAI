"""
Autonomous Scheduler — periodically runs background agents and workers
using APScheduler. Decouples background processes from web request flows.
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("app.scheduler")

scheduler = AsyncIOScheduler()


async def run_periodic_job_discovery():
    """
    Orchestrates job discovery on an interval of 30 minutes.
    Collects roles and locations from active candidate profiles.

    NOTE: DiscoveryOrchestrator is now fully async — no db constructor arg.
    """
    import json as _json
    from app.core.database import SessionLocal
    from app.models.models import CandidateProfile
    from app.job_discovery.crawler.orchestrator import DiscoveryOrchestrator

    logger.info("Scheduler: Triggering periodic job discovery...")

    roles: set = set()
    locations: set = set()
    skills: set = set()

    with SessionLocal() as db:
        profiles = (
            db.query(CandidateProfile)
            .order_by(CandidateProfile.created_at.desc())
            .limit(50)
            .all()
        )
        for p in profiles:
            if p.skills:
                skills.update(p.skills)
            if hasattr(p, "parsed_metadata") and p.parsed_metadata:
                try:
                    meta = (
                        _json.loads(p.parsed_metadata)
                        if isinstance(p.parsed_metadata, str)
                        else p.parsed_metadata
                    )
                    if meta.get("preferred_roles"):
                        roles.update(meta["preferred_roles"])
                    if meta.get("locations"):
                        locations.update(meta["locations"])
                except Exception:
                    pass

    role_list = list(roles) or ["Software Engineer", "Full Stack Developer", "Backend Engineer"]
    location_list = list(locations) or ["India", "Remote"]
    skill_list = list(skills) or ["Python", "JavaScript", "React"]

    # DiscoveryOrchestrator takes NO db arg — manages its own sessions
    orchestrator = DiscoveryOrchestrator()
    await orchestrator.run_discovery(
        roles=role_list,
        locations=location_list,
        skills=skill_list,
        max_per_source=30,
    )


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


async def clean_expired_jobs():
    """
    Daily cleanup to deactivate expired jobs.
    """
    from app.core.database import SessionLocal
    from app.models.job_models import Job
    
    logger.info("Scheduler: Running daily cleanup for expired jobs...")
    with SessionLocal() as db:
        now = datetime.utcnow()
        expired = db.query(Job).filter(
            Job.is_active == True,
            Job.expires_at < now
        ).all()
        
        if expired:
            logger.info(f"Scheduler: Deactivating {len(expired)} expired jobs.")
            for job in expired:
                job.is_active = False
                job.lifecycle_status = "expired"
            db.commit()


def start_scheduler():
    """Starts the background scheduler and registers cron/interval jobs."""
    try:
        # 1. Job Discovery (every 30 minutes)
        scheduler.add_job(
            run_periodic_job_discovery,
            'interval',
            minutes=30,
            id='run_periodic_job_discovery',
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

        # 4. Cleanup expired jobs (daily at 2 AM)
        scheduler.add_job(
            clean_expired_jobs,
            'cron',
            hour=2,
            id='clean_expired_jobs',
            replace_existing=True
        )

        scheduler.start()
        logger.info("APScheduler AsyncIOScheduler started successfully with 4 jobs registered.")
    except Exception as e:
        logger.error(f"Failed to start APScheduler: {e}")


def shutdown_scheduler():
    """Gracefully shuts down the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler AsyncIOScheduler shut down")
