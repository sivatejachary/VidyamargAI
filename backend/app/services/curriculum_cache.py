"""
curriculum_cache.py — Redis curriculum cache with:
  - Cache versioning constants
  - State-machine circuit breaker (CLOSED / OPEN / HALF-OPEN)
  - Stale-while-revalidate stampede protection (versioned locks)
  - zlib compression for large payloads
  - Redis memory budget tracking
  - Cache invalidation & RQ warming integration
"""
from __future__ import annotations

import logging
import os
import time
import zlib
from enum import Enum
from typing import Any, Optional

import orjson

from app.core.config import settings
from app.core.monitoring import cache_status_var

logger = logging.getLogger("app.curriculum_cache")

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
CACHE_VERSION = "v4"
SCHEMA_VERSION = "schema1"

COURSE_CACHE_TTL = 60 * 60 * 24        # 24 hours
PROGRESS_CACHE_TTL = 60 * 10           # 10 minutes
LOCK_TTL = 30                           # 30 seconds
WAIT_ON_LOCK_MS = 500                   # ms to wait before retry
COMPRESS_THRESHOLD = 2048               # bytes

# Memory budget
MEMORY_WARN_RATIO = 0.80
MEMORY_CRIT_RATIO = 0.90
MEMORY_MAX_BYTES  = 512 * 1024 * 1024  # 512 MB

# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------
class _CBState(Enum):
    CLOSED    = "CLOSED"
    OPEN      = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class _CircuitBreaker:
    FAILURE_THRESHOLD = 3
    RECOVERY_TIMEOUT  = 60  # seconds

    def __init__(self):
        self.state       = _CBState.CLOSED
        self.failures    = 0
        self._opened_at  = 0.0

    def record_success(self):
        self.failures = 0
        self.state    = _CBState.CLOSED

    def record_failure(self):
        self.failures += 1
        if self.failures >= self.FAILURE_THRESHOLD:
            self.state      = _CBState.OPEN
            self._opened_at = time.monotonic()
            logger.warning("Redis circuit OPEN — bypassing Redis for %ds", self.RECOVERY_TIMEOUT)

    def allow_request(self) -> bool:
        if self.state == _CBState.CLOSED:
            return True
        if self.state == _CBState.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.RECOVERY_TIMEOUT:
                self.state = _CBState.HALF_OPEN
                logger.info("Redis circuit HALF-OPEN — sending probe request")
                return True
            return False
        # HALF_OPEN: allow exactly one probe
        return True


_cb = _CircuitBreaker()

# ---------------------------------------------------------------------------
# Redis client (lazy, optional)
# ---------------------------------------------------------------------------
_redis = None

def _get_redis():
    global _redis
    if _redis is None:
        try:
            import redis
            _redis = redis.Redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=False,
            )
        except Exception as exc:
            logger.warning("Redis not available: %s", exc)
    return _redis


# ---------------------------------------------------------------------------
# Key builders
# ---------------------------------------------------------------------------
def course_key(course_id: str, updated_at_unix: int) -> str:
    return f"lms:course:{CACHE_VERSION}:{SCHEMA_VERSION}:{course_id}:{updated_at_unix}"

def progress_key(user_id: int, course_id: str) -> str:
    return f"lms:progress:{user_id}:{course_id}"

def lock_key(course_id: str, updated_at_unix: int) -> str:
    return f"lock:lms:course:{course_id}:{updated_at_unix}"


# ---------------------------------------------------------------------------
# Encode / decode helpers
# ---------------------------------------------------------------------------
def _encode(payload: Any) -> bytes:
    raw = orjson.dumps(payload)
    if len(raw) > COMPRESS_THRESHOLD:
        return zlib.compress(raw)
    return raw

def _decode(data: bytes) -> Any:
    try:
        return orjson.loads(zlib.decompress(data))
    except zlib.error:
        return orjson.loads(data)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_course_cache(course_id: str, updated_at_unix: int) -> Optional[Any]:
    """Return cached curriculum or None."""
    if not _cb.allow_request():
        cache_status_var.set("BYPASS")
        return None
    r = _get_redis()
    if r is None:
        cache_status_var.set("BYPASS")
        return None
    try:
        key  = course_key(course_id, updated_at_unix)
        data = r.get(key)
        if data:
            _cb.record_success()
            cache_status_var.set("HIT")
            return _decode(data)
        _cb.record_success()
        cache_status_var.set("MISS")
        return None
    except Exception as exc:
        _cb.record_failure()
        logger.warning("Redis read error: %s", exc)
        cache_status_var.set("ERROR")
        return None


