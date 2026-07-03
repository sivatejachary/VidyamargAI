from typing import Dict, Any, Callable, Awaitable
from app.job_discovery.workers.dead_letter import send_to_dlq
from app.core.event_bus import event_bus
import logging

logger = logging.getLogger("app.job_discovery.workers.retry")

class WorkerRetryHandler:
    """
    Implements a 3-strike retry policy for asynchronous stream events.
    """
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    async def execute_with_retry(
        self,
        stream: str,
        event: Dict[str, Any],
        handler_func: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        try:
            await handler_func(event)
        except Exception as exc:
            metadata = event.setdefault("_metadata", {})
            retries = metadata.get("retries", 0)
            if retries < self.max_retries:
                # Increment retry count
                metadata["retries"] = retries + 1
                
                logger.warning(
                    f"[Retry] Error in stream '{stream}'. Attempt {retries + 1}/{self.max_retries} failed: {exc}. "
                    f"Re-queueing event..."
                )
                
                # Re-publish back to stream to retry
                try:
                    await event_bus.publish(stream, event)
                except Exception as pub_exc:
                    logger.critical(f"[Retry] Re-publish failed: {pub_exc}. Routing to DLQ.")
                    await send_to_dlq(stream, event, f"Re-publish failed: {str(pub_exc)}")
            else:
                # Exceeded max retries
                reason = f"Exceeded max retries ({self.max_retries}). Last error: {str(exc)}"
                logger.error(f"[Retry] Strike {self.max_retries} failed. Routing to DLQ: {reason}")
                await send_to_dlq(stream, event, reason)
