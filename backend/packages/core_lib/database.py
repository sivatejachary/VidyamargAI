import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

logger = logging.getLogger("packages.core_lib.database")

Base = declarative_base()

class DatabaseManager:
    """
    Database connection manager supporting async engines and connection pooling.
    """
    def __init__(self, database_url: str, echo: bool = False):
        self.database_url = database_url
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
            
        logger.info(f"Initializing async database engine with URL masked prefix: {self.database_url.split('@')[-1] if '@' in self.database_url else self.database_url}")
        
        self.engine = create_async_engine(
            self.database_url,
            echo=echo,
            pool_size=20,
            max_overflow=10,
            pool_recycle=1800,
            pool_pre_ping=True,
            connect_args={
                "server_settings": {
                    "search_path": "vidyamarg"
                }
            }
        )
        
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            class_=AsyncSession
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Dependency generator yielding async database sessions."""
        async with self.session_factory() as session:
            try:
                yield session
            except Exception as e:
                logger.error(f"Database session encountered error: {e}")
                await session.rollback()
                raise e
            finally:
                await session.close()

    async def close(self):
        """Closes the connection pool."""
        await self.engine.dispose()
        logger.info("Database connection pool disposed.")
