import asyncio
import logging
import time
from functools import wraps
from datetime import datetime
from app.models.mcp_models import MCPAuditLog
from app.core.database import SessionLocal

logger = logging.getLogger("app.services.mcp_audit")
_AUDIT_QUEUE = asyncio.Queue(maxsize=10000)

# Drop / overflow counters
audit_queue_dropped = 0
audit_queue_overflow = 0

def get_queue_size() -> int:
    return _AUDIT_QUEUE.qsize()

def get_dropped_count() -> int:
    global audit_queue_dropped
    return audit_queue_dropped

def get_overflow_count() -> int:
    global audit_queue_overflow
    return audit_queue_overflow

async def queue_audit_log(agent: str, tool: str, latency: float, status: str, error_message: str = None, request_id: str = None, candidate_id: int = None, run_id: int = None):
    global audit_queue_dropped, audit_queue_overflow
    is_critical = (status == "failure") or (agent in ["CircuitBreaker", "DLQ", "Security"])
    
    if _AUDIT_QUEUE.full():
        audit_queue_overflow += 1
        if not is_critical:
            audit_queue_dropped += 1
            logger.warning(f"Audit queue full. Dropped normal audit log for {agent}.{tool}")
            return
        else:
            try:
                # Discard oldest normal log to make space for critical event
                _AUDIT_QUEUE.get_nowait()
                audit_queue_dropped += 1
            except asyncio.QueueEmpty:
                pass

    try:
        await _AUDIT_QUEUE.put({
            "agent": agent,
            "tool": tool,
            "latency": latency,
            "status": status,
            "error_message": error_message,
            "request_id": request_id,
            "candidate_id": candidate_id,
            "run_id": run_id,
            "created_at": datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Failed to put log in audit queue: {e}")

def audit_tool_call(func):
    """Decorator to measure tool latency and queue audit logs safely across event loops."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        from app.services.circuit_breaker import allow_request, record_success, record_failure

        # Resolve correlation IDs from args or kwargs
        candidate_id = kwargs.get("candidate_id") or kwargs.get("user_id")
        run_id = kwargs.get("run_id")
        request_id = kwargs.get("request_id")
        
        # Try finding candidate_id from args if not in kwargs
        if not candidate_id and len(args) > 0:
            for arg in args:
                if isinstance(arg, int) and arg > 0:
                    candidate_id = arg
                    break

        agent_name = getattr(self, "server_name", self.__class__.__name__)
        start_time = time.perf_counter()
        status = "success"
        err_msg = None

        # 1. Check Circuit Breaker
        if not allow_request(agent_name):
            status = "failure"
            err_msg = f"Circuit breaker is OPEN for {agent_name}. Fast-failing request."
            latency = 0.0
            
            # Queue audit log for circuit breaker fail-fast event
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(queue_audit_log(
                    agent=agent_name,
                    tool=func.__name__,
                    latency=latency,
                    status=status,
                    error_message=err_msg,
                    request_id=request_id,
                    candidate_id=candidate_id,
                    run_id=run_id
                ))
            except RuntimeError:
                try:
                    with SessionLocal() as audit_db:
                        log = MCPAuditLog(
                            agent=agent_name,
                            tool=func.__name__,
                            latency=latency,
                            status=status,
                            error_message=err_msg,
                            request_id=request_id,
                            candidate_id=candidate_id,
                            run_id=run_id
                        )
                        audit_db.add(log)
                        audit_db.commit()
                except Exception as db_err:
                    logger.error(f"Fallback audit write failed: {db_err}")
            raise RuntimeError(err_msg)

        # 2. Execute call
        try:
            res = func(self, *args, **kwargs)
            record_success(agent_name)
            return res
        except Exception as e:
            record_failure(agent_name)
            status = "failure"
            err_msg = str(e)
            raise e
        finally:
            # Only log latency for actual calls that were executed
            if status != "failure" or "Fast-failing request" not in (err_msg or ""):
                latency = (time.perf_counter() - start_time) * 1000.0
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(queue_audit_log(
                        agent=agent_name,
                        tool=func.__name__,
                        latency=latency,
                        status=status,
                        error_message=err_msg,
                        request_id=request_id,
                        candidate_id=candidate_id,
                        run_id=run_id
                    ))
                except RuntimeError:
                    try:
                        with SessionLocal() as audit_db:
                            log = MCPAuditLog(
                                agent=agent_name,
                                tool=func.__name__,
                                latency=latency,
                                status=status,
                                error_message=err_msg,
                                request_id=request_id,
                                candidate_id=candidate_id,
                                run_id=run_id
                            )
                            audit_db.add(log)
                            audit_db.commit()
                    except Exception as db_err:
                        logger.error(f"Fallback audit write failed: {db_err}")
    return wrapper

async def audit_logger_worker():
    """Background task to batch-write logs every 5 seconds."""
    logger.info("Background audit logger worker started.")
    while True:
        try:
            await asyncio.sleep(5)
            batch = []
            while not _AUDIT_QUEUE.empty():
                try:
                    batch.append(_AUDIT_QUEUE.get_nowait())
                except asyncio.QueueEmpty:
                    break
            
            if not batch:
                continue
            
            with SessionLocal() as db:
                try:
                    for item in batch:
                        log = MCPAuditLog(
                            agent=item["agent"],
                            tool=item["tool"],
                            latency=item["latency"],
                            status=item["status"],
                            error_message=item["error_message"],
                            request_id=item["request_id"],
                            candidate_id=item["candidate_id"],
                            run_id=item["run_id"],
                            created_at=item["created_at"]
                        )
                        db.add(log)
                    db.commit()
                except Exception as e:
                    logger.error(f"Error persisting batch audit logs: {e}")
                    db.rollback()
        except asyncio.CancelledError:
            logger.info("Audit logger worker cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in audit logger worker: {e}")
