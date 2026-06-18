"""
MCP Gateway — central mesh routing tool calls to registered MCP servers.
Handles rate limiting, caching, circuit breakers, feature flags, consent checks, and audit logging.
"""
import logging
import time
import json
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import User, UserConsent
from app.models.mcp_models import ToolPermission, CircuitBreakerState, MCPAuditLog

logger = logging.getLogger("app.mcp.gateway")

# In-memory cache for circuit breaker states (60s TTL) to prevent DB hotspots
_BREAKER_CACHE: Dict[str, Dict[str, Any]] = {}
BREAKER_CACHE_TTL = 60.0  # seconds

# In-memory simple rate limiter cache (sliding window)
# { "user_id:server_name": [timestamp, ...] }
_RATE_LIMITS: Dict[str, list] = {}
RATE_LIMIT_WINDOW = 3600  # 1 hour
MAX_LIMIT_PER_HOUR = 100  # Default fallback limit

# In-memory TTL cache for read-only tool calls
# { "server:tool:args_hash": (expiry, response) }
_READ_CACHE: Dict[str, tuple] = {}

# In-memory Audit Queue for batch inserts
_AUDIT_QUEUE: asyncio.Queue = asyncio.Queue(maxsize=10000)
audit_queue_dropped = 0
audit_queue_overflow = 0


# --------------------------------------------------------------------------
# Circuit Breaker Helpers
# --------------------------------------------------------------------------
def _get_breaker_state(server_name: str, db: Session) -> str:
    """Gets current circuit state (CLOSED, OPEN, HALF-OPEN) from DB/Cache."""
    now = time.time()
    cached = _BREAKER_CACHE.get(server_name)
    if cached and (now - cached["fetched_at"] < BREAKER_CACHE_TTL):
        return cached["state"]

    # Load from DB
    breaker = db.query(CircuitBreakerState).filter(CircuitBreakerState.tool_name == server_name).first()
    if not breaker:
        breaker = CircuitBreakerState(tool_name=server_name, state="CLOSED")
        db.add(breaker)
        db.commit()
        db.refresh(breaker)

    state = breaker.state
    # Check if OPEN has expired
    if state == "OPEN" and breaker.opened_at:
        elapsed = (datetime.utcnow() - breaker.opened_at).total_seconds()
        if elapsed >= 60.0:  # Reopen after 60 seconds
            breaker.state = "HALF-OPEN"
            db.commit()
            state = "HALF-OPEN"
            logger.info(f"Circuit breaker for {server_name} transitioned to HALF-OPEN")

    _BREAKER_CACHE[server_name] = {
        "state": state,
        "fetched_at": now
    }
    return state


def _record_breaker_success(server_name: str, db: Session):
    """Records a successful tool call to close the circuit."""
    breaker = db.query(CircuitBreakerState).filter(CircuitBreakerState.tool_name == server_name).first()
    if breaker:
        breaker.state = "CLOSED"
        breaker.failure_count = 0
        breaker.last_failure = None
        breaker.opened_at = None
        db.commit()
        _BREAKER_CACHE[server_name] = {
            "state": "CLOSED",
            "fetched_at": time.time()
        }


def _record_breaker_failure(server_name: str, db: Session):
    """Records a failure. Opens the circuit if 3 failures occur in a row."""
    breaker = db.query(CircuitBreakerState).filter(CircuitBreakerState.tool_name == server_name).first()
    if breaker:
        breaker.failure_count += 1
        breaker.last_failure = datetime.utcnow()
        if breaker.failure_count >= 3:
            breaker.state = "OPEN"
            breaker.opened_at = datetime.utcnow()
            logger.warning(f"Circuit breaker for {server_name} opened due to 3 consecutive failures")
        db.commit()
        _BREAKER_CACHE[server_name] = {
            "state": breaker.state,
            "fetched_at": time.time()
        }


