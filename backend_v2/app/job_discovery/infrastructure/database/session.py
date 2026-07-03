"""
VidyaMarg AI — Async Database Session Factory
=============================================
Uses SQLAlchemy 2.x async engine with asyncpg driver.
Connection pooling is configured for production-scale concurrency.
pgBouncer should sit in front of PostgreSQL in production.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.job_discovery import config as cfg

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

engine = create_async_engine(
    cfg.DATABASE_URL,
    pool_size=cfg.DATABASE_POOL_SIZE,
    max_overflow=cfg.DATABASE_MAX_OVERFLOW,
    pool_timeout=cfg.DATABASE_POOL_TIMEOUT,
    pool_pre_ping=True,           # Validates connections before use
    pool_recycle=1800,            # Recycle connections after 30 minutes
    echo=False,                   # Set True for SQL query logging in dev
)

# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that provides a database session.
    Automatically commits on success, rolls back on exception,
    and closes the session in the finally block.

    Usage:
        async with get_async_session() as session:
            result = await session.execute(stmt)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables() -> None:
    """
    Creates all ORM-mapped tables that do not yet exist.
    Should only be used in development/testing.
    In production, use Alembic migrations.
    """
    from app.job_discovery.infrastructure.database.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Dispose the engine connection pool. Call on application shutdown."""
    await engine.dispose()
