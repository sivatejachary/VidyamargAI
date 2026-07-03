"""
VidyaMarg AI — Job Discovery Platform Configuration
====================================================
All environment-driven configuration for the autonomous job discovery module.
This module is completely independent from the main AI OS backend.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from dotenv import load_dotenv
from pathlib import Path

# Try loading .env from current and parent directories
env_paths = [
    Path.cwd() / ".env",
    Path(__file__).resolve().parent / ".env",
    Path(__file__).resolve().parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
]
for p in env_paths:
    if p.exists():
        load_dotenv(p)
        break
else:
    load_dotenv()


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
_db_env = os.getenv("JD_DATABASE_URL") or os.getenv("DATABASE_URL") or "postgresql+asyncpg://postgres:postgres@localhost:5432/vidyamarg_jobs"
if _db_env.startswith("postgresql://"):
    DATABASE_URL = _db_env.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = _db_env

DATABASE_POOL_SIZE: int = int(os.getenv("JD_DB_POOL_SIZE", "20"))
DATABASE_MAX_OVERFLOW: int = int(os.getenv("JD_DB_MAX_OVERFLOW", "40"))
DATABASE_POOL_TIMEOUT: int = int(os.getenv("JD_DB_POOL_TIMEOUT", "30"))

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
REDIS_URL: str = os.getenv("JD_REDIS_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/1"
REDIS_BUFFER_TTL_SECONDS: int = int(os.getenv("JD_REDIS_BUFFER_TTL", "86400"))  # 24 hrs
REDIS_STREAM_NAME: str = "jobs:events:stream"
REDIS_CONSUMER_GROUP_PREFIX: str = "jd_workers"
REDIS_LOCK_EXPIRE_SECONDS: int = 120

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL: str = os.getenv("JD_CELERY_BROKER", REDIS_URL)
CELERY_RESULT_BACKEND: str = os.getenv("JD_CELERY_BACKEND", REDIS_URL)
CELERY_TASK_SERIALIZER: str = "json"
CELERY_RESULT_SERIALIZER: str = "json"
CELERY_ACCEPT_CONTENT: List[str] = ["json"]
CELERY_TIMEZONE: str = "UTC"
CELERY_ENABLE_UTC: bool = True
CELERY_ACK_LATE: bool = True
CELERY_TASK_REJECT_ON_WORKER_LOST: bool = True
CELERY_WORKER_CONCURRENCY: int = int(os.getenv("JD_CELERY_CONCURRENCY", "8"))

# ---------------------------------------------------------------------------
# Qdrant
# ---------------------------------------------------------------------------
QDRANT_URL: str = os.getenv("JD_QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY: Optional[str] = os.getenv("JD_QDRANT_API_KEY")
QDRANT_COLLECTION_NAME: str = os.getenv("JD_QDRANT_COLLECTION", "job_embeddings")
QDRANT_VECTOR_SIZE: int = 1536  # OpenAI text-embedding-3-small
QDRANT_DISTANCE: str = "Cosine"

# ---------------------------------------------------------------------------
# Embedding Model
# ---------------------------------------------------------------------------
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL: str = os.getenv("JD_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_BATCH_SIZE: int = int(os.getenv("JD_EMBEDDING_BATCH_SIZE", "100"))

# ---------------------------------------------------------------------------
# Connectors
# ---------------------------------------------------------------------------
CONNECTOR_TIMEOUT_SECONDS: int = int(os.getenv("JD_CONNECTOR_TIMEOUT", "30"))
CONNECTOR_MAX_RETRIES: int = int(os.getenv("JD_CONNECTOR_MAX_RETRIES", "3"))
CONNECTOR_RETRY_BACKOFF_BASE: float = 2.0   # exponential base
CONNECTOR_MAX_JOBS_PER_RUN: int = int(os.getenv("JD_MAX_JOBS_PER_RUN", "500"))
CONNECTOR_CIRCUIT_BREAKER_THRESHOLD: int = int(os.getenv("JD_CB_THRESHOLD", "5"))

# Telegram
TELEGRAM_API_ID: Optional[str] = os.getenv("TG_API_ID")
TELEGRAM_API_HASH: Optional[str] = os.getenv("TG_API_HASH")
TELEGRAM_SESSION_PATH: str = os.getenv("TG_SESSION_PATH", "/app/sessions/telegram")

# ---------------------------------------------------------------------------
# Scheduler Intervals (in minutes unless noted)
# ---------------------------------------------------------------------------
SCHEDULE_DISCOVERY_INTERVAL_MIN: int = int(os.getenv("JD_SCHEDULE_DISCOVERY", "60"))
SCHEDULE_RECOMMENDATION_INTERVAL_MIN: int = int(os.getenv("JD_SCHEDULE_RECS", "60"))
SCHEDULE_NOTIFICATION_INTERVAL_MIN: int = int(os.getenv("JD_SCHEDULE_NOTIF", "15"))
SCHEDULE_CLEANUP_HOUR: int = int(os.getenv("JD_SCHEDULE_CLEANUP_HOUR", "2"))
SCHEDULE_REINDEX_HOUR: int = int(os.getenv("JD_SCHEDULE_REINDEX_HOUR", "3"))
SCHEDULE_HEALTH_INTERVAL_MIN: int = int(os.getenv("JD_SCHEDULE_HEALTH", "5"))

# ---------------------------------------------------------------------------
# Matching Engine Weights (must sum to 1.0)
# ---------------------------------------------------------------------------
@dataclass
class MatchingWeights:
    semantic: float = 0.35
    skill: float = 0.25
    experience: float = 0.15
    salary: float = 0.10
    location: float = 0.08
    remote_preference: float = 0.04
    company_preference: float = 0.02
    freshness: float = 0.01

    def validate(self) -> None:
        total = sum(vars(self).values())
        assert abs(total - 1.0) < 1e-6, f"Matching weights must sum to 1.0, got {total}"


MATCHING_WEIGHTS = MatchingWeights()

# ---------------------------------------------------------------------------
# Pipeline Quality Thresholds
# ---------------------------------------------------------------------------
MIN_TITLE_LENGTH: int = 3
MAX_TITLE_LENGTH: int = 500
MIN_DESCRIPTION_LENGTH: int = 30
MAX_SPAM_SCORE: float = 0.6
MIN_TRUST_SCORE: float = 0.2
JOB_EXPIRY_DAYS: int = int(os.getenv("JD_JOB_EXPIRY_DAYS", "60"))

# ---------------------------------------------------------------------------
# API Server
# ---------------------------------------------------------------------------
API_HOST: str = os.getenv("JD_API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("JD_API_PORT", "8100"))
API_SECRET_KEY: str = os.getenv("JD_API_SECRET_KEY", "change-me-in-production-please")
API_ALGORITHM: str = "HS256"
API_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JD_TOKEN_EXPIRE_MIN", "1440"))

# ---------------------------------------------------------------------------
# Monitoring & Alerting
# ---------------------------------------------------------------------------
SLACK_WEBHOOK_URL: Optional[str] = os.getenv("JD_SLACK_WEBHOOK")
PAGERDUTY_KEY: Optional[str] = os.getenv("JD_PAGERDUTY_KEY")
QUEUE_DEPTH_ALERT_THRESHOLD: int = int(os.getenv("JD_QUEUE_ALERT", "10000"))
WORKER_HEARTBEAT_TIMEOUT_SECONDS: int = int(os.getenv("JD_HEARTBEAT_TIMEOUT", "300"))

# ---------------------------------------------------------------------------
# Supported Connector IDs
# ---------------------------------------------------------------------------
ENABLED_CONNECTORS: List[str] = [
    name.strip()
    for name in os.getenv(
        "JD_ENABLED_CONNECTORS",
        "remoteok,telegram,greenhouse,lever,wellfound,indeed,linkedin",
    ).split(",")
    if name.strip()
]
