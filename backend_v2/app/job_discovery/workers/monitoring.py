"""
VidyaMarg AI — Monitoring Worker
==================================
Proactive health checks for all critical system components.

Checks performed every 5 minutes:
  ✔ PostgreSQL   — asyncpg connect + SELECT 1
  ✔ Redis        — PING
  ✔ Qdrant       — get_collection_info
  ✔ Connectors   — circuit breaker states via ConnectorRegistry
  ✔ Celery queues — reserved task counts via celery.control.inspect()

If any critical component (PG / Redis / Qdrant) is offline the worker
sends a Slack alert via cfg.SLACK_WEBHOOK_URL (if configured).

Returns a structured health dict suitable for the /health API endpoint.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.job_discovery.workers.celery_app import celery_app
from app.job_discovery import config as cfg

logger = logging.getLogger("jd.workers.monitoring")

# Components whose failure should trigger an alert
_CRITICAL_COMPONENTS = {"postgres", "redis", "qdrant"}


# ---------------------------------------------------------------------------
# Individual health-check coroutines
# ---------------------------------------------------------------------------

async def _check_postgres() -> str:
    """Returns 'healthy' if a SELECT 1 succeeds, else 'offline'."""
    try:
        import asyncpg  # type: ignore[import]

        # Parse a plain psycopg-style URL into asyncpg kwargs
        dsn = cfg.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn=dsn, timeout=10)
        await conn.fetchval("SELECT 1")
        await conn.close()
        return "healthy"
    except Exception as exc:  # noqa: BLE001
        logger.error("[monitoring] PostgreSQL health check failed: %s", exc)
        return "offline"


async def _check_redis() -> str:
    """Returns 'healthy' if Redis responds to PING, else 'offline'."""
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(
            cfg.REDIS_URL, encoding="utf-8", decode_responses=True, socket_timeout=5
        )
        await client.ping()
        await client.aclose()
        return "healthy"
    except Exception as exc:  # noqa: BLE001
        logger.error("[monitoring] Redis health check failed: %s", exc)
        return "offline"


async def _check_qdrant() -> str:
    """Returns 'healthy' if Qdrant collection info is retrievable, else 'offline'."""
    try:
        from qdrant_client import AsyncQdrantClient

        client = AsyncQdrantClient(
            url=cfg.QDRANT_URL,
            api_key=cfg.QDRANT_API_KEY,
            timeout=10,
        )
        await client.get_collection(cfg.QDRANT_COLLECTION_NAME)
        await client.close()
        return "healthy"
    except Exception as exc:  # noqa: BLE001
        logger.error("[monitoring] Qdrant health check failed: %s", exc)
        return "offline"


def _get_circuit_states() -> Dict[str, str]:
    """Returns {connector_name: circuit_state_str} from the connector registry."""
    try:
        from app.job_discovery.connectors.registry import get_registry

        registry = get_registry()
        return registry.get_circuit_states()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[monitoring] Could not fetch circuit states: %s", exc)
        return {}


def _get_queue_depths() -> Dict[str, int]:
    """
    Inspects active Celery workers and returns reserved task counts per queue.
    Falls back to {} if no workers respond within the timeout.
    """
    try:
        inspector = celery_app.control.inspect(timeout=5.0)
        reserved: Optional[Dict[str, Any]] = inspector.reserved()
        if not reserved:
            return {}

        depths: Dict[str, int] = {}
        for worker_name, tasks in reserved.items():
            if isinstance(tasks, list):
                for task in tasks:
                    queue = task.get("delivery_info", {}).get("routing_key", "default")
                    depths[queue] = depths.get(queue, 0) + 1
        return depths
    except Exception as exc:  # noqa: BLE001
        logger.warning("[monitoring] Could not inspect Celery queues: %s", exc)
        return {}


def _send_slack_alert(offline_components: list, health: Dict[str, Any]) -> None:
    """
    Fires a Slack webhook notification when critical components are offline.
    Silently skips if cfg.SLACK_WEBHOOK_URL is not configured.
    """
    if not cfg.SLACK_WEBHOOK_URL:
        return

    component_list = ", ".join(f"`{c}`" for c in offline_components)
    message = {
        "text": (
            f"🚨 *VidyaMarg AI — System Alert*\n"
            f"Critical components offline: {component_list}\n"
            f"Checked at: `{health['checked_at']}`\n"
            f"Full health: ```{json.dumps(health, indent=2)}```"
        )
    }

    try:
        payload = json.dumps(message).encode("utf-8")
        req = urllib.request.Request(
            cfg.SLACK_WEBHOOK_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
        logger.info("[monitoring] Slack alert sent — HTTP %d", status)
    except Exception as exc:  # noqa: BLE001
        logger.error("[monitoring] Slack alert failed: %s", exc)


# ---------------------------------------------------------------------------
# Celery Task
# ---------------------------------------------------------------------------

@celery_app.task(name="app.workers.monitoring.run_health_checks")
def run_health_checks() -> Dict[str, Any]:
    """
    Runs comprehensive health checks across all system components.

    Returns:
        {
            'postgres':   'healthy' | 'offline',
            'redis':      'healthy' | 'offline',
            'qdrant':     'healthy' | 'offline',
            'connectors': { connector_name: circuit_state, ... },
            'queues':     { queue_name: reserved_count, ... },
            'checked_at': '<ISO 8601 UTC timestamp>',
        }

    Side effects:
        • Logs a WARNING for each offline critical component.
        • Sends a Slack alert (via cfg.SLACK_WEBHOOK_URL) if any critical
          component is offline.
    """
    logger.info("[monitoring] run_health_checks — starting")
    t0 = time.monotonic()

    # ----------------------------------------------------------------
    # Run async checks concurrently
    # ----------------------------------------------------------------
    async def _gather_checks():
        pg, redis, qdrant = await asyncio.gather(
            _check_postgres(),
            _check_redis(),
            _check_qdrant(),
            return_exceptions=False,
        )
        return pg, redis, qdrant

    loop = asyncio.new_event_loop()
    try:
        pg_status, redis_status, qdrant_status = loop.run_until_complete(_gather_checks())
    finally:
        loop.close()

    # ----------------------------------------------------------------
    # Sync checks (registry + Celery inspect)
    # ----------------------------------------------------------------
    circuit_states = _get_circuit_states()
    queue_depths = _get_queue_depths()

    health: Dict[str, Any] = {
        "postgres": pg_status,
        "redis": redis_status,
        "qdrant": qdrant_status,
        "connectors": circuit_states,
        "queues": queue_depths,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": int((time.monotonic() - t0) * 1000),
    }

    # ----------------------------------------------------------------
    # Alert on critical failures
    # ----------------------------------------------------------------
    offline = [
        component
        for component in _CRITICAL_COMPONENTS
        if health.get(component) == "offline"
    ]

    if offline:
        logger.error(
            "[monitoring] CRITICAL — components offline: %s | health=%s",
            offline,
            json.dumps(health),
        )
        _send_slack_alert(offline, health)
    else:
        logger.info(
            "[monitoring] All systems healthy — duration_ms=%d",
            health["duration_ms"],
        )

    # Log warnings for open connector circuits
    for connector, state in circuit_states.items():
        if state == "open":
            logger.warning(
                "[monitoring] Connector '%s' circuit breaker OPEN — all requests rejected.",
                connector,
            )

    # Log warning if any queue is deep
    for queue, depth in queue_depths.items():
        if depth > cfg.QUEUE_DEPTH_ALERT_THRESHOLD:
            logger.warning(
                "[monitoring] Queue '%s' depth %d exceeds threshold %d.",
                queue,
                depth,
                cfg.QUEUE_DEPTH_ALERT_THRESHOLD,
            )

    return health
