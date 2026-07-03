"""
VidyaMarg AI — RemoteOK Connector
==================================
Scrapes the RemoteOK public JSON API (no authentication required).
Endpoint: https://remoteok.com/api

Response format:
  [
    { "legal": "..." },           ← index 0: metadata — skip
    { "id": "...", "slug": "...", "position": "...", ... },
    ...
  ]

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

logger = logging.getLogger("jd.connectors.remoteok")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_API_URL: str = "https://remoteok.com/api"
_HEALTH_TIMEOUT: float = 5.0
_HEADERS: Dict[str, str] = {
    "User-Agent": "VidyaMargAI-Agent/2.0 (+https://vidyamarg.ai)",
    "Accept": "application/json",
}


class RemoteOKConnector(BaseJobConnector):
    """
    Public RemoteOK API connector.

    No credentials required — the API is freely accessible.
    Returns up to ``config.max_results`` normalized RawJob objects.
    """

    # ------------------------------------------------------------------
    # Contract: authenticate
    # ------------------------------------------------------------------

    async def authenticate(self) -> bool:
        """RemoteOK requires no authentication. Always returns True."""
        return True

    # ------------------------------------------------------------------
    # Contract: health_check
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """
        Probe https://remoteok.com/api with a 5-second timeout.
        Returns True only when HTTP 200 is received.
        """
        try:
            async with httpx.AsyncClient(
                headers=_HEADERS,
                timeout=_HEALTH_TIMEOUT,
                follow_redirects=True,
            ) as client:
                response = await client.get(_API_URL)
                healthy = response.status_code == 200
                self.logger.info(
                    f"[health_check] status={response.status_code} healthy={healthy}"
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
        Fetches all jobs from the RemoteOK public API and filters them
        by the role keywords supplied in ``query_params['roles']``.

        Args:
            query_params: Expects an optional ``roles`` key containing a
                          list of keyword strings (case-insensitive).

        Returns:
            ConnectorResult with normalized RawJob objects.
        """
        start_ts = time.perf_counter()

        try:
            role_keywords: List[str] = [
                kw.lower()
                for kw in query_params.get("roles", [])
                if isinstance(kw, str)
            ]

            timeout = self.config.timeout_seconds or 30
            async with httpx.AsyncClient(
                headers=_HEADERS,
                timeout=float(timeout),
                follow_redirects=True,
            ) as client:
                self.logger.info(f"[discover_jobs] GET {_API_URL}")
                response = await client.get(_API_URL)
                response.raise_for_status()

            raw_list: List[Dict[str, Any]] = response.json()

            # The first element is always a metadata/legal object — skip it.
            job_entries: List[Dict[str, Any]] = [
                item
                for item in raw_list[1:]
                if isinstance(item, dict) and item.get("slug")
            ]

            self.logger.info(
                f"[discover_jobs] fetched {len(job_entries)} raw job entries"
            )

            jobs: List[RawJob] = []
            for raw in job_entries:
                if len(jobs) >= self.config.max_results:
                    break

                # Role keyword filtering — match against position, tags, or company
                if role_keywords and not self._matches_roles(raw, role_keywords):
                    continue

                normalized = self.normalize(raw)
                if normalized is not None:
                    jobs.append(normalized)

            latency_ms = int((time.perf_counter() - start_ts) * 1000)
            self.logger.info(
                f"[discover_jobs] returning {len(jobs)} jobs "
                f"(filtered from {len(job_entries)}) in {latency_ms}ms"
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
        Maps a single RemoteOK API job dict into a canonical RawJob.

        Fields mapped:
          - external_id  : MD5 of (connector_name + slug)
          - source_name  : 'remoteok'
          - title        : raw['position']
          - company_name : raw['company']
          - is_remote    : always True (RemoteOK is remote-only)
          - location     : 'Remote'
          - country      : 'GLOBAL'
          - required_skills: raw['tags'][:15]
          - salary_min   : raw['salary_min'] (parsed to float)
          - salary_max   : raw['salary_max'] (parsed to float)
          - apply_url    : raw['apply_url'] or constructed from slug
          - posted_at    : None (epoch from API is unreliable)
        """
        try:
            slug: str = str(raw_payload.get("slug", "") or "")
            position: str = str(raw_payload.get("position", "") or "").strip()
            company: str = str(raw_payload.get("company", "") or "").strip()

            if not slug or not position or not company:
                self.logger.debug(
                    f"[normalize] skipping incomplete entry: slug={slug!r}"
                )
                return None

            external_id = self.make_external_id(slug)

            # Skills — RemoteOK provides a list of tag strings
            raw_tags: Any = raw_payload.get("tags", [])
            tags: List[str] = (
                [str(t) for t in raw_tags if t]
                if isinstance(raw_tags, list)
                else []
            )

            # Apply URL
            apply_url: str = str(raw_payload.get("apply_url", "") or "")
            if not apply_url:
                apply_url = f"https://remoteok.com/remote-jobs/{slug}"

            # Job URL (same as apply for RemoteOK)
            job_url: str = str(raw_payload.get("url", "") or apply_url)

            return RawJob(
                external_id=external_id,
                source_name="remoteok",
                title=position,
                company_name=company,
                description=str(raw_payload.get("description", "") or ""),
                apply_url=apply_url,
                job_url=job_url,
                location="Remote",
                country="GLOBAL",
                is_remote=True,
                required_skills=tags[:15],
                salary_min=self.safe_float(raw_payload.get("salary_min")),
                salary_max=self.safe_float(raw_payload.get("salary_max")),
                salary_currency="USD",
                posted_at=None,
                raw_payload=raw_payload,
            )

        except Exception as exc:
            self.logger.error(
                f"[normalize] failed for slug={raw_payload.get('slug')!r}: {exc!r}",
                exc_info=True,
            )
            return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _matches_roles(
        self, raw: Dict[str, Any], role_keywords: List[str]
    ) -> bool:
        """
        Returns True if the job matches at least one role keyword.
        Checks the position title, company name, and tags.
        """
        position_lower = str(raw.get("position", "")).lower()
        company_lower = str(raw.get("company", "")).lower()
        tags_lower = " ".join(
            str(t) for t in (raw.get("tags") or [])
        ).lower()

        haystack = f"{position_lower} {company_lower} {tags_lower}"
        return any(kw in haystack for kw in role_keywords)
