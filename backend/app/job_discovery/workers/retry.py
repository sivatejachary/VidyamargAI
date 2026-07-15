"""
WorkerRetryHandler — Exponential-backoff retry using Redis ZSET delay queue.

Critical bugs fixed vs legacy implementation:
  1. Legacy: re-published failed events IMMEDIATELY back to the same stream,
     exhausting 3 retries in milliseconds (hot retry loop).
  2. Fix: Failed events are placed in a Redis Sorted Set (delay queue) keyed
     by their next-eligible processing timestamp (ZSET score = Unix epoch).
  3. A companion DelayedRetryWorker (see delay_worker.py) polls the ZSET and
     re-publishes events only when their retry window has elapsed.
  4. Backoff schedule: 2s → 8s → 32s (geometric: base=2, exponent=attempts²)
  5. After max_retries exceeded, event is routed to the Dead Letter Queue.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Awaitable, Dict, Optional

from app.job_discovery.workers.dead_letter import send_to_dlq

logger = logging.getLogger("app.job_discovery.workers.retry")

# Backoff delays in seconds per retry attempt (0-indexed)
_BACKOFF_SECONDS = [2, 8, 32, 128, 512]
_DELAY_ZSET_KEY = "job_discovery:retry_delay_queue"


def _backoff_for(attempt: int) -> float:
    """Return the delay in seconds for a given retry attempt (0-indexed)."""
    if attempt < len(_BACKOFF_SECONDS):
        return float(_BACKOFF_SECONDS[attempt])
    return float(_BACKOFF_SECONDS[-1])


class WorkerRetryHandler:
    """
    Wraps an async worker handler with a 3-strike exponential backoff policy.

    On failure, the failed event is queued into a Redis ZSET delay queue
    instead of being immediately re-published to the stream. A separate
    DelayedRetryWorker drains the ZSET and re-publishes when the delay elapses.
    """

    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries

    async def execute_with_retry(
        self,
        stream: str,
        event: Dict[str, Any],
        handler_func: Callable[[Dict[str, Any]], Awaitable[None]],
    ) -> None:
        try:
            await handler_func(event)
        except Exception as exc:
            metadata = event.setdefault("_metadata", {})
            attempt = metadata.get("retries", 0)

            if attempt < self.max_retries:
                delay = _backoff_for(attempt)
                metadata["retries"] = attempt + 1
                metadata["last_error"] = str(exc)[:500]
                metadata["retry_stream"] = stream

                logger.warning(
                    f"[Retry] stream='{stream}' attempt={attempt + 1}/{self.max_retries} "
                    f"error={exc!r} — scheduling retry in {delay}s"
                )
                await _schedule_delayed_retry(stream, event, delay)
            else:
                reason = (
                    f"Exceeded max_retries={self.max_retries}. "
                    f"Last error: {str(exc)[:500]}"
                )
                logger.error(
                    f"[Retry] stream='{stream}' DLQ after {self.max_retries} attempts: {reason}"
                )
                await send_to_dlq(stream, event, reason)


async def _schedule_delayed_retry(
    stream: str,
    event: Dict[str, Any],
    delay_seconds: float,
) -> None:
    """
    Push the event into a Redis ZSET with score = now + delay_seconds.
    The DelayedRetryWorker polls this ZSET and re-publishes due events.
    """
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis is None:
            # Fallback: immediate re-publish (better than silent drop)
            logger.warning(
                "[Retry] Redis unavailable — falling back to immediate re-publish"
            )
            from app.core.event_bus import event_bus
            await event_bus.publish(stream, event)
            return

        score = time.time() + delay_seconds
        payload = json.dumps({"stream": stream, "event": event})
        await redis.zadd(_DELAY_ZSET_KEY, {payload: score})
        logger.debug(
            f"[Retry] Queued delayed retry in '{_DELAY_ZSET_KEY}' "
            f"at T+{delay_seconds}s for stream='{stream}'"
        )
    except Exception as exc:
        logger.critical(
            f"[Retry] Could not queue delayed retry — routing to DLQ: {exc}"
        )
        await send_to_dlq(stream, event, f"Retry scheduling failed: {exc}")
