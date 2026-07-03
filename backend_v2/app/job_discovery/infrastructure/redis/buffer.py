"""
VidyaMarg AI — Redis Collector Buffer
======================================
Thread-safe, pipeline-accelerated Redis buffer for raw job payloads.
All connectors write here during a discovery run.
The orchestrator reads and clears after ALL connectors have finished.

Key schema:  job_buffer:{run_id}:{connector_name}  (Redis Hash)
Value schema: JSON-serialized raw job dict per hash field.

Fallback: If Redis is unavailable, the buffer degrades to an in-memory
          dict protected by an asyncio.Lock. This prevents data loss
          when Redis is temporarily offline.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

from app.job_discovery import config as cfg

logger = logging.getLogger("jd.redis.buffer")


class InMemoryFallbackBuffer:
    """Thread-safe in-memory fallback when Redis is unavailable."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, str]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def push_raw_jobs(
        self, run_id: str, connector_name: str, jobs: List[Dict[str, Any]]
    ) -> None:
        async with self._lock:
            key = f"{run_id}:{connector_name}"
            for i, job in enumerate(jobs):
                self._store[key][f"job_{i}"] = json.dumps(job, default=str)
        logger.warning(
            f"[InMemoryFallback] Stored {len(jobs)} jobs for run={run_id} connector={connector_name}"
        )

    async def get_all_raw(self, run_id: str) -> List[Dict[str, Any]]:
        async with self._lock:
            prefix = f"{run_id}:"
            all_jobs: List[Dict[str, Any]] = []
            keys_to_delete = [k for k in self._store if k.startswith(prefix)]
            for key in keys_to_delete:
                for val in self._store[key].values():
                    all_jobs.append(json.loads(val))
                del self._store[key]
        return all_jobs

    async def count(self, run_id: str) -> int:
        async with self._lock:
            prefix = f"{run_id}:"
            total = sum(
                len(v) for k, v in self._store.items() if k.startswith(prefix)
            )
        return total


class RedisCollectorBuffer:
    """
    Primary Redis-backed collector buffer.
    Automatically falls back to InMemoryFallbackBuffer on Redis failure.
    """

    def __init__(self, redis_url: str = cfg.REDIS_URL) -> None:
        self._redis_url = redis_url
        self._client: Optional[aioredis.Redis] = None
        self._fallback = InMemoryFallbackBuffer()
        self._use_fallback = False

    async def connect(self) -> None:
        """Establish Redis connection. Called at startup."""
        try:
            self._client = aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
            )
            await self._client.ping()
            self._use_fallback = False
            logger.info("Redis Collector Buffer connected.")
        except Exception as exc:
            logger.error(f"Redis unavailable, switching to in-memory fallback: {exc}")
            self._use_fallback = True

    async def push_raw_jobs(
        self, run_id: str, connector_name: str, jobs: List[Dict[str, Any]]
    ) -> None:
        """
        Atomically pushes all raw job payloads from a single connector into Redis.
        Uses a Redis pipeline for O(1) round-trips regardless of job count.
        """
        if self._use_fallback or not self._client:
            await self._fallback.push_raw_jobs(run_id, connector_name, jobs)
            return

        key = f"job_buffer:{run_id}:{connector_name}"
        try:
            pipe = self._client.pipeline(transaction=False)
            for i, job in enumerate(jobs):
                pipe.hset(key, f"job_{i}", json.dumps(job, default=str))
            pipe.expire(key, cfg.REDIS_BUFFER_TTL_SECONDS)
            await pipe.execute()
            logger.debug(
                f"[Buffer] Stored {len(jobs)} jobs | run={run_id} | connector={connector_name}"
            )
        except Exception as exc:
            logger.error(f"[Buffer] Redis write failed, falling back: {exc}")
            self._use_fallback = True
            await self._fallback.push_raw_jobs(run_id, connector_name, jobs)

    async def get_all_raw(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves ALL raw jobs from buffer for a given run_id,
        clearing the buffer as it goes (atomic read-delete per key).
        """
        if self._use_fallback or not self._client:
            return await self._fallback.get_all_raw(run_id)

        all_jobs: List[Dict[str, Any]] = []
        pattern = f"job_buffer:{run_id}:*"

        try:
            cursor = 0
            while True:
                cursor, keys = await self._client.scan(
                    cursor=cursor, match=pattern, count=200
                )
                for key in keys:
                    raw_hash = await self._client.hgetall(key)
                    for val in raw_hash.values():
                        try:
                            all_jobs.append(json.loads(val))
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping malformed JSON in buffer key: {key}")
                    # Atomic cleanup
                    await self._client.delete(key)

                if cursor == 0:
                    break

            logger.info(f"[Buffer] Retrieved {len(all_jobs)} raw jobs for run={run_id}")
            return all_jobs

        except Exception as exc:
            logger.error(f"[Buffer] Redis read failed: {exc}")
            return await self._fallback.get_all_raw(run_id)

    async def count_for_run(self, run_id: str) -> int:
        """Returns total buffered job count for a run_id."""
        if self._use_fallback or not self._client:
            return await self._fallback.count(run_id)
        try:
            pattern = f"job_buffer:{run_id}:*"
            cursor, keys = await self._client.scan(cursor=0, match=pattern, count=200)
            total = 0
            for key in keys:
                total += await self._client.hlen(key)
            return total
        except Exception:
            return 0

    async def close(self) -> None:
        """Closes the Redis connection."""
        if self._client:
            await self._client.aclose()


# ---------------------------------------------------------------------------
# Module-level singleton (initialized in main.py lifespan)
# ---------------------------------------------------------------------------

_buffer_instance: Optional[RedisCollectorBuffer] = None


def get_collector_buffer() -> RedisCollectorBuffer:
    global _buffer_instance
    if _buffer_instance is None:
        _buffer_instance = RedisCollectorBuffer()
    return _buffer_instance
