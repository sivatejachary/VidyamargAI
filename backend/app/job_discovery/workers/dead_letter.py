from typing import Dict, Any
from app.core.event_bus import event_bus
import logging

logger = logging.getLogger("app.job_discovery.workers.dead_letter")

async def send_to_dlq(stream: str, event: Dict[str, Any], reason: str):
    """
    Publishes the failed event payload to jobs.failed.dlq with error details.
    """
    dlq_payload = {
        "original_stream": stream,
        "failed_event": event,
        "reason": reason,
    }
    try:
        await event_bus.publish("jobs.failed.dlq", dlq_payload)
        logger.error(f"[DLQ] Routed failed event from '{stream}' to 'jobs.failed.dlq'. Reason: {reason}")
    except Exception as e:
        logger.critical(f"[DLQ] Failed to publish to DLQ: {e}. Lost payload: {dlq_payload}")
