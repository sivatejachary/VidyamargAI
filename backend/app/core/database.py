import time
import logging
import os
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings
from app.core.monitoring import db_queries_var, db_query_time_var, cache_status_var

logger = logging.getLogger("app.db")

# Connection pool settings safe for Railway
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,
    connect_args={
        "options": "-c idle_in_transaction_session_timeout=120000 -c lock_timeout=5000"
    }
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
    try:
        # Accumulate DB query execution time
        current_time = db_query_time_var.get()
        db_query_time_var.set(current_time + duration)
    except Exception:
        pass

    if duration > 0.2:
        logger.warning(f"Slow Query ({duration:.2f}s): {statement[:200]}")
        # Run EXPLAIN ANALYZE only in development to prevent overhead in production
        is_prod = (
            os.getenv("ENV") == "production" or 
            os.getenv("ENVIRONMENT") == "production"
        )
        is_testing = os.getenv("TESTING") == "true"
        if not is_prod and not is_testing:
            try:
                with engine.connect() as explain_conn:
                    dbapi_conn = explain_conn.connection
                    with dbapi_conn.cursor() as explain_cursor:
                        explain_cursor.execute(f"EXPLAIN ANALYZE {statement}", parameters)
                        explain_res = explain_cursor.fetchall()
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

