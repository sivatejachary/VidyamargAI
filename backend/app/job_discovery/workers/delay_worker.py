"""
DelayedRetryWorker — Drains the Redis ZSET delay queue.

Polls the `job_discovery:retry_delay_queue` ZSET for events whose
retry time has elapsed (score <= now), pops them atomically, and
re-publishes them to their original stream so a fresh consumer picks
them up for processing.

This is the companion to WorkerRetryHandler's exponential backoff
scheduling. Without this worker, delayed retries would never execute.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

logger = logging.getLogger("app.job_discovery.workers.delay_worker")

_DELAY_ZSET_KEY = "job_discovery:retry_delay_queue"
_POLL_INTERVAL_SECONDS = 5.0
_BATCH_SIZE = 20


async def start_delay_worker() -> None:
    """
    Background task: poll the ZSET every 5 seconds, re-publish due events.

    Call this once from the FastAPI lifespan startup hook:
        asyncio.create_task(start_delay_worker())
    """
    logger.info("[DelayWorker] Started — polling every %ss", _POLL_INTERVAL_SECONDS)
    while True:
        try:
            await _drain_due_events()
        except Exception as exc:
            logger.error(f"[DelayWorker] Drain error: {exc}")
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


async def _drain_due_events() -> None:
    """Pop and re-publish all events whose delay has elapsed."""
    from app.core.redis_client import get_redis
    from app.core.event_bus import event_bus

    redis = await get_redis()
    if redis is None:
        return

    now = time.time()

    # ZRANGEBYSCORE + ZREM in a Lua script for atomicity
    # This prevents double-processing if multiple delay workers run.
    lua_script = """
        local keys = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, ARGV[2])
        if #keys > 0 then
            redis.call('ZREM', KEYS[1], unpack(keys))
        end
        return keys
    """
    try:
        due_payloads = await redis.eval(
            lua_script,
            1,
            _DELAY_ZSET_KEY,
            str(now),
            str(_BATCH_SIZE),
        )
    except Exception as exc:
        logger.error(f"[DelayWorker] Lua eval failed: {exc}")
        return

    if not due_payloads:
        return

    logger.info(f"[DelayWorker] Draining {len(due_payloads)} due retry event(s).")

    for payload_str in due_payloads:
        try:
            payload = json.loads(payload_str)
            stream = payload["stream"]
            event = payload["event"]
            await event_bus.publish(stream, event)
            logger.debug(f"[DelayWorker] Re-published delayed event to stream='{stream}'")
        except Exception as exc:
            logger.error(f"[DelayWorker] Failed to re-publish payload: {exc}")
