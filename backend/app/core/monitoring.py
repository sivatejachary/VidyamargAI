import contextvars
import logging
import os
import time
from typing import Optional

logger = logging.getLogger("app.monitoring")

# ContextVars — one per request via token-reset pattern
db_queries_var: contextvars.ContextVar[int] = contextvars.ContextVar("db_queries", default=0)
db_query_time_var: contextvars.ContextVar[float] = contextvars.ContextVar("db_query_time", default=0.0)
cache_status_var: contextvars.ContextVar[str] = contextvars.ContextVar("cache_status", default="BYPASS")


def is_production() -> bool:
    return os.getenv("ENV") == "production" or os.getenv("ENVIRONMENT") == "production"


def is_testing() -> bool:
    return os.getenv("TESTING") == "true"
