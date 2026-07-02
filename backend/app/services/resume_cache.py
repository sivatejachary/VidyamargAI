import json
import logging
from app.core.config import settings

logger = logging.getLogger("app.resume_cache")

# Local in-memory fallback
_LOCAL_RESUME_CACHE = {}

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
                logger.warning(f"Redis not available for resume cache: {e}")
    return _redis

def get_cached_resume_analysis(candidate_id: int):
    r = _get_redis()
    key = f"resume_analysis_cache:{candidate_id}"
    if r:
        try:
            val = r.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.error(f"Redis cache error reading resume analysis for candidate {candidate_id}: {e}")
    return _LOCAL_RESUME_CACHE.get(candidate_id)

def set_cached_resume_analysis(candidate_id: int, data: dict):
    r = _get_redis()
    key = f"resume_analysis_cache:{candidate_id}"
    # TTL: 24 hours
    ttl = 60 * 60 * 24
    if r:
        try:
            r.setex(key, ttl, json.dumps(data))
            return
        except Exception as e:
            logger.error(f"Redis cache error writing resume analysis for candidate {candidate_id}: {e}")
    try:
        _LOCAL_RESUME_CACHE[candidate_id] = json.loads(json.dumps(data))
    except Exception:
        _LOCAL_RESUME_CACHE[candidate_id] = data

def invalidate_resume_analysis(candidate_id: int):
    r = _get_redis()
    key = f"resume_analysis_cache:{candidate_id}"
    if r:
        try:
            r.delete(key)
        except Exception as e:
            logger.error(f"Redis cache error deleting resume analysis for candidate {candidate_id}: {e}")
    if candidate_id in _LOCAL_RESUME_CACHE:
        try:
            del _LOCAL_RESUME_CACHE[candidate_id]
        except KeyError:
            pass
