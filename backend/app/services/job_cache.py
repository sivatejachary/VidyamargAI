"""
Redis caching service for live job results.
Falls back to in-memory TTL caching if Redis server is not available or fails.
Cache key format: "jobs:{user_id}:{search_query_hash}"
TTL: 1800 seconds (30 minutes)
"""
import time
import hashlib
import asyncio
import logging
import json
import redis
from typing import Optional, List, Any, Dict
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global store for in-memory fallback: { cache_key: (data, expires_at) }
_STORE: Dict[str, tuple] = {}
_LOCK = asyncio.Lock()

DEFAULT_TTL = 1800  # 30 minutes

# Try to connect to Redis on startup
_REDIS_CLIENT = None
try:
    _REDIS_CLIENT = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=2)
    # Test connection
    _REDIS_CLIENT.ping()
    logger.info("Connected to Redis successfully for job caching.")
except Exception as e:
    _REDIS_CLIENT = None
    logger.warning(f"Could not connect to Redis: {e}. Falling back to in-memory TTL caching.")


def _make_key(user_id: int, search: str) -> str:
    query_hash = hashlib.md5((search or "").lower().strip().encode()).hexdigest()[:8]
    return f"jobs:{user_id}:{query_hash}"


async def get(user_id: int, search: str) -> Optional[Any]:
    """Return cached jobs list/dict or None if missing/expired."""
    key = _make_key(user_id, search)
    
    if _REDIS_CLIENT is not None:
        try:
            loop = asyncio.get_running_loop()
            # Run blocking redis call in executor
            data_str = await loop.run_in_executor(None, _REDIS_CLIENT.get, key)
            if data_str:
                logger.debug(f"Redis cache hit for key={key}")
                return json.loads(data_str)
            logger.debug(f"Redis cache miss for key={key}")
            return None
        except Exception as e:
            logger.warning(f"Redis get failed: {e}. Trying in-memory fallback.")
            
    async with _LOCK:
        entry = _STORE.get(key)
        if entry is None:
            return None
        data, expires_at = entry
        if time.time() > expires_at:
            del _STORE[key]
            logger.debug(f"Cache expired for key={key}")
            return None
        logger.debug(f"Cache hit for key={key}")
        return data


async def set(user_id: int, search: str, data: Any, ttl: int = DEFAULT_TTL) -> None:
    """Store jobs list/dict in cache with TTL."""
    key = _make_key(user_id, search)
    
    if _REDIS_CLIENT is not None:
        try:
            data_str = json.dumps(data)
            loop = asyncio.get_running_loop()
            # Run blocking redis call in executor
            await loop.run_in_executor(None, lambda: _REDIS_CLIENT.setex(key, ttl, data_str))
            logger.debug(f"Redis cache set for key={key}, ttl={ttl}s")
            return
        except Exception as e:
            logger.warning(f"Redis set failed: {e}. Trying in-memory fallback.")
            
    expires_at = time.time() + ttl
    async with _LOCK:
        _STORE[key] = (data, expires_at)
    logger.debug(f"Cache set for key={key}, ttl={ttl}s")


async def invalidate(user_id: int) -> None:
    """Clear all cached results for a specific user."""
    prefix = f"jobs:{user_id}:"
    
    if _REDIS_CLIENT is not None:
        try:
            loop = asyncio.get_running_loop()
            def do_invalidate():
                keys = _REDIS_CLIENT.keys(f"{prefix}*")
                if keys:
                    # Redis delete accepts key strings as arguments
                    _REDIS_CLIENT.delete(*keys)
                return len(keys)
            count = await loop.run_in_executor(None, do_invalidate)
            logger.info(f"Invalidated {count} Redis cache entries for user {user_id}")
            return
        except Exception as e:
            logger.warning(f"Redis invalidate failed: {e}. Trying in-memory fallback.")
            
    async with _LOCK:
        keys_to_delete = [k for k in _STORE if k.startswith(prefix)]
        for k in keys_to_delete:
            del _STORE[k]
    logger.info(f"Invalidated {len(keys_to_delete)} cache entries for user {user_id}")


