"""
Dead Letter Queue — Persistent DLQ for unrecoverable worker events.

Events that exceed max_retries are written here with full context:
  - original stream
  - event payload
  - error reason
  - timestamp

Stored in Redis Stream `jobs.failed.dlq` with MAXLEN cap to bound memory.
Also written to DB (AgentNotification) for admin visibility.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict

from app.core.event_bus import event_bus

logger = logging.getLogger("app.job_discovery.workers.dead_letter")

_DLQ_STREAM = "jobs.failed.dlq"
_DLQ_MAXLEN = 10_000  # ring-buffer — discard oldest beyond this


async def send_to_dlq(
    stream: str,
    event: Dict[str, Any],
    reason: str,
) -> None:
    """
    Persist a failed event to the Dead Letter Queue.

    Writes to:
      1. Redis Stream `jobs.failed.dlq` (for operator tooling)
      2. AgentNotification table (for admin portal visibility) — best-effort
    """
    dlq_payload: Dict[str, Any] = {
        "original_stream": stream,
        "event": event,
        "reason": reason,
        "failed_at": datetime.utcnow().isoformat(),
    }

    # 1. Redis DLQ stream
    try:
        await event_bus.publish(_DLQ_STREAM, dlq_payload)
        logger.error(
            f"[DLQ] Event routed to DLQ. stream='{stream}' reason='{reason[:200]}'"
        )
    except Exception as exc:
        logger.critical(
            f"[DLQ] Could not write to Redis DLQ — event LOST. "
            f"stream='{stream}' exc={exc} payload={json.dumps(dlq_payload)[:500]}"
        )

    # 2. Admin DB notification (best-effort, never raises)
    try:
        from app.core.database import SessionLocal
        from app.models.job_models import AgentNotification

        with SessionLocal() as db:
            db.add(
                AgentNotification(
                    candidate_id=event.get("candidate_id"),
                    title=f"[DLQ] Failed event on stream: {stream}",
                    content=f"Reason: {reason[:500]}",
                    is_read=False,
                )
            )
            db.commit()
    except Exception as exc:
        logger.warning(f"[DLQ] DB notification write failed (non-fatal): {exc}")
