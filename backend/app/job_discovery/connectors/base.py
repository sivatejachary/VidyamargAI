"""
Base Connector — Abstract async interface for all job source connectors.

Every connector must:
  • Implement async_search() using httpx.AsyncClient (non-blocking)
  • Return a list of raw job dicts matching the canonical schema
  • Handle errors internally and log them; never propagate exceptions
  • Set source_name on every returned record
"""
from __future__ import annotations

import abc
import logging
from typing import Any, Dict, List

import httpx

logger = logging.getLogger("app.job_discovery.connectors.base")

# Canonical raw-job schema keys — all connectors must produce these
CANONICAL_KEYS = frozenset({
    "external_id", "title", "company_name", "description",
    "apply_url", "job_url", "location", "city", "state", "country",
    "is_remote", "is_hybrid", "role_category", "industry", "seniority",
    "employment_type", "required_skills", "preferred_skills",
    "salary_min", "salary_max", "salary_currency", "salary_raw",
    "experience_min_years", "experience_max_years",
    "posted_at", "source_name",
})


class BaseConnector(abc.ABC):
    """
    Abstract base class for all async job source connectors.

    Sub-classes must implement `async_search`. The `search` sync wrapper
    is intentionally removed — callers must use `async_search` exclusively.
    """

    # Override per connector
    SOURCE_NAME: str = "unknown"
    DEFAULT_TIMEOUT: float = 20.0
    MAX_RESULTS_PER_QUERY: int = 10

    def _build_empty_job(self) -> Dict[str, Any]:
        """Returns a blank canonical job dict with sensible defaults."""
        return {
            "external_id": None,
            "title": "",
            "company_name": "",
            "description": "",
            "apply_url": "",
            "job_url": "",
            "location": "India",
            "city": "",
            "state": "",
            "country": "IN",
            "is_remote": False,
            "is_hybrid": False,
            "role_category": "",
            "industry": "",
            "seniority": "mid",
            "employment_type": "full_time",
            "required_skills": [],
            "preferred_skills": [],
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "INR",
            "salary_raw": "",
            "experience_min_years": None,
            "experience_max_years": None,
            "posted_at": None,
            "source_name": self.SOURCE_NAME,
        }

    @abc.abstractmethod
    async def async_search(
        self,
        roles: List[str],
        locations: List[str],
        skills: List[str],
        max_results: int = 50,
        client: httpx.AsyncClient | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute the search and return a list of canonical raw-job dicts.

        Parameters
        ----------
        roles:       Job title / role queries (max 5 used)
        locations:   Target locations (max 3 used)
        skills:      Skills to bias the search (max 10 used)
        max_results: Cap on total results returned
        client:      Shared httpx.AsyncClient; create a local one if None

        Returns
        -------
        List of raw job dicts following CANONICAL_KEYS schema.
        """

    async def _get_client(
        self,
        client: httpx.AsyncClient | None,
        headers: Dict[str, str] | None = None,
    ) -> tuple[httpx.AsyncClient, bool]:
        """
        Returns (client, owned) where owned=True means caller must close it.
        """
        if client is not None:
            return client, False
        return httpx.AsyncClient(
            timeout=self.DEFAULT_TIMEOUT,
            headers=headers or {},
            follow_redirects=True,
        ), True
