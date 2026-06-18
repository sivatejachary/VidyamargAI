import json
import logging
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.mcp_models import CircuitBreakerState
from app.core.queue import redis_conn

logger = logging.getLogger("app.services.circuit_breaker")

_LOCAL_CB_CACHE = {}  # {tool_name: (state_data, expires_at)}
CB_CACHE_TTL = 60  # seconds
FAILURE_THRESHOLD = 3
RECOVERY_TIMEOUT = 60  # seconds

def _get_cached_state(tool_name: str) -> dict:
    """Read state from Redis, fallback to local memory, fallback to None (miss)."""
    # 1. Try Redis
    if redis_conn:
        try:
            cached = redis_conn.get(f"mcp:cb:{tool_name}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis get for breaker {tool_name} failed: {e}")
            
    # 2. Try Local Cache
    if tool_name in _LOCAL_CB_CACHE:
        val, expiry = _LOCAL_CB_CACHE[tool_name][0], _LOCAL_CB_CACHE[tool_name][1]
        if datetime.utcnow() < expiry:
            return val
        else:
            del _LOCAL_CB_CACHE[tool_name]
            
    return None

def _set_cached_state(tool_name: str, state_data: dict):
    """Write state to Redis (60s TTL) and local memory fallback."""
    # 1. Try Redis
    if redis_conn:
        try:
            redis_conn.setex(f"mcp:cb:{tool_name}", CB_CACHE_TTL, json.dumps(state_data))
        except Exception as e:
            logger.warning(f"Redis set for breaker {tool_name} failed: {e}")
            
    # 2. Try Local Cache
    expiry = datetime.utcnow() + timedelta(seconds=CB_CACHE_TTL)
    _LOCAL_CB_CACHE[tool_name] = (state_data, expiry)

def _get_db_state(tool_name: str) -> dict:
    """Query DB for breaker state, creating record if missing."""
    with SessionLocal() as db:
        record = db.query(CircuitBreakerState).filter(CircuitBreakerState.tool_name == tool_name).first()
        if not record:
            record = CircuitBreakerState(
                tool_name=tool_name,
                state="CLOSED",
                failure_count=0
            )
            db.add(record)
            db.commit()
        return {
            "state": record.state,
            "failure_count": record.failure_count,
            "last_failure": record.last_failure.isoformat() if record.last_failure else None,
            "opened_at": record.opened_at.isoformat() if record.opened_at else None
        }

def _update_db_state(tool_name: str, state: str, failure_count: int, last_failure: datetime = None, opened_at: datetime = None):
    """Update DB record and refresh cache."""
    with SessionLocal() as db:
        record = db.query(CircuitBreakerState).filter(CircuitBreakerState.tool_name == tool_name).first()
        if not record:
            record = CircuitBreakerState(tool_name=tool_name)
            db.add(record)
        record.state = state
        record.failure_count = failure_count
        if last_failure is not None:
            record.last_failure = last_failure
        elif state == "CLOSED":
            record.last_failure = None
            
        if opened_at is not None:
            record.opened_at = opened_at
        elif state == "CLOSED":
            record.opened_at = None
            
        db.commit()
        
        state_data = {
            "state": record.state,
            "failure_count": record.failure_count,
            "last_failure": record.last_failure.isoformat() if record.last_failure else None,
            "opened_at": record.opened_at.isoformat() if record.opened_at else None
        }
        _set_cached_state(tool_name, state_data)

def allow_request(tool_name: str) -> bool:
    """Check if tool call is allowed by breaker."""
    state_data = _get_cached_state(tool_name)
    if not state_data:
        try:
            state_data = _get_db_state(tool_name)
            _set_cached_state(tool_name, state_data)
        except Exception as e:
            logger.error(f"Error reading breaker state from DB for {tool_name}: {e}")
            return True # Fail open if DB is down
        
    state = state_data.get("state", "CLOSED")
    if state == "CLOSED":
        return True
        
    if state == "OPEN":
        opened_at_str = state_data.get("opened_at")
        if opened_at_str:
            opened_at = datetime.fromisoformat(opened_at_str)
            elapsed = (datetime.utcnow() - opened_at).total_seconds()
            if elapsed >= RECOVERY_TIMEOUT:
                logger.info(f"Circuit Breaker for {tool_name} transitioned from OPEN to HALF-OPEN (recovery time elapsed)")
                try:
                    _update_db_state(tool_name, "HALF-OPEN", state_data.get("failure_count", 0))
                except Exception as e:
                    logger.error(f"Failed to transition breaker state to HALF-OPEN: {e}")
                return True
        return False
        
    # HALF-OPEN: Allow probe requests
    return True

def record_success(tool_name: str):
    """Record a successful tool call to close breaker."""
    state_data = _get_cached_state(tool_name)
    if not state_data:
        try:
            state_data = _get_db_state(tool_name)
        except Exception:
            state_data = {"state": "CLOSED", "failure_count": 0}
        
    if state_data.get("state") != "CLOSED":
        logger.info(f"Circuit Breaker for {tool_name} CLOSED after success.")
    try:
        _update_db_state(tool_name, "CLOSED", 0, last_failure=None, opened_at=None)
    except Exception as e:
        logger.error(f"Failed to record breaker success for {tool_name}: {e}")

def record_failure(tool_name: str):
    """Record a failed tool call, incrementing failure count and opening breaker if needed."""
    state_data = _get_cached_state(tool_name)
    if not state_data:
        try:
            state_data = _get_db_state(tool_name)
        except Exception:
            state_data = {"state": "CLOSED", "failure_count": 0}
        
    failures = state_data.get("failure_count", 0) + 1
    state = state_data.get("state", "CLOSED")
    opened_at = None
    
    if state in ["CLOSED", "HALF-OPEN"]:
        if failures >= FAILURE_THRESHOLD:
            state = "OPEN"
            opened_at = datetime.utcnow()
            logger.warning(f"Circuit Breaker for {tool_name} OPENED due to {failures} consecutive failures.")
        else:
            logger.info(f"Circuit Breaker for {tool_name} failure logged. Failures={failures}")
            
    try:
        _update_db_state(
            tool_name,
            state,
            failures,
            last_failure=datetime.utcnow(),
            opened_at=opened_at
        )
    except Exception as e:
        logger.error(f"Failed to record breaker failure for {tool_name}: {e}")

def get_open_breakers_count() -> int:
    """Return count of currently open circuit breakers."""
    # Read from DB
    try:
        with SessionLocal() as db:
            return db.query(CircuitBreakerState).filter(CircuitBreakerState.state == "OPEN").count()
    except Exception as e:
        logger.error(f"Failed to count open breakers: {e}")
        # fallback to local cache
        return sum(1 for data in _LOCAL_CB_CACHE.values() if data[0].get("state") == "OPEN")
