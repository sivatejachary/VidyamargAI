"""
VidyaMarg AI — FastAPI Dependency Injection
============================================
All shared dependencies for the API layer.
Provides database sessions, Qdrant client access, and API key validation.
"""
from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.job_discovery import config as cfg
from app.job_discovery.infrastructure.database.session import AsyncSessionLocal
from app.job_discovery.infrastructure.qdrant.client import get_qdrant_store

# ---------------------------------------------------------------------------
# API Key Authentication
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(_api_key_header)) -> str:
    """
    Validates the X-API-Key header.
    Tush AI must include this header in every request to the Job Discovery API.
    """
    if not api_key or api_key != cfg.API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Include X-API-Key header.",
        )
    return api_key


# ---------------------------------------------------------------------------
# Database Session
# ---------------------------------------------------------------------------

async def get_db_session() -> AsyncGenerator:
    """Yields an async SQLAlchemy session. Auto-commits on success, rollbacks on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Qdrant Client
# ---------------------------------------------------------------------------

async def get_qdrant():
    """Returns the singleton Qdrant vector store instance."""
    return get_qdrant_store()