async def cleanup_expired() -> int:
    """Remove all expired entries. Returns count of removed entries."""
    if _REDIS_CLIENT is not None:
        # Redis handles TTL expiration automatically!
        return 0
        
    now = time.time()
    async with _LOCK:
        expired = [k for k, (_, exp) in _STORE.items() if now > exp]
        for k in expired:
            del _STORE[k]
    if expired:
        logger.debug(f"Cache cleanup: removed {len(expired)} expired entries")
    return len(expired)


def get_stats() -> dict:
    """Return cache statistics."""
    if _REDIS_CLIENT is not None:
        try:
            info = _REDIS_CLIENT.info()
            return {
                "redis_connected": True,
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_keys": _REDIS_CLIENT.dbsize()
            }
        except Exception:
            pass
            
    now = time.time()
    total = len(_STORE)
    active = sum(1 for _, (_, exp) in _STORE.items() if now <= exp)
    return {"redis_connected": False, "total_entries": total, "active_entries": active, "expired_entries": total - active}


def get_redis_client():
    """Return the global Redis client."""
    return _REDIS_CLIENT


async def _get_key_data(key: str) -> Optional[Any]:
    if _REDIS_CLIENT is not None:
        try:
            loop = asyncio.get_running_loop()
            data_str = await loop.run_in_executor(None, _REDIS_CLIENT.get, key)
            if data_str:
                return json.loads(data_str)
            return None
        except Exception as e:
            logger.warning(f"Redis get failed for key {key}: {e}. Trying in-memory fallback.")
            
    async with _LOCK:
        entry = _STORE.get(key)
        if entry is None:
            return None
        data, expires_at = entry
        if time.time() > expires_at:
            del _STORE[key]
            return None
        return data

async def _set_key_data(key: str, data: Any, ttl: int) -> None:
    if _REDIS_CLIENT is not None:
        try:
            data_str = json.dumps(data)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: _REDIS_CLIENT.setex(key, ttl, data_str))
            return
        except Exception as e:
            logger.warning(f"Redis set failed for key {key}: {e}. Trying in-memory fallback.")
            
    expires_at = time.time() + ttl
    async with _LOCK:
        _STORE[key] = (data, expires_at)

async def _delete_key(key: str) -> None:
    if _REDIS_CLIENT is not None:
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _REDIS_CLIENT.delete, key)
            return
        except Exception as e:
            logger.warning(f"Redis delete failed for key {key}: {e}. Trying in-memory fallback.")
            
    async with _LOCK:
        if key in _STORE:
            del _STORE[key]

async def _delete_by_prefix(prefix: str) -> None:
    if _REDIS_CLIENT is not None:
        try:
            loop = asyncio.get_running_loop()
            def do_delete():
                keys = _REDIS_CLIENT.keys(f"{prefix}*")
                if keys:
                    # Unpack keys for delete call
                    _REDIS_CLIENT.delete(*keys)
                return len(keys)
            await loop.run_in_executor(None, do_delete)
            return
        except Exception as e:
            logger.warning(f"Redis delete by prefix failed for {prefix}: {e}. Trying in-memory fallback.")
            
    async with _LOCK:
        keys_to_delete = [k for k in _STORE if k.startswith(prefix)]
        for k in keys_to_delete:
            del _STORE[k]


async def get_candidate_profile(candidate_id: int) -> Optional[Dict[str, Any]]:
    return await _get_key_data(f"candidate_profile:{candidate_id}")

async def set_candidate_profile(candidate_id: int, data: Dict[str, Any]) -> None:
    await _set_key_data(f"candidate_profile:{candidate_id}", data, ttl=900)

async def invalidate_candidate_profile(candidate_id: int) -> None:
    await _delete_key(f"candidate_profile:{candidate_id}")


async def get_jobs_pool(candidate_id: int, query_hash: str) -> Optional[List[Dict[str, Any]]]:
    return await _get_key_data(f"jobs:pool:{candidate_id}:{query_hash}")

async def set_jobs_pool(candidate_id: int, query_hash: str, data: List[Dict[str, Any]]) -> None:
    await _set_key_data(f"jobs:pool:{candidate_id}:{query_hash}", data, ttl=300)

