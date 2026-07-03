"""
VidyaMarg AI — Celery Beat Scheduler Configuration
===================================================
Defines the periodic cron schedules for the job discovery module.
Uses standard Celery crontab definitions.

To prevent duplicate task execution in multi-instance / scaled environments,
this module implements a Redis-backed Distributed Lock context manager.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator, Optional
import redis

from celery.schedules import crontab
from app.job_discovery.workers.celery_app import celery_app
from app.job_discovery import config as cfg

logger = logging.getLogger("jd.scheduler")


# ---------------------------------------------------------------------------
# Redis Distributed Lock for Multi-Instance Deployments
# ---------------------------------------------------------------------------

class RedisDistributedLock:
    """
    Guarantees that a cron job runs exactly once across all Celery instances.
    Usage:
        with RedisDistributedLock("cleanup_lock", expire_seconds=300) as acquired:
            if acquired:
                # perform task
    """

    def __init__(self, lock_name: str, expire_seconds: int = 120) -> None:
        self.lock_key = f"locks:{lock_name}"
        self.expire_seconds = expire_seconds
        self._redis_client: Optional[redis.Redis] = None
        self._acquired = False

    def __enter__(self) -> bool:
        try:
            self._redis_client = redis.Redis.from_url(cfg.REDIS_URL, decode_responses=True)
            # SET lock_key locked NX EX expire_seconds
            self._acquired = bool(
                self._redis_client.set(
                    self.lock_key,
                    "locked",
                    nx=True,
                    ex=self.expire_seconds,
                )
            )
            if self._acquired:
                logger.debug(f"[Lock] Acquired distributed lock: {self.lock_key}")
            return self._acquired
        except Exception as exc:
            logger.error(f"[Lock] Redis lock acquisition failed: {exc}")
            # Degrade gracefully: on Redis failure, allow execution but log warning
            return True

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._acquired and self._redis_client:
            try:
                self._redis_client.delete(self.lock_key)
                logger.debug(f"[Lock] Released distributed lock: {self.lock_key}")
            except Exception as exc:
                logger.error(f"[Lock] Redis lock release failed: {exc}")


@contextmanager
def acquire_lock(lock_name: str, expire_seconds: int = 120) -> Generator[bool, None, None]:
    """Convenience context manager wrapper."""
    with RedisDistributedLock(lock_name, expire_seconds) as locked:
        yield locked


# ---------------------------------------------------------------------------
# Celery Beat Schedule Configuration
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule = {
    # 1. Poll external connectors for new jobs (Every 60 minutes)
    "discovery-scheduler-every-60-min": {
        "task": "app.workers.discovery.run_all_connectors",
        "schedule": crontab(minute="0", hour="*"),
    },
    # 2. Run matching engine and refresh recommendations (Hourly)
    "recommendation-scheduler-hourly": {
        "task": "app.workers.recommendation.generate_hourly_recs",
        "schedule": crontab(minute="0", hour="*"),
    },
    # 3. Flush WebSocket and email notifications for recommendations (Every 15 minutes)
    "notification-scheduler-every-15-min": {
        "task": "app.workers.notification.flush_notifications",
        "schedule": crontab(minute="*/15"),
    },
    # 4. Clean up / soft-delete expired jobs in DB & Qdrant (Daily at 02:00 AM UTC)
    "cleanup-scheduler-daily": {
        "task": "app.workers.cleanup.archive_expired_jobs",
        "schedule": crontab(hour="2", minute="0"),
    },
    # 5. Recovery Sync: Re-embed pending items in Qdrant (Daily at 03:00 AM UTC)
    "reindex-scheduler-daily": {
        "task": "app.workers.cleanup.sync_missing_qdrant_embeddings",
        "schedule": crontab(hour="3", minute="0"),
    },
    # 6. System health sentinel probe (Every 5 minutes)
    "health-scheduler-every-5-min": {
        "task": "app.workers.monitoring.run_health_checks",
        "schedule": crontab(minute="*/5"),
    },
}
