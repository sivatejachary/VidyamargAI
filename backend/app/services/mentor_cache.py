import json
import logging
from app.core.config import settings

logger = logging.getLogger("app.mentor_cache")

# Local in-memory fallback
_LOCAL_MENTOR_CACHE = {}

_redis = None
def _get_redis():
    global _redis
    if _redis is None:
        if settings.REDIS_URL:
            try:
                import redis
                _redis = redis.Redis.from_url(
                    settings.REDIS_URL,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                    decode_responses=True
                )
            except Exception as e:
                logger.warning(f"Redis not available for mentor cache: {e}")
    return _redis

def get_cached_mentor_profile(user_id: int):
    r = _get_redis()
    key = f"mentor_profile_cache:{user_id}"
    if r:
        try:
            val = r.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.error(f"Redis cache error reading user {user_id}: {e}")
    return _LOCAL_MENTOR_CACHE.get(user_id)

def set_cached_mentor_profile(user_id: int, data: dict):
    r = _get_redis()
    key = f"mentor_profile_cache:{user_id}"
    # TTL: 24 hours
    ttl = 60 * 60 * 24
    if r:
        try:
            r.setex(key, ttl, json.dumps(data))
            return
        except Exception as e:
            logger.error(f"Redis cache error writing user {user_id}: {e}")
    _LOCAL_MENTOR_CACHE[user_id] = data

def invalidate_mentor_profile(user_id: int):
    r = _get_redis()
    key = f"mentor_profile_cache:{user_id}"
    if r:
        try:
            r.delete(key)
        except Exception as e:
            logger.error(f"Redis cache error deleting user {user_id}: {e}")
    if user_id in _LOCAL_MENTOR_CACHE:
        del _LOCAL_MENTOR_CACHE[user_id]