async def invalidate_jobs_pool(candidate_id: int) -> None:
    await _delete_by_prefix(f"jobs:pool:{candidate_id}:")


async def get_skill_gap(candidate_id: int) -> Optional[Dict[str, Any]]:
    return await _get_key_data(f"skill_gap:{candidate_id}")

async def set_skill_gap(candidate_id: int, data: Dict[str, Any]) -> None:
    await _set_key_data(f"skill_gap:{candidate_id}", data, ttl=1800)

async def invalidate_skill_gap(candidate_id: int) -> None:
    await _delete_key(f"skill_gap:{candidate_id}")


async def get_study_plan(candidate_id: int) -> Optional[List[Dict[str, Any]]]:
    return await _get_key_data(f"study_plan:{candidate_id}")

async def set_study_plan(candidate_id: int, data: List[Dict[str, Any]]) -> None:
    await _set_key_data(f"study_plan:{candidate_id}", data, ttl=3600)

async def invalidate_study_plan(candidate_id: int) -> None:
    await _delete_key(f"study_plan:{candidate_id}")


async def get_generated_roles(candidate_id: int) -> Optional[List[str]]:
    return await _get_key_data(f"generated_roles:{candidate_id}")

async def set_generated_roles(candidate_id: int, roles: List[str]) -> None:
    await _set_key_data(f"generated_roles:{candidate_id}", roles, ttl=1800)

async def invalidate_generated_roles(candidate_id: int) -> None:
    await _delete_key(f"generated_roles:{candidate_id}")


async def get_search_strategy(candidate_id: int) -> Optional[Dict[str, Any]]:
    return await _get_key_data(f"search_strategy:{candidate_id}")

async def set_search_strategy(candidate_id: int, strategy: Dict[str, Any]) -> None:
    await _set_key_data(f"search_strategy:{candidate_id}", strategy, ttl=1800)

async def invalidate_search_strategy(candidate_id: int) -> None:
    await _delete_key(f"search_strategy:{candidate_id}")


async def get_text_embedding(text: str) -> Optional[List[float]]:
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
    return await _get_key_data(f"embedding:{text_hash}")

async def set_text_embedding(text: str, embedding: List[float]) -> None:
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
    await _set_key_data(f"embedding:{text_hash}", embedding, ttl=86400) # Cache for 24 hours


async def get_search_results(source: str, query: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve cached search results from Redis for a given source and query (TTL: 1 hour)."""
    text_hash = hashlib.md5(query.lower().strip().encode("utf-8")).hexdigest()
    return await _get_key_data(f"job_search:{source}:{text_hash}")

async def set_search_results(source: str, query: str, data: List[Dict[str, Any]]) -> None:
    """Cache search results in Redis for 1 hour."""
    text_hash = hashlib.md5(query.lower().strip().encode("utf-8")).hexdigest()
    await _set_key_data(f"job_search:{source}:{text_hash}", data, ttl=3600)  # 1 hour

async def get_job_detail(url: str) -> Optional[Dict[str, Any]]:
    """Retrieve job details from Redis by URL (TTL: 24 hours)."""
    url_hash = hashlib.md5(url.lower().strip().encode("utf-8")).hexdigest()
    return await _get_key_data(f"job_detail:{url_hash}")

async def set_job_detail(url: str, data: Dict[str, Any]) -> None:
    """Cache job details in Redis for 24 hours."""
    url_hash = hashlib.md5(url.lower().strip().encode("utf-8")).hexdigest()
    await _set_key_data(f"job_detail:{url_hash}", data, ttl=86400)  # 24 hours

async def get_company(company_name: str) -> Optional[Dict[str, Any]]:
    """Retrieve company details from Redis by name (TTL: 7 days)."""
    co_hash = hashlib.md5(company_name.lower().strip().encode("utf-8")).hexdigest()
    return await _get_key_data(f"company:{co_hash}")

async def set_company(company_name: str, data: Dict[str, Any]) -> None:
    """Cache company details in Redis for 7 days."""
    co_hash = hashlib.md5(company_name.lower().strip().encode("utf-8")).hexdigest()
    await _set_key_data(f"company:{co_hash}", data, ttl=604800)  # 7 days


