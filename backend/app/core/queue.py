"""Redis Queue (RQ) infrastructure with Postgres fallback and bounded execution limits."""
from __future__ import annotations

import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from datetime import datetime

logger = logging.getLogger("app.queue")
MAX_FALLBACK_QUEUE = 500

try:
    import redis
    from rq import Queue
    from app.core.config import settings

    redis_conn = redis.Redis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=5,
        socket_timeout=5,
        decode_responses=False,
    )
    high_queue = Queue("high", connection=redis_conn, default_timeout=300)
    default_queue = Queue("default", connection=redis_conn, default_timeout=600)
    low_queue = Queue("low", connection=redis_conn, default_timeout=1800)
    logger.info("RQ queues initialized: high / default / low")
except Exception as exc:
    logger.warning(f"RQ not available ({exc}); queue operations will be skipped")
    redis_conn = None
    high_queue = None
    default_queue = None
    low_queue = None

# Bounded thread pool executor for fallback jobs
fallback_executor = ThreadPoolExecutor(max_workers=3)
redis_failover_active = False

def is_redis_connected() -> bool:
    global redis_failover_active
    if redis_conn is None:
        redis_failover_active = True
        return False
    try:
        redis_conn.ping()
        redis_failover_active = False
        return True
    except Exception:
        redis_failover_active = True
        return False

def get_fallback_queue_depth() -> int:
    from app.core.database import SessionLocal
    from app.models.models import JobAgentRun
    try:
        with SessionLocal() as db:
            return db.query(JobAgentRun).filter(JobAgentRun.status == "queued").count()
    except Exception as e:
        logger.error(f"Error fetching fallback queue depth: {e}")
        return 0

def run_agent_flow_sync_wrapper(run_id: int, candidate_id: int):
    """Sync wrapper that runs the async run_agent_flow."""
    from app.core.database import SessionLocal
    from app.models.models import JobAgentRun
    from app.agents.manager import run_agent_flow
    logger.info(f"Running fallback job for run_id={run_id} candidate_id={candidate_id}")
    
    # Mark as running in DB
    try:
        with SessionLocal() as db:
            run = db.query(JobAgentRun).filter(JobAgentRun.id == run_id).first()
            if run:
                run.status = "running"
                db.commit()
    except Exception as e:
        logger.error(f"Failed to update status to running for fallback job {run_id}: {e}")

    try:
        # Run async function using asyncio.run
        asyncio.run(run_agent_flow(run_id, candidate_id))
    except Exception as e:
        logger.error(f"Error executing fallback agent flow: {e}")
        try:
            with SessionLocal() as db:
                run = db.query(JobAgentRun).filter(JobAgentRun.id == run_id).first()
                if run:
                    run.status = "failed"
                    run.completed_at = datetime.utcnow()
                    db.commit()
        except Exception:
            pass

def enqueue_agent_run(run_id: int, candidate_id: int) -> str:
    """
    Enqueues an agent run job. 
    Uses Redis Queue if available, otherwise falls back to Postgres-backed local executor.
    """
    global redis_failover_active
    from app.core.database import SessionLocal
    from app.models.models import JobAgentRun
    from app.models.mcp_models import DeadLetterJob
    
    if is_redis_connected():
        try:
            default_queue.enqueue(run_agent_flow_sync_wrapper, run_id, candidate_id)
            logger.info(f"Successfully enqueued run_id={run_id} to RQ default queue.")
            return "queued_rq"
        except Exception as exc:
            logger.warning(f"Failed to enqueue to Redis RQ: {exc}. Falling back to DB queue.")
            
    # Fallback to DB queue
    redis_failover_active = True
    depth = get_fallback_queue_depth()
    if depth >= MAX_FALLBACK_QUEUE:
        logger.critical(f"Fallback queue depth ({depth}) exceeds MAX_FALLBACK_QUEUE ({MAX_FALLBACK_QUEUE}). Rejecting job intake!")
        try:
            with SessionLocal() as db:
                dlq = DeadLetterJob(
                    run_id=run_id,
                    candidate_id=candidate_id,
                    job_type="run_agent_flow",
                    arguments={"run_id": run_id, "candidate_id": candidate_id},
                    error_message=f"Intake paused: Fallback queue depth limit {MAX_FALLBACK_QUEUE} exceeded."
                )
                db.add(dlq)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to write DLQ: {e}")
        raise RuntimeError("Intake paused: Fallback queue limit exceeded.")
        
    try:
        with SessionLocal() as db:
            run = db.query(JobAgentRun).filter(JobAgentRun.id == run_id).first()
            if run:
                run.status = "queued"
                db.commit()
    except Exception as e:
        logger.error(f"Failed to set job status to queued in DB: {e}")
        
    fallback_executor.submit(run_agent_flow_sync_wrapper, run_id, candidate_id)
    logger.info(f"Successfully enqueued run_id={run_id} to local ThreadPoolExecutor fallback queue.")
    return "queued_fallback"

def safe_enqueue(queue: Optional["Queue"], func, *args, **kwargs) -> bool:
    """Enqueue a job; return False gracefully if workers are unavailable."""
    if queue is None:
        logger.debug(f"Queue unavailable, skipping enqueue of {getattr(func, '__name__', func)}")
        return False
    try:
        queue.enqueue(func, *args, **kwargs)
        return True
    except Exception as exc:
        logger.warning(f"Failed to enqueue {getattr(func, '__name__', func)}: {exc}")
        return False

def recover_queued_jobs_on_startup():
    """Scan database on startup to recover any jobs left in 'queued' status."""
    from app.core.database import SessionLocal
    from app.models.models import JobAgentRun
    try:
        with SessionLocal() as db:
            queued_runs = db.query(JobAgentRun).filter(JobAgentRun.status == "queued").all()
            if queued_runs:
                logger.info(f"Found {len(queued_runs)} queued runs on startup. Re-submitting to fallback executor.")
                for run in queued_runs:
                    fallback_executor.submit(run_agent_flow_sync_wrapper, run.id, run.candidate_id)
    except Exception as e:
        logger.error(f"Error recovering queued jobs on startup: {e}")
