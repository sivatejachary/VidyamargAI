"""
VidyaMarg AI — Abstract Connector Base Class
=============================================
Every job discovery connector MUST inherit from BaseJobConnector.

Contract:
  - authenticate()     → Verify credentials / session validity
  - health_check()     → Lightweight probe to verify source is accessible
  - discover_jobs()    → Fetch raw jobs from remote source
  - normalize()        → Map source-specific fields to canonical RawJob schema

Design principles:
  - Failure of one connector MUST NEVER crash or block others
  - All network calls must be async
  - Timeouts must be respected
  - Circuit breaker state is tracked externally (in ConnectorRegistry)
"""
from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.job_discovery.domain.models import RawJob

logger = logging.getLogger("jd.connectors.base")


@dataclass
class ConnectorConfig:
    """Configuration passed to every connector at instantiation."""
    name: str
    display_name: str
    source_type: str  # api | scraper | rss | telegram | partner
    base_url: str = ""
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    rate_limit_rpm: int = 60
    max_results: int = 200
    timeout_seconds: int = 30
    max_retries: int = 3
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectorResult:
    """Structured result returned by discover_jobs()."""
    connector_name: str
    jobs: List[RawJob]
    success: bool
    jobs_found: int = 0
    error_message: Optional[str] = None
    latency_ms: int = 0

    def __post_init__(self) -> None:
        self.jobs_found = len(self.jobs)


class BaseJobConnector(ABC):
    """
    Abstract base for all job discovery connectors.
    All methods except normalize() are async.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config
        self.name = config.name
        self.logger = logging.getLogger(f"jd.connectors.{config.name}")
        self._request_headers: Dict[str, str] = {
            "User-Agent": "VidyaMargAI-Agent/2.0 (+https://vidyamarg.ai)",
            "Accept": "application/json, text/html;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
        }

    # ------------------------------------------------------------------
    # Required contract methods
    # ------------------------------------------------------------------

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Verifies credentials/session validity.
        Returns True if authentication is successful, False otherwise.
        Must not raise exceptions — return False on any failure.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Lightweight probe to check if the remote source is accessible.
        Should return within TIMEOUT_SECONDS.
        Returns True if source is healthy, False otherwise.
        """

    @abstractmethod
    async def discover_jobs(
        self, query_params: Dict[str, Any]
    ) -> ConnectorResult:
        """
        Fetches raw job data from the target source.
        Must catch ALL exceptions internally and return ConnectorResult(success=False).
        Must respect self.config.max_results limit.
        """

    @abstractmethod
    def normalize(self, raw_payload: Dict[str, Any]) -> Optional[RawJob]:
        """
        Synchronous normalization of a single source-specific job dict
        into a canonical RawJob domain model.
        Returns None if the payload cannot be normalized.
        """

    # ------------------------------------------------------------------
    # Utility helpers (available to all subclasses)
    # ------------------------------------------------------------------

    def make_external_id(self, *parts: str) -> str:
        """Generates a deterministic MD5-based external ID."""
        combined = ":".join([self.name] + list(parts))
        return hashlib.md5(combined.encode("utf-8")).hexdigest()

    def extract_skills(self, text: str) -> List[str]:
        """
        Heuristic skill extraction from free text.
        Looks for common tech keywords. Subclasses should override with
        source-specific extraction if structured skill data is available.
        """
        known_skills = {
            "python", "java", "javascript", "typescript", "go", "rust", "kotlin",
            "swift", "c++", "c#", "sql", "nosql", "postgresql", "mysql", "mongodb",
            "redis", "elasticsearch", "kafka", "rabbitmq", "aws", "azure", "gcp",
            "docker", "kubernetes", "terraform", "fastapi", "django", "flask",
            "react", "vue", "angular", "node.js", "graphql", "rest", "grpc",
            "machine learning", "deep learning", "nlp", "pytorch", "tensorflow",
            "spark", "hadoop", "airflow", "dbt", "data engineering", "devops",
            "ci/cd", "jenkins", "github actions", "linux", "bash", "git",
        }
        text_lower = text.lower()
        return [skill for skill in known_skills if skill in text_lower]

    def safe_float(self, value: Any) -> Optional[float]:
        """Safely converts a value to float, returning None on failure."""
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def timed(self, func_name: str) -> "_Timer":
        """Returns a context manager for timing operations."""
        return _Timer(func_name, self.logger)


class _Timer:
    """Simple context manager for timing code blocks."""

    def __init__(self, label: str, log: logging.Logger) -> None:
        self._label = label
        self._log = log
        self._start = 0.0

    def __enter__(self) -> "_Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        elapsed_ms = int((time.perf_counter() - self._start) * 1000)
        self._log.debug(f"[{self._label}] completed in {elapsed_ms}ms")
        self.elapsed_ms = elapsed_ms
