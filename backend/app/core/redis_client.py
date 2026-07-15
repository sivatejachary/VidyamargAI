"""
Redis Client — Singleton async Redis connection.

Provides a module-level async Redis client used by:
  - WorkerRetryHandler (ZSET delay queue)
  - DelayedRetryWorker (ZSET polling)
  - Any module that needs direct Redis access

Falls back gracefully (returns None) if Redis is unavailable so callers
can degrade without crashing.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("app.core.redis_client")

_redis_instance = None


async def get_redis():
    """
    Returns a connected redis.asyncio.Redis client, or None if unavailable.
    Reuses a module-level singleton — safe to call multiple times.
    """
    global _redis_instance
    if _redis_instance is not None:
        return _redis_instance

    try:
        from app.core.config import settings
        import redis.asyncio as aioredis

        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        client = await aioredis.from_url(
            redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        await client.ping()
        _redis_instance = client
        logger.info("Redis client connected successfully.")
        return _redis_instance
    except Exception as exc:
        logger.warning(f"Redis unavailable — get_redis() returning None: {exc}")
        return None


async def close_redis() -> None:
    """Close the singleton Redis connection on shutdown."""
    global _redis_instance
    if _redis_instance is not None:
        try:
            await _redis_instance.aclose()
        except Exception:
            pass
        _redis_instance = None
