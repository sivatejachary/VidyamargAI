"""
VidyaMarg AI — Greenhouse Connector
=====================================
Reads from the Greenhouse public job board API (no credentials required).
Fetches jobs across a curated list of known boards.

Board endpoint: GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true

Response shape:
  {
    "jobs": [
      {
        "id": 12345,
        "title": "...",
        "absolute_url": "...",
        "location": { "name": "..." },
        "content": "...",   ← HTML job description (present when ?content=true)
        ...
      },
      ...
    ],
    "meta": { "total": 42 }
  }

All network I/O is async (httpx.AsyncClient).
Any failure returns ConnectorResult(success=False) — never raises.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.job_discovery.connectors.base import (
    BaseJobConnector,
    ConnectorConfig,
    ConnectorResult,
)
from app.job_discovery.domain.models import RawJob

logger = logging.getLogger("jd.connectors.greenhouse")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_API_BASE: str = "https://boards-api.greenhouse.io/v1/boards"
_HEALTH_BOARD: str = "stripe"
_HEALTH_TIMEOUT: float = 10.0
_HEADERS: Dict[str, str] = {
    "User-Agent": "VidyaMargAI-Agent/2.0 (+https://vidyamarg.ai)",
    "Accept": "application/json",
}

# Well-known public Greenhouse boards with active job postings.
KNOWN_BOARDS: List[str] = [
    "stripe",
    "airbnb",
    "notion",
    "figma",
    "vercel",
    "hashicorp",
    "gitlab",
    "cockroachdb",
    "planetscale",
    "supabase",
]


class GreenhouseConnector(BaseJobConnector):
    """
    Public Greenhouse board API connector.

    Iterates over ``KNOWN_BOARDS`` and collects job postings up to
    ``config.max_results``. Role keyword filtering is applied per job.
    """

    # ------------------------------------------------------------------
    # Contract: authenticate
    # ------------------------------------------------------------------

    async def authenticate(self) -> bool:
        """Greenhouse public boards require no authentication. Always True."""
        return True

    # ------------------------------------------------------------------
    # Contract: health_check
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """
        Probes the Stripe board endpoint as a liveness check.
        Returns True if HTTP 200 is received within the timeout.
        """
        url = f"{_API_BASE}/{_HEALTH_BOARD}/jobs"
        try:
            async with httpx.AsyncClient(
                headers=_HEADERS,
                timeout=_HEALTH_TIMEOUT,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
                healthy = response.status_code == 200
                self.logger.info(
                    f"[health_check] GET {url} → {response.status_code} healthy={healthy}"
                )
                return healthy
        except Exception as exc:
            self.logger.warning(f"[health_check] failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Contract: discover_jobs
    # ------------------------------------------------------------------

    async def discover_jobs(
        self, query_params: Dict[str, Any]
    ) -> ConnectorResult:
        """
        Iterates over all known Greenhouse boards and collects filtered jobs.

        Args:
            query_params: Expects an optional ``roles`` key with a list of
                          keyword strings (case-insensitive).

        Returns:
            ConnectorResult aggregating jobs from all boards.
        """
        start_ts = time.perf_counter()

        try:
            role_keywords: List[str] = [
                kw.lower()
                for kw in query_params.get("roles", [])
                if isinstance(kw, str)
            ]

            timeout = float(self.config.timeout_seconds or 30)
            jobs: List[RawJob] = []

            async with httpx.AsyncClient(
                headers=_HEADERS,
                timeout=timeout,
                follow_redirects=True,
            ) as client:
                for board_slug in KNOWN_BOARDS:
                    if len(jobs) >= self.config.max_results:
                        break
                    await self._fetch_board(
                        client=client,
                        board_slug=board_slug,
                        role_keywords=role_keywords,
                        jobs=jobs,
                    )

            latency_ms = int((time.perf_counter() - start_ts) * 1000)
            self.logger.info(
                f"[discover_jobs] collected {len(jobs)} jobs across "
                f"{len(KNOWN_BOARDS)} boards in {latency_ms}ms"
            )

            return ConnectorResult(
                connector_name=self.name,
                jobs=jobs,
                success=True,
                latency_ms=latency_ms,
            )

        except Exception as exc:
            latency_ms = int((time.perf_counter() - start_ts) * 1000)
            self.logger.error(
                f"[discover_jobs] unhandled exception: {exc!r}",
                exc_info=True,
            )
            return ConnectorResult(
                connector_name=self.name,
                jobs=[],
                success=False,
                error_message=str(exc),
                latency_ms=latency_ms,
            )

    # ------------------------------------------------------------------
    # Contract: normalize
    # ------------------------------------------------------------------

    def normalize(self, raw_payload: Dict[str, Any]) -> Optional[RawJob]:
        """
        Maps a single Greenhouse job dict into a canonical RawJob.

        The ``raw_payload`` must contain a special ``_board_slug`` key
        injected by ``_fetch_board`` so we can derive the company name.

        Fields mapped:
          - external_id  : MD5 of (connector_name + str(raw['id']))
          - source_name  : 'greenhouse'
          - title        : raw['title']
          - company_name : board slug in title-case (e.g. 'stripe' → 'Stripe')
          - description  : raw.get('content', '')
          - apply_url    : raw.get('absolute_url', '')
          - location     : raw['location']['name'] if present
          - is_remote    : True if 'remote' appears anywhere in the location
          - required_skills: heuristic extraction from description
        """
        try:
            job_id: Any = raw_payload.get("id")
            title: str = str(raw_payload.get("title", "") or "").strip()
            board_slug: str = str(raw_payload.get("_board_slug", "") or "")

            if not job_id or not title:
                self.logger.debug(
                    f"[normalize] skipping entry with missing id or title"
                )
                return None

            external_id = self.make_external_id(str(job_id))

            company_name: str = board_slug.replace("-", " ").title() if board_slug else "Unknown"

            description: str = str(raw_payload.get("content", "") or "")
            apply_url: str = str(raw_payload.get("absolute_url", "") or "")

            # Location
            location_obj: Any = raw_payload.get("location")
            if isinstance(location_obj, dict):
                location: str = str(location_obj.get("name", "") or "")
            else:
                location = ""

            is_remote: bool = "remote" in location.lower()

            required_skills: List[str] = self.extract_skills(description)

            return RawJob(
                external_id=external_id,
                source_name="greenhouse",
                title=title,
                company_name=company_name,
                description=description,
                apply_url=apply_url,
                job_url=apply_url,
                location=location,
                is_remote=is_remote,
                required_skills=required_skills,
                raw_payload={
                    k: v for k, v in raw_payload.items() if k != "_board_slug"
                },
            )

        except Exception as exc:
            self.logger.error(
                f"[normalize] failed for id={raw_payload.get('id')!r}: {exc!r}",
                exc_info=True,
            )
            return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_board(
        self,
        client: httpx.AsyncClient,
        board_slug: str,
        role_keywords: List[str],
        jobs: List[RawJob],
    ) -> None:
        """
        Fetches all jobs for a single Greenhouse board and appends
        matching, normalized results to ``jobs`` (in-place).
        Failures are logged and silently skipped.
        """
        url = f"{_API_BASE}/{board_slug}/jobs"
        params = {"content": "true"}

        try:
            self.logger.info(f"[_fetch_board] GET {url}")
            response = await client.get(url, params=params)

            if response.status_code == 404:
                self.logger.warning(
                    f"[_fetch_board] board '{board_slug}' returned 404 — skipping"
                )
                return

            response.raise_for_status()

            data: Dict[str, Any] = response.json()
            raw_jobs: List[Dict[str, Any]] = data.get("jobs", [])

            self.logger.info(
                f"[_fetch_board] board={board_slug!r} fetched {len(raw_jobs)} raw jobs"
            )

            for raw in raw_jobs:
                if len(jobs) >= self.config.max_results:
                    break

                if not isinstance(raw, dict):
                    continue

                # Inject board slug so normalize() can derive company name
                raw["_board_slug"] = board_slug

                if role_keywords and not self._matches_roles(raw, role_keywords):
                    continue

                normalized = self.normalize(raw)
                if normalized is not None:
                    jobs.append(normalized)

        except httpx.HTTPStatusError as exc:
            self.logger.error(
                f"[_fetch_board] HTTP error for board={board_slug!r}: "
                f"{exc.response.status_code} {exc!r}"
            )
        except Exception as exc:
            self.logger.error(
                f"[_fetch_board] unexpected error for board={board_slug!r}: {exc!r}",
                exc_info=True,
            )

    def _matches_roles(
        self, raw: Dict[str, Any], role_keywords: List[str]
    ) -> bool:
        """
        Returns True if the job title or description matches at least one keyword.
        """
        title_lower = str(raw.get("title", "")).lower()
        content_lower = str(raw.get("content", "")).lower()[:2000]  # cap for speed
        haystack = f"{title_lower} {content_lower}"
        return any(kw in haystack for kw in role_keywords)
