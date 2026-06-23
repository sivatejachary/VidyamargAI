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

