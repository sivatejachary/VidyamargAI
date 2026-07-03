"""
VidyaMarg AI — Job Discovery FastAPI Application
=================================================
Standalone FastAPI micro-service for the Job Discovery bounded context.
Runs independently from the main AI OS backend on port 8100.

Startup lifecycle:
  1. Connect Redis Buffer
  2. Connect Redis Event Broker
  3. Connect Qdrant Vector Store
  4. Initialize database tables (dev) or verify via Alembic (prod)
  5. Mount all API routers
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.job_discovery import config as cfg
from app.job_discovery.api.v1 import jobs, matching, monitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("jd.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application startup and shutdown lifecycle manager."""
    # ------------------------------------------------------------------
    # STARTUP
    # ------------------------------------------------------------------
    logger.info("=== Job Discovery Platform starting up ===")

    # 1. Redis Collector Buffer
    from app.job_discovery.infrastructure.redis.buffer import get_collector_buffer
    buffer = get_collector_buffer()
    await buffer.connect()

    # 2. Redis Event Broker
    from app.job_discovery.infrastructure.redis.stream import get_event_broker
    broker = get_event_broker()
    await broker.connect()

    # 3. Qdrant Vector Store
    from app.job_discovery.infrastructure.qdrant.client import get_qdrant_store
    qdrant = get_qdrant_store()
    await qdrant.connect()

    # 4. Ensure consumer groups exist for all workers
    consumer_groups = [
        "jd_embedding_workers",
        "jd_matching_workers",
        "jd_recommendation_workers",
        "jd_notification_workers",
    ]
    for group in consumer_groups:
        await broker.ensure_consumer_group(group)

    logger.info("=== Job Discovery Platform ready ===")
    yield

    # ------------------------------------------------------------------
    # SHUTDOWN
    # ------------------------------------------------------------------
    logger.info("=== Job Discovery Platform shutting down ===")
    await buffer.close()
    await broker.close()
    await qdrant.close()
    from app.job_discovery.infrastructure.database.session import dispose_engine
    await dispose_engine()
    logger.info("=== Shutdown complete ===")


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="VidyaMarg AI — Job Discovery Platform",
    description=(
        "Autonomous job discovery, normalization, embedding, and matching engine. "
        "This API is the exclusive interface for Tush AI to access job data. "
        "The AI OS MUST NOT access the database directly."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to AI OS service IP in production
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

app.include_router(jobs.router, prefix="/api/v1")
app.include_router(matching.router, prefix="/api/v1")
app.include_router(monitor.router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "VidyaMarg AI — Job Discovery Platform",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.job_discovery.main:app",
        host=cfg.API_HOST,
        port=cfg.API_PORT,
        reload=False,
        workers=4,
        log_level="info",
    )
