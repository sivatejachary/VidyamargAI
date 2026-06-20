"""
Platform Rate Limiter — Enforces per-platform daily application limits.
Prevents account lockouts and suspicious activity flags.
"""
import json
import logging
import os
from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {"max_per_day": 50, "delay_between_ms": 8000}
_config_cache: Optional[dict] = None


def _load_config() -> dict:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "platform_rate_limits.json"
    )
    try:
        with open(os.path.abspath(config_path)) as f:
            _config_cache = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load platform_rate_limits.json: {e}. Using defaults.")
        _config_cache = {"default": DEFAULT_CONFIG}
    return _config_cache


class PlatformRateLimiter:
    """
    Checks and enforces daily application limits per (user_id, platform).
    Primary: Redis counter with TTL (midnight reset).
    Fallback: DB count of today's ApplicationTask rows for this platform.
    """

    def _get_limit(self, platform: str) -> int:
        config = _load_config()
        return config.get(platform, config.get("default", DEFAULT_CONFIG))["max_per_day"]

    def get_delay_ms(self, platform: str) -> int:
        config = _load_config()
        return config.get(platform, config.get("default", DEFAULT_CONFIG))["delay_between_ms"]

    def check_and_consume(self, user_id: int, platform: str, db: Session) -> bool:
        """
        Returns True if application is allowed (and consumes one slot).
        Returns False if daily limit is already reached.
        """
        limit = self._get_limit(platform)
        if limit <= 0:
            return True  # No limit configured

        # Try Redis first
        redis_result = self._redis_check_and_consume(user_id, platform, limit)
        if redis_result is not None:
            return redis_result

        # Fallback: DB count
        return self._db_check(user_id, platform, limit, db)

    def _redis_check_and_consume(self, user_id: int, platform: str, limit: int) -> Optional[bool]:
        """Try Redis-based rate limiting with daily TTL."""
        try:
            import redis
            from app.core.config import settings
            r = redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6379"))
            today = date.today().isoformat()
            key = f"auto_apply:rate:{user_id}:{platform}:{today}"
            current = r.incr(key)
            if current == 1:
                # First use today — set TTL to end of day
                import time
                seconds_until_midnight = 86400 - (int(time.time()) % 86400)
                r.expire(key, seconds_until_midnight + 60)
            return current <= limit
        except Exception:
            return None  # Redis unavailable — fall through to DB

    def _db_check(self, user_id: int, platform: str, limit: int, db: Session) -> bool:
        """DB fallback: count today's tasks for this (user, platform)."""
        try:
            from app.models.auto_apply_models import ApplicationTask
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            count = db.query(ApplicationTask).filter(
                ApplicationTask.candidate_id == user_id,
                ApplicationTask.platform == platform,
                ApplicationTask.created_at >= today_start,
                ApplicationTask.status.notin_(["CANCELLED", "SKIPPED"])
            ).count()
            return count < limit
        except Exception as e:
            logger.error(f"DB rate limit check failed: {e}")
            return True  # Fail open


# Module-level singleton
platform_rate_limiter = PlatformRateLimiter()