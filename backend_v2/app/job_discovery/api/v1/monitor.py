"""
VidyaMarg AI — Monitoring & Health Dashboard API
=================================================
Provides real-time system health, connector status, queue metrics,
and pipeline statistics for the operations dashboard.

Endpoints:
  GET /api/v1/monitor/health        — System-wide health check
  GET /api/v1/monitor/connectors    — All connector statuses
  GET /api/v1/monitor/pipeline      — Recent crawl history
  GET /api/v1/monitor/qdrant        — Vector DB stats
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.job_discovery.api.dependency import get_db_session, verify_api_key
from app.job_discovery.connectors.registry import get_registry
from app.job_discovery.infrastructure.qdrant.client import get_qdrant_store

logger = logging.getLogger("jd.api.monitor")
router = APIRouter(prefix="/monitor", tags=["Monitoring"])


class ComponentHealth(BaseModel):
    component: str
    status: str
    latency_ms: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class SystemHealthResponse(BaseModel):
    overall_status: str
    checked_at: str
    components: List[ComponentHealth]


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="Full system health check",
)
async def system_health(
    _: str = Depends(verify_api_key),
    session=Depends(get_db_session),
) -> SystemHealthResponse:
    """Returns health status of all system components."""
    import time
    components: List[ComponentHealth] = []
    any_critical_failure = False

    # 1. PostgreSQL
    try:
        start = time.perf_counter()
        from sqlalchemy import text
        await session.execute(text("SELECT 1"))
        latency = int((time.perf_counter() - start) * 1000)
        components.append(ComponentHealth(component="postgresql", status="healthy", latency_ms=latency))
    except Exception as exc:
        any_critical_failure = True
        components.append(ComponentHealth(component="postgresql", status="offline", details={"error": str(exc)}))

    # 2. Qdrant
    try:
        start = time.perf_counter()
        qdrant = get_qdrant_store()
        is_ok = await qdrant.is_healthy()
        latency = int((time.perf_counter() - start) * 1000)
        components.append(ComponentHealth(
            component="qdrant",
            status="healthy" if is_ok else "offline",
            latency_ms=latency,
        ))
    except Exception as exc:
        components.append(ComponentHealth(component="qdrant", status="offline", details={"error": str(exc)}))

    # 3. Connector circuit states
    registry = get_registry()
    circuit_states = registry.get_circuit_states()
    open_circuits = [name for name, state in circuit_states.items() if state == "open"]
    components.append(ComponentHealth(
        component="connectors",
        status="degraded" if open_circuits else "healthy",
        details={
            "circuit_states": circuit_states,
            "open_circuits": open_circuits,
        },
    ))

    overall = "healthy" if not any_critical_failure else "degraded"
    return SystemHealthResponse(
        overall_status=overall,
        checked_at=datetime.utcnow().isoformat() + "Z",
        components=components,
    )


@router.get(
    "/connectors",
    summary="List all connector statuses and circuit breaker states",
)
async def get_connector_statuses(_: str = Depends(verify_api_key)) -> Dict[str, Any]:
    """Returns full connector registry details including circuit breaker state."""
    registry = get_registry()
    return {
        "connectors": registry.list_all(),
        "checked_at": datetime.utcnow().isoformat() + "Z",
    }


@router.get(
    "/pipeline",
    summary="Recent crawl history and pipeline metrics",
)
async def get_pipeline_stats(
    hours: int = 24,
    _: str = Depends(verify_api_key),
    session=Depends(get_db_session),
) -> Dict[str, Any]:
    """Returns aggregated stats from the last N hours of crawl history."""
    from sqlalchemy import func, select
    from app.job_discovery.infrastructure.database.models import CrawlHistoryORM

    cutoff = datetime.utcnow() - timedelta(hours=hours)
    stmt = select(CrawlHistoryORM).where(CrawlHistoryORM.started_at >= cutoff)
    result = await session.execute(stmt)
    crawls = result.scalars().all()

    return {
        "period_hours": hours,
        "total_runs": len(crawls),
        "total_jobs_found": sum(c.jobs_found or 0 for c in crawls),
        "total_jobs_saved": sum(c.jobs_saved or 0 for c in crawls),
        "successful_runs": sum(1 for c in crawls if c.status == "success"),
        "failed_runs": sum(1 for c in crawls if c.status == "failed"),
        "by_source": {
            name: {
                "runs": sum(1 for c in crawls if c.source_name == name),
                "jobs_found": sum(c.jobs_found or 0 for c in crawls if c.source_name == name),
            }
            for name in set(c.source_name for c in crawls)
        },
    }


@router.get(
    "/qdrant",
    summary="Qdrant vector DB statistics",
)
async def get_qdrant_stats(_: str = Depends(verify_api_key)) -> Dict[str, Any]:
    """Returns Qdrant collection statistics including vector count and index status."""
    qdrant = get_qdrant_store()
    info = await qdrant.get_collection_info()
    if not info:
        return {"status": "offline", "message": "Qdrant unavailable"}
    return {"status": "online", **info, "checked_at": datetime.utcnow().isoformat() + "Z"}
