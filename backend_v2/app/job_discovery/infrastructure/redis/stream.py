"""
VidyaMarg AI — Redis Event Stream Broker
=========================================
Publishes and consumes versioned domain events via Redis Streams.
Consumer groups allow independent scaling of each worker type.

Stream key: jobs:events:stream
Consumer group prefix: jd_workers

Every publish call appends a XADD entry to the stream.
Workers use XREADGROUP for reliable message delivery with ACKs.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import redis.asyncio as aioredis

from app.job_discovery import config as cfg
from app.job_discovery.domain.events import DomainEvent

logger = logging.getLogger("jd.redis.stream")


class EventStreamBroker:
    """
    Wraps Redis Streams XADD/XREADGROUP for event-driven worker communication.
    All events are persisted to the stream for replay capability.
    """

    def __init__(self, redis_url: str = cfg.REDIS_URL) -> None:
        self._redis_url = redis_url
        self._client: Optional[aioredis.Redis] = None
        self._local_queue: List[Dict[str, Any]] = []  # Fallback when Redis offline
        self._available = False

    async def connect(self) -> None:
        try:
            self._client = aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            self._available = True
            logger.info("Event Stream Broker connected to Redis.")
        except Exception as exc:
            logger.error(f"Redis unavailable for event stream: {exc}. Using local queue fallback.")
            self._available = False

    async def publish(self, event: DomainEvent, stream_key: Optional[str] = None) -> Optional[str]:
        """
        Publishes a domain event to the Redis stream.
        Returns the stream message ID on success, None on failure.
        The stream key is derived from the event type if not provided.
        """
        event_dict = event.to_dict()
        key = stream_key or f"jobs:{event_dict['event_type'].lower().replace('event', '')}.stream"

        if not self._available or not self._client:
            logger.warning(f"[Stream] Appending to local fallback queue: {event_dict['event_type']}")
            self._local_queue.append({"stream": key, "data": event_dict})
            return None

        try:
            msg_id = await self._client.xadd(
                cfg.REDIS_STREAM_NAME,
                {"event_type": event_dict["event_type"], "data": json.dumps(event_dict)},
                maxlen=100_000,   # Trim to last 100k events
                approximate=True,
            )
            logger.debug(
                f"[Stream] Published {event_dict['event_type']} id={msg_id} "
                f"correlation={event_dict.get('correlation_id')}"
            )
            return msg_id
        except Exception as exc:
            logger.error(f"[Stream] Publish failed: {exc}")
            self._local_queue.append({"stream": key, "data": event_dict})
            return None

    async def ensure_consumer_group(self, group_name: str) -> None:
        """Creates a consumer group if it does not exist."""
        if not self._available or not self._client:
            return
        try:
            await self._client.xgroup_create(
                cfg.REDIS_STREAM_NAME, group_name, id="0", mkstream=True
            )
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def read_group(
        self,
        group_name: str,
        consumer_name: str,
        count: int = 50,
        block_ms: int = 5000,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Reads messages from the stream as a consumer group member.
        Returns list of (message_id, decoded_event_dict) tuples.
        """
        if not self._available or not self._client:
            return []
        try:
            messages = await self._client.xreadgroup(
                groupname=group_name,
                consumername=consumer_name,
                streams={cfg.REDIS_STREAM_NAME: ">"},
                count=count,
                block=block_ms,
            )
            result = []
            if messages:
                for _, entries in messages:
                    for msg_id, fields in entries:
                        try:
                            event_dict = json.loads(fields.get("data", "{}"))
                            result.append((msg_id, event_dict))
                        except json.JSONDecodeError:
                            logger.warning(f"Malformed stream message: {msg_id}")
            return result
        except Exception as exc:
            logger.error(f"[Stream] Read group failed: {exc}")
            return []

    async def ack(self, group_name: str, message_id: str) -> None:
        """Acknowledges a processed message to prevent redelivery."""
        if not self._available or not self._client:
            return
        try:
            await self._client.xack(cfg.REDIS_STREAM_NAME, group_name, message_id)
        except Exception as exc:
            logger.error(f"[Stream] ACK failed for msg {message_id}: {exc}")

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_broker_instance: Optional[EventStreamBroker] = None


def get_event_broker() -> EventStreamBroker:
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = EventStreamBroker()
    return _broker_instance
