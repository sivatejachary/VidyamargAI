"""
Event Bus — Redis Streams based event backbone.
Decouples all agents. Enables replay, monitoring, audit trail.
Falls back to in-memory PubSub if Redis is unavailable.
"""
import json
import asyncio
import logging
from typing import Callable, Dict, Any, Optional
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger("app.event_bus")


class EventBus:
    """Redis Streams-based event bus with consumer groups and in-memory fallback."""

    def __init__(self):
        self._redis = None
        self._fallback_listeners: Dict[str, list[Callable]] = {}
        self._fallback_mode = False

    async def connect(self, redis_url: str):
        """Connect to Redis, fallback to in-memory if it fails."""
        try:
            import redis.asyncio as aioredis
            self._redis = await aioredis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2, decode_responses=True)
            # Try to ping to verify connection
            await self._redis.ping()
            await self._ensure_streams()
            logger.info("EventBus connected to Redis Streams.")
        except Exception as exc:
            logger.warning(f"Redis not available for EventBus ({exc}). Falling back to in-memory PubSub.")
            self._redis = None
            self._fallback_mode = True

    async def _ensure_streams(self):
        """Create streams and consumer groups if they don't exist."""
        streams = [
            "job:found", "job:matched",
            "app:sent", "app:otp", "app:complete",
            "track:update", "track:interview",
            "career:insight",
            "jobs.persisted.v1", "jobs.embedded.v1",
            "jobs.matched.v1", "recommendations.created.v1",
            "jobs.failed.dlq"
        ]
        for stream in streams:
            try:
                # Group creation auto-creates stream if mkstream=True
                await self._redis.xgroup_create(
                    stream, "agent_consumers", "$", mkstream=True
                )
            except Exception:
                pass  # Group already exists

    async def publish(self, stream: str, event: Dict[str, Any]):
        """Publish an event to a stream or in-memory listeners."""
        event_time = datetime.utcnow().isoformat()
        event["timestamp"] = event.get("timestamp", event_time)
        event["stream"] = stream

        if self._fallback_mode or not self._redis:
            # Local PubSub fallback
            logger.debug(f"[InMemory EventBus] Publishing to {stream}: {event}")
            handlers = self._fallback_listeners.get(stream, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(event))
                    else:
                        # Run sync handler in thread pool
                        loop = asyncio.get_running_loop()
                        loop.run_in_executor(None, handler, event)
                except Exception as e:
                    logger.error(f"In-memory handler error for {stream}: {e}")
            return "in-memory-id"

        try:
            payload = {
                "data": json.dumps(event),
                "timestamp": event["timestamp"],
                "stream": stream,
            }
            msg_id = await self._redis.xadd(stream, payload)
            logger.debug(f"Published to {stream} on Redis: {msg_id}")
            return msg_id
        except Exception as exc:
            logger.error(f"Redis xadd failed, falling back to in-memory publish: {exc}")
            # Dynamic fallback
            handlers = self._fallback_listeners.get(stream, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(event))
                    else:
                        loop = asyncio.get_running_loop()
                        loop.run_in_executor(None, handler, event)
                except Exception as e:
                    logger.error(f"Fallback handler error for {stream}: {e}")
            return "fallback-id"

    async def subscribe(
        self,
        stream: str,
        handler: Callable,
        consumer_name: str = "default",
        batch_size: int = 10
    ):
        """Subscribe to a stream. If in fallback mode, register to in-memory list."""
        if stream not in self._fallback_listeners:
            self._fallback_listeners[stream] = []
        if handler not in self._fallback_listeners[stream]:
            self._fallback_listeners[stream].append(handler)

        if not self._fallback_mode and self._redis:
            # Start background Redis consumer loop
            asyncio.create_task(
                self._consume_loop(stream, handler, consumer_name, batch_size)
            )
            logger.info(f"Registered Redis consumer for {stream} (consumer: {consumer_name})")
        else:
            logger.info(f"Registered In-Memory consumer for {stream}")

    async def _consume_loop(self, stream, handler, consumer_name, batch_size):
        """Background loop that processes Redis Streams events."""
        while True:
            try:
                if not self._redis:
                    await asyncio.sleep(5)
                    continue

                # Read new messages (id ">" means only messages never delivered to other consumers)
                messages = await self._redis.xreadgroup(
                    groupname="agent_consumers",
                    consumername=consumer_name,
                    streams={stream: ">"},
                    count=batch_size,
                    block=2000  # Block 2s waiting for messages
                )
                if not messages:
                    continue

                for _, msgs in messages:
                    for msg_id, data in msgs:
                        try:
                            event = json.loads(data["data"])
                            if asyncio.iscoroutinefunction(handler):
                                await handler(event)
                            else:
                                loop = asyncio.get_running_loop()
                                await loop.run_in_executor(None, handler, event)
                            # Acknowledge after successful processing
                            await self._redis.xack(stream, "agent_consumers", msg_id)
                        except Exception as e:
                            logger.error(f"Handler error for {stream}/{msg_id}: {e}")
            except Exception as e:
                logger.error(f"Consumer loop error for {stream}: {e}")
                await asyncio.sleep(5)


event_bus = EventBus()


# ─── Event Publishing Helpers ────────────────────────────────────────────────

async def publish_job_found(candidate_id: int, job: dict):
    await event_bus.publish("job:found", {
        "candidate_id": candidate_id,
        "job": job,
    })

async def publish_job_matched(candidate_id: int, job_pool_id: int, score: float):
    await event_bus.publish("job:matched", {
        "candidate_id": candidate_id,
        "job_pool_id": job_pool_id,
        "match_score": score,
    })

async def publish_app_sent(candidate_id: int, job_id: str, portal: str):
    await event_bus.publish("app:sent", {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "portal": portal,
    })

async def publish_otp_required(user_id: int, callback_key: str, portal: str):
    await event_bus.publish("app:otp", {
        "user_id": user_id,
        "callback_key": callback_key,
        "portal": portal,
    })

async def publish_interview_found(candidate_id: int, company: str, interview_date: str):
    await event_bus.publish("track:interview", {
        "candidate_id": candidate_id,
        "company": company,
        "interview_date": interview_date,
    })