# --------------------------------------------------------------------------
# Rate Limiting
# --------------------------------------------------------------------------
def _check_rate_limit(user_id: int, server_name: str) -> bool:
    """Sliding window rate limit: Max 100 calls per server per user per hour."""
    key = f"{user_id}:{server_name}"
    now = time.time()
    
    if key not in _RATE_LIMITS:
        _RATE_LIMITS[key] = []
        
    # Filter out timestamps older than window
    timestamps = [t for t in _RATE_LIMITS[key] if now - t < RATE_LIMIT_WINDOW]
    _RATE_LIMITS[key] = timestamps
    
    if len(timestamps) >= MAX_LIMIT_PER_HOUR:
        logger.warning(f"Rate limit exceeded for user {user_id} on server {server_name}")
        return False
        
    _RATE_LIMITS[key].append(now)
    return True


# --------------------------------------------------------------------------
# Audit Logger Worker
# --------------------------------------------------------------------------
async def queue_audit_log(
    agent: str, tool: str, latency: float, status: str,
    error_message: Optional[str] = None, request_id: Optional[str] = None,
    candidate_id: Optional[int] = None, run_id: Optional[int] = None
):
    global audit_queue_dropped, audit_queue_overflow
    is_critical = (status == "failure") or (agent in ["CircuitBreaker", "DLQ", "Security"])
    
    if _AUDIT_QUEUE.full():
        audit_queue_overflow += 1
        if not is_critical:
            audit_queue_dropped += 1
            logger.warning(f"Audit queue full. Dropping normal audit log for {agent}.{tool}")
            return
        else:
            try:
                _AUDIT_QUEUE.get_nowait()
                audit_queue_dropped += 1
            except asyncio.QueueEmpty:
                pass

    await _AUDIT_QUEUE.put({
        "agent": agent,
        "tool": tool,
        "latency": latency,
        "status": status,
        "error_message": error_message,
        "request_id": request_id,
        "candidate_id": candidate_id,
        "run_id": run_id
    })


async def audit_logger_worker():
    """Background task to batch-write logs every 5 seconds."""
    while True:
        try:
            await asyncio.sleep(5)
            batch = []
            while not _AUDIT_QUEUE.empty():
                batch.append(await _AUDIT_QUEUE.get())
            
            if not batch:
                continue
            
            # Write batch in a single transaction
            db = SessionLocal()
            try:
                for item in batch:
                    log = MCPAuditLog(**item)
                    db.add(log)
                db.commit()
            except Exception as e:
                logger.error(f"Error persisting batch audit logs: {e}")
                db.rollback()
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in audit logger worker: {e}")


# --------------------------------------------------------------------------
# Registry of Local Servers
# --------------------------------------------------------------------------
_SERVERS: Dict[str, Any] = {}

def register_server(server_name: str, server_instance: Any):
    """Registers an MCP server instance."""
    _SERVERS[server_name] = server_instance
    logger.info(f"Registered MCP Server: {server_name}")


def get_registered_servers() -> list:
    return list(_SERVERS.keys())


