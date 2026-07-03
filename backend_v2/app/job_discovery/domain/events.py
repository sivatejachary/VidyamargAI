"""
VidyaMarg AI — Versioned Domain Events
=======================================
All events are immutable value objects published to Redis Streams.
Every event carries a full tracing envelope (event_id, correlation_id, trace_id).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Base Envelope
# ---------------------------------------------------------------------------

@dataclass
class DomainEvent:
    """
    Base envelope for all versioned domain events.
    Every concrete event must inherit from this class.
    """
    version: int = 1
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    producer: str = "job_discovery.unknown"
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.__class__.__name__,
            "version": self.version,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "producer": self.producer,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainEvent":
        inst = cls.__new__(cls)
        inst.event_id = data["event_id"]
        inst.version = data["version"]
        inst.timestamp = data["timestamp"]
        inst.correlation_id = data["correlation_id"]
        inst.trace_id = data["trace_id"]
        inst.producer = data["producer"]
        inst.payload = data["payload"]
        return inst


# ---------------------------------------------------------------------------
# Discovery Pipeline Events
# ---------------------------------------------------------------------------

@dataclass
class JobsDiscoveredEvent(DomainEvent):
    """
    Published when a connector completes a crawl run.
    Stream key: jobs.discovered.v1
    """
    producer: str = "job_discovery.connector"

    @classmethod
    def create(
        cls,
        run_id: str,
        connector_name: str,
        job_count: int,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> "JobsDiscoveredEvent":
        ev = cls()
        if correlation_id:
            ev.correlation_id = correlation_id
        if trace_id:
            ev.trace_id = trace_id
        ev.payload = {
            "run_id": run_id,
            "connector": connector_name,
            "job_count": job_count,
        }
        return ev


@dataclass
class JobsNormalizedEvent(DomainEvent):
    """
    Published after batch normalization & validation is complete.
    Stream key: jobs.normalized.v1
    """
    producer: str = "job_discovery.normalizer"

    @classmethod
    def create(
        cls,
        run_id: str,
        valid_count: int,
        invalid_count: int,
        correlation_id: Optional[str] = None,
    ) -> "JobsNormalizedEvent":
        ev = cls()
        if correlation_id:
            ev.correlation_id = correlation_id
        ev.payload = {
            "run_id": run_id,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
        }
        return ev


@dataclass
class JobsPersistedEvent(DomainEvent):
    """
    Published after bulk DB insert is committed.
    Stream key: jobs.persisted.v1
    Triggers: Embedding Worker
    """
    producer: str = "job_discovery.orchestrator"

    @classmethod
    def create(
        cls,
        run_id: str,
        job_ids: List[int],
        companies_created: int,
        correlation_id: Optional[str] = None,
    ) -> "JobsPersistedEvent":
        ev = cls()
        if correlation_id:
            ev.correlation_id = correlation_id
        ev.payload = {
            "run_id": run_id,
            "job_ids": job_ids,
            "companies_created": companies_created,
        }
        return ev


@dataclass
class JobEmbeddedEvent(DomainEvent):
    """
    Published after a job's vector is written to Qdrant.
    Stream key: jobs.embedded.v1
    Triggers: Matching Worker
    """
    producer: str = "job_discovery.embedding_worker"

    @classmethod
    def create(
        cls,
        job_id: int,
        vector_id: str,
        dimensions: int,
        correlation_id: Optional[str] = None,
    ) -> "JobEmbeddedEvent":
        ev = cls()
        if correlation_id:
            ev.correlation_id = correlation_id
        ev.payload = {
            "job_id": job_id,
            "vector_id": vector_id,
            "dimensions": dimensions,
        }
        return ev


@dataclass
class JobsMatchedEvent(DomainEvent):
    """
    Published after matching engine runs against a batch of new jobs.
    Stream key: jobs.matched.v1
    Triggers: Recommendation Worker
    """
    producer: str = "job_discovery.matching_worker"

    @classmethod
    def create(
        cls,
        job_id: int,
        matched_candidates_count: int,
        correlation_id: Optional[str] = None,
    ) -> "JobsMatchedEvent":
        ev = cls()
        if correlation_id:
            ev.correlation_id = correlation_id
        ev.payload = {
            "job_id": job_id,
            "matched_candidates_count": matched_candidates_count,
        }
        return ev


@dataclass
class RecommendationCreatedEvent(DomainEvent):
    """
    Published after a recommendation is generated for a candidate.
    Stream key: recommendations.created.v1
    Triggers: Notification Worker
    """
    producer: str = "job_discovery.recommendation_worker"

    @classmethod
    def create(
        cls,
        candidate_id: int,
        recommendation_id: int,
        job_id: int,
        score: float,
        correlation_id: Optional[str] = None,
    ) -> "RecommendationCreatedEvent":
        ev = cls()
        if correlation_id:
            ev.correlation_id = correlation_id
        ev.payload = {
            "candidate_id": candidate_id,
            "recommendation_id": recommendation_id,
            "job_id": job_id,
            "score": score,
        }
        return ev


@dataclass
class NotificationCreatedEvent(DomainEvent):
    """
    Published when a user-facing notification is ready to dispatch.
    Stream key: notifications.created.v1
    """
    producer: str = "job_discovery.notification_worker"

    @classmethod
    def create(
        cls,
        notification_id: int,
        candidate_id: int,
        channel: str,
        status: str = "pending",
        correlation_id: Optional[str] = None,
    ) -> "NotificationCreatedEvent":
        ev = cls()
        if correlation_id:
            ev.correlation_id = correlation_id
        ev.payload = {
            "notification_id": notification_id,
            "candidate_id": candidate_id,
            "channel": channel,
            "status": status,
        }
        return ev


# ---------------------------------------------------------------------------
# Stream key registry
# ---------------------------------------------------------------------------

STREAM_KEYS = {
    "jobs.discovered.v1": JobsDiscoveredEvent,
    "jobs.normalized.v1": JobsNormalizedEvent,
    "jobs.persisted.v1": JobsPersistedEvent,
    "jobs.embedded.v1": JobEmbeddedEvent,
    "jobs.matched.v1": JobsMatchedEvent,
    "recommendations.created.v1": RecommendationCreatedEvent,
    "notifications.created.v1": NotificationCreatedEvent,
}
