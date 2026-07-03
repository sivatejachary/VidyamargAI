"""
VidyaMarg AI — Celery Application Factory
==========================================
Creates and configures the shared Celery application used by all workers.
All worker modules import this celery_app instance.
"""
from __future__ import annotations

from celery import Celery

from app.job_discovery import config as cfg

celery_app = Celery(
    "job_discovery",
    broker=cfg.CELERY_BROKER_URL,
    backend=cfg.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer=cfg.CELERY_TASK_SERIALIZER,
    result_serializer=cfg.CELERY_RESULT_SERIALIZER,
    accept_content=cfg.CELERY_ACCEPT_CONTENT,
    timezone=cfg.CELERY_TIMEZONE,
    enable_utc=cfg.CELERY_ENABLE_UTC,
    task_acks_late=cfg.CELERY_ACK_LATE,
    task_reject_on_worker_lost=cfg.CELERY_TASK_REJECT_ON_WORKER_LOST,
    worker_concurrency=cfg.CELERY_WORKER_CONCURRENCY,
    task_track_started=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    # Dead Letter Queue routing
    task_routes={
        "app.workers.discovery.*": {"queue": "discovery"},
        "app.workers.embedding.*": {"queue": "embedding"},
        "app.workers.matching.*": {"queue": "matching"},
        "app.workers.recommendation.*": {"queue": "recommendation"},
        "app.workers.notification.*": {"queue": "notification"},
        "app.workers.cleanup.*": {"queue": "cleanup"},
        "app.workers.monitoring.*": {"queue": "monitoring"},
    },
    # Retry policy defaults
    task_max_retries=3,
    task_default_retry_delay=60,  # 1 minute
)

# Auto-discover all task modules
celery_app.autodiscover_tasks([
    "app.job_discovery.workers.discovery",
    "app.job_discovery.workers.embedding",
    "app.job_discovery.workers.matching",
    "app.job_discovery.workers.recommendation",
    "app.job_discovery.workers.notification",
    "app.job_discovery.workers.cleanup",
    "app.job_discovery.workers.monitoring",
])
