import contextvars
import time
import logging
import os
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

logger = logging.getLogger("app.db")

# Performance tracking ContextVars
db_queries_var = contextvars.ContextVar("db_queries", default=0)
cache_status_var = contextvars.ContextVar("cache_status", default="BYPASS")

# Connection pool settings safe for Railway
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Slow Query Monitoring Listeners
@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.perf_counter()
    try:
        # Increment request database query counter
        current_count = db_queries_var.get()
        db_queries_var.set(current_count + 1)
    except Exception:
        pass

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    duration = time.perf_counter() - context._query_start_time
    if duration > 0.2:
        logger.warning(f"Slow Query ({duration:.2f}s): {statement[:200]}")
        # Run EXPLAIN ANALYZE only in development to prevent overhead in production
        if os.getenv("ENV") != "production" and os.getenv("TESTING") != "true":
            try:
                with engine.connect() as explain_conn:
                    explain_res = explain_conn.execute(text(f"EXPLAIN ANALYZE {statement}"), parameters).fetchall()
                    logger.warning("EXPLAIN ANALYZE:\n" + "\n".join([line[0] for line in explain_res]))
            except Exception as explain_err:
                logger.warning(f"Could not run EXPLAIN: {explain_err}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