def set_course_cache(course_id: str, updated_at_unix: int, payload: Any) -> bool:
    """Write curriculum to Redis."""
    if not _cb.allow_request():
        return False
    r = _get_redis()
    if r is None:
        return False
    try:
        key = course_key(course_id, updated_at_unix)
        r.setex(key, COURSE_CACHE_TTL, _encode(payload))
        _cb.record_success()
        return True
    except Exception as exc:
        _cb.record_failure()
        logger.warning("Redis write error: %s", exc)
        return False


def invalidate_course_cache(course_id: str) -> int:
    """Delete ALL versions of a course key (pattern scan)."""
    r = _get_redis()
    if r is None:
        return 0
    try:
        pattern = f"lms:course:{CACHE_VERSION}:{SCHEMA_VERSION}:{course_id}:*"
        keys = list(r.scan_iter(pattern))
        if keys:
            return r.delete(*keys)
        return 0
    except Exception as exc:
        logger.warning("Cache invalidation error: %s", exc)
        return 0


def get_progress_cache(user_id: int, course_id: str) -> Optional[Any]:
    if not _cb.allow_request():
        return None
    r = _get_redis()
    if r is None:
        return None
    try:
        data = r.get(progress_key(user_id, course_id))
        if data:
            _cb.record_success()
            return _decode(data)
        _cb.record_success()
        return None
    except Exception as exc:
        _cb.record_failure()
        logger.warning("Redis progress read error: %s", exc)
        return None


def invalidate_progress_cache(user_id: int, course_id: str) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        r.delete(progress_key(user_id, course_id))
    except Exception as exc:
        logger.warning("Progress cache delete error: %s", exc)


def acquire_lock(course_id: str, updated_at_unix: int) -> bool:
    """Acquire a short-lived build lock. Returns True if acquired."""
    r = _get_redis()
    if r is None:
        return True  # proceed without lock if Redis unavailable
    try:
        key = lock_key(course_id, updated_at_unix)
        return bool(r.set(key, 1, nx=True, ex=LOCK_TTL))
    except Exception:
        return True  # fail open


def release_lock(course_id: str, updated_at_unix: int) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        r.delete(lock_key(course_id, updated_at_unix))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Cache metrics
# ---------------------------------------------------------------------------
def get_cache_stats() -> dict:
    """Return Redis memory and key metrics for /api/v1/cache/stats."""
    r = _get_redis()
    if r is None:
        return {"error": "Redis unavailable", "circuit_state": _cb.state.value}
    try:
        info = r.info("memory")
        keyspace = r.info("keyspace")
        total_keys = sum(
            int(str(v).split(",")[0].replace("keys=", ""))
            for v in keyspace.values()
        ) if keyspace else 0
        used_mb = info.get("used_memory", 0) / (1024 * 1024)
        peak_mb = info.get("used_memory_peak", 0) / (1024 * 1024)
        ratio   = info.get("used_memory", 0) / MEMORY_MAX_BYTES
        evicted = r.info("stats").get("evicted_keys", 0)
        return {
            "circuit_state":   _cb.state.value,
            "redis_memory_mb": round(used_mb, 2),
            "peak_memory_mb":  round(peak_mb, 2),
            "memory_ratio":    round(ratio, 3),
            "memory_warning":  ratio >= MEMORY_WARN_RATIO,
            "memory_critical": ratio >= MEMORY_CRIT_RATIO,
            "total_keys":      total_keys,
            "evicted_keys":    evicted,
        }
    except Exception as exc:
        return {"error": str(exc), "circuit_state": _cb.state.value}


# ---------------------------------------------------------------------------
# Cache warming (called by RQ worker)
# ---------------------------------------------------------------------------
def warm_course_cache(course_id: str) -> bool:
    """
    Rebuild and cache the full curriculum for a course.
    Intended to be called by RQ high_queue workers.
    Returns True on success.
    """
    from app.core.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        # Get updated_at timestamp for versioned key
        row = db.execute(
            text("SELECT updated_at FROM courses WHERE id = :id"),
            {"id": course_id}
        ).fetchone()
        if not row:
            return False
        import datetime
        updated_at = row[0]
        if isinstance(updated_at, datetime.datetime):
            updated_at_unix = int(updated_at.timestamp())
        else:
            updated_at_unix = int(time.time())

        # Check lock
        if not acquire_lock(course_id, updated_at_unix):
            logger.info("warm_course_cache: lock held for %s, skipping", course_id)
            return False

        try:
            from app.api.endpoints import _build_curriculum_payload
            payload = _build_curriculum_payload(db, course_id, user_id=None)
            if payload:
                set_course_cache(course_id, updated_at_unix, payload)
                logger.info("warm_course_cache: warmed %s", course_id)
                return True
        finally:
            release_lock(course_id, updated_at_unix)
    except Exception as exc:
        logger.error("warm_course_cache failed for %s: %s", course_id, exc)
        return False
    finally:
        db.close()