# --------------------------------------------------------------------------
# Gateway Central Call Routing Tool
# --------------------------------------------------------------------------
class MCPGateway:
    
    async def call_tool(
        self,
        user_id: int,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        db: Session,
        request_id: Optional[str] = None,
        run_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Routes tool execution with full checks: auth, rate limit, feature flags, cache, and breaker.
        """
        start_time = time.perf_counter()
        
        # 1. Authenticate user role and permissions
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found", "status": "auth_error"}
            
        role = user.role or "candidate"
        
        # Check permissions in ToolPermission table
        perm = db.query(ToolPermission).filter(
            ToolPermission.role == role,
            ToolPermission.tool.in_([server_name, "*"])
        ).first()
        
        if not perm and role != "admin" and role != "super_admin":
            # Default fallback checks
            logger.warning(f"No permissions found for role={role} on server={server_name}")
            return {"error": "Permission denied", "status": "auth_error"}

        # 2. Check Feature Flags via local feature flags check
        is_feature_enabled = True
        if server_name in _SERVERS and hasattr(_SERVERS[server_name], "requires_feature"):
            flag_name = _SERVERS[server_name].requires_feature
            ff_server = _SERVERS.get("mcp-server-feature-flags")
            if ff_server:
                is_feature_enabled = ff_server.is_enabled(user_id, flag_name, db)
                
        if not is_feature_enabled:
            return {"error": f"Feature gated: Upgrade your plan to use {server_name}", "status": "feature_gated"}

        # 3. Check Legal Consent for high-risk submission tools
        # High-risk actions: auto-submit and resume upload
        if tool_name in ["submit_application", "upload_resume_pdf", "login_portal"]:
            consent_type = "app_submission"
            if tool_name == "upload_resume_pdf":
                consent_type = "resume_upload"
            elif tool_name == "login_portal":
                consent_type = "account_access"
                
            consent = db.query(UserConsent).filter(
                UserConsent.user_id == user_id,
                UserConsent.consent_type == consent_type,
                UserConsent.granted == True
            ).first()
            
            if not consent:
                logger.warning(f"Block tool {tool_name}: Missing consent {consent_type} for user {user_id}")
                return {"error": f"User consent required for {consent_type}", "status": "consent_required"}

        # 4. Check Rate Limits
        if not _check_rate_limit(user_id, server_name):
            return {"error": "Rate limit exceeded", "status": "rate_limited"}

        # 5. Check Circuit Breaker
        breaker_state = _get_breaker_state(server_name, db)
        if breaker_state == "OPEN":
            return {"error": "Service temporarily unavailable (circuit open)", "status": "circuit_open"}

        # 6. Read Cache check for read-only tools
        cache_key = f"{server_name}:{tool_name}:{json.dumps(arguments, sort_keys=True)}"
        now = time.time()
        if tool_name.startswith("get") or tool_name.startswith("search") or tool_name.startswith("research"):
            cached_val = _READ_CACHE.get(cache_key)
            if cached_val and cached_val[0] > now:
                # Cache Hit!
                latency = (time.perf_counter() - start_time) * 1000.0
                await queue_audit_log(
                    server_name, tool_name, latency, "success_cached",
                    request_id=request_id, candidate_id=user_id, run_id=run_id
                )
                return {"result": cached_val[1], "status": "success", "cached": True}

        # 7. Route and execute tool call
        server_instance = _SERVERS.get(server_name)
        if not server_instance:
            return {"error": f"MCP server '{server_name}' not registered", "status": "not_found"}
            
        handler = getattr(server_instance, tool_name, None)
        if not handler:
            return {"error": f"Tool '{tool_name}' not found on server '{server_name}'", "status": "not_found"}

        status = "success"
        error_msg = None
        result = None
        
        try:
            # Execute tool (handler could be async or sync)
            if asyncio.iscoroutinefunction(handler):
                result = await handler(user_id, arguments, db)
            else:
                result = handler(user_id, arguments, db)
                
            _record_breaker_success(server_name, db)
            
            # Cache read results for 1800s (30m)
            if tool_name.startswith("get") or tool_name.startswith("search") or tool_name.startswith("research"):
                _READ_CACHE[cache_key] = (now + 1800.0, result)
                
        except Exception as exc:
            status = "failure"
            error_msg = str(exc)
            logger.exception(f"Error executing tool {server_name}.{tool_name}: {exc}")
            _record_breaker_failure(server_name, db)
            result = {"error": f"Tool execution failed: {error_msg}"}

        # 8. Queue Audit Log
        latency = (time.perf_counter() - start_time) * 1000.0
        
        # Safe async schedule of audit log
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(queue_audit_log(
                server_name, tool_name, latency, status,
                error_message=error_msg, request_id=request_id,
                candidate_id=user_id, run_id=run_id
            ))
        except RuntimeError:
            # Sync fallback
            try:
                log = MCPAuditLog(
                    agent=server_name, tool=tool_name, latency=latency, status=status,
                    error_message=error_msg, request_id=request_id,
                    candidate_id=user_id, run_id=run_id
                )
                db.add(log)
                db.commit()
            except Exception as e:
                logger.error(f"Fallback audit log failed: {e}")

        return {"result": result, "status": status}


# Gateway Singleton
gateway = MCPGateway()
