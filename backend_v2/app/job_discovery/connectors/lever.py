"""
VidyaMarg AI — Lever Connector
================================
Reads from the Lever public job posting API (no credentials required).
Fetches postings across a curated list of known companies.

Company endpoint: GET https://api.lever.co/v0/postings/{company}?mode=json

Response shape (mode=json):
  [
    {
      "id": "uuid",
      "text": "Software Engineer",
      "hostedUrl": "https://jobs.lever.co/...",
      "categories": {
        "location": "Remote",
        "team": "Engineering",
        "commitment": "Full-time"
      },
      "descriptionPlain": "...",
      "lists": [ { "text": "Responsibilities", "content": "..." }, ... ],
      "additional": "...",
      ...
    },
    ...
  ]

All network I/O is async (httpx.AsyncClient).
Any failure returns ConnectorResult(success=False) — never raises.
"""
from __future__ import annotations

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

logger = logging.getLogger("jd.connectors.lever")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_API_BASE: str = "https://api.lever.co/v0/postings"
_HEALTH_COMPANY: str = "netflix"
_HEALTH_TIMEOUT: float = 10.0
_HEADERS: Dict[str, str] = {
    "User-Agent": "VidyaMargAI-Agent/2.0 (+https://vidyamarg.ai)",
    "Accept": "application/json",
}

# Well-known companies that use Lever and expose public postings.
KNOWN_COMPANIES: List[str] = [
    "netflix",
    "coinbase",
    "instacart",
    "duolingo",
    "canva",
    "airtable",
    "brex",
    "scale-ai",
    "anthropic",
    "cohere",
]


class LeverConnector(BaseJobConnector):
    """
    Public Lever job posting API connector.

    Iterates over ``KNOWN_COMPANIES`` and collects job postings up to
    ``config.max_results``. Role keyword filtering is applied per posting.
    """

    # ------------------------------------------------------------------
    # Contract: authenticate
    # ------------------------------------------------------------------

    async def authenticate(self) -> bool:
        """Lever public API requires no authentication. Always True."""
        return True

    # ------------------------------------------------------------------
    # Contract: health_check
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """
        Probes the Netflix postings endpoint as a liveness check.
        Returns True if HTTP 200 is received within the timeout.
        """
        url = f"{_API_BASE}/{_HEALTH_COMPANY}"
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
        Iterates over all known Lever companies and collects filtered jobs.

        Args:
            query_params: Expects an optional ``roles`` key with a list of
                          keyword strings (case-insensitive).

        Returns:
            ConnectorResult aggregating postings from all companies.
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
                for company_slug in KNOWN_COMPANIES:
                    if len(jobs) >= self.config.max_results:
                        break
                    await self._fetch_company(
                        client=client,
                        company_slug=company_slug,
                        role_keywords=role_keywords,
                        jobs=jobs,
                    )

            latency_ms = int((time.perf_counter() - start_ts) * 1000)
            self.logger.info(
                f"[discover_jobs] collected {len(jobs)} jobs across "
                f"{len(KNOWN_COMPANIES)} companies in {latency_ms}ms"
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
        Maps a single Lever posting dict into a canonical RawJob.

        The ``raw_payload`` must contain a special ``_company_slug`` key
        injected by ``_fetch_company`` so we can derive the company name.

        Fields mapped:
          - external_id   : MD5 of (connector_name + raw['id'])
          - source_name   : 'lever'
          - title         : raw['text']
          - company_name  : company slug in title-case
          - description   : raw['descriptionPlain'] or assembled from
                            raw['lists'] + raw['additional']
          - apply_url     : raw.get('hostedUrl', '')
          - location      : raw['categories'].get('location', 'Remote')
          - is_remote     : True if 'remote' in location.lower()
          - team          : raw['categories'].get('team', '')
          - required_skills: heuristic extraction from description
        """
        try:
            posting_id: str = str(raw_payload.get("id", "") or "").strip()
            title: str = str(raw_payload.get("text", "") or "").strip()
            company_slug: str = str(raw_payload.get("_company_slug", "") or "")

            if not posting_id or not title:
                self.logger.debug(
                    "[normalize] skipping entry with missing id or text"
                )
                return None

            external_id = self.make_external_id(posting_id)

            company_name: str = (
                company_slug.replace("-", " ").title()
                if company_slug
                else "Unknown"
            )

            # Build description from available text sources
            description: str = self._build_description(raw_payload)

            apply_url: str = str(raw_payload.get("hostedUrl", "") or "")

            # Categories
            categories: Dict[str, Any] = raw_payload.get("categories") or {}
            location: str = str(categories.get("location", "") or "Remote")
            team: str = str(categories.get("team", "") or "")

            is_remote: bool = "remote" in location.lower()
            required_skills: List[str] = self.extract_skills(description)

            return RawJob(
                external_id=external_id,
                source_name="lever",
                title=title,
                company_name=company_name,
                description=description,
                apply_url=apply_url,
                job_url=apply_url,
                location=location,
                is_remote=is_remote,
                required_skills=required_skills,
                raw_payload={
                    k: v
                    for k, v in raw_payload.items()
                    if k != "_company_slug"
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

    async def _fetch_company(
        self,
        client: httpx.AsyncClient,
        company_slug: str,
        role_keywords: List[str],
        jobs: List[RawJob],
    ) -> None:
        """
        Fetches all postings for a single Lever company and appends
        matching, normalized results to ``jobs`` (in-place).
        Failures are logged and silently skipped.
        """
        url = f"{_API_BASE}/{company_slug}"
        params = {"mode": "json"}

        try:
            self.logger.info(f"[_fetch_company] GET {url}")
            response = await client.get(url, params=params)

            if response.status_code == 404:
                self.logger.warning(
                    f"[_fetch_company] company '{company_slug}' returned 404 — skipping"
                )
                return

            response.raise_for_status()

            raw_list: List[Dict[str, Any]] = response.json()

            if not isinstance(raw_list, list):
                self.logger.warning(
                    f"[_fetch_company] unexpected response shape for "
                    f"company={company_slug!r}: {type(raw_list)}"
                )
                return

            self.logger.info(
                f"[_fetch_company] company={company_slug!r} "
                f"fetched {len(raw_list)} raw postings"
            )

            for raw in raw_list:
                if len(jobs) >= self.config.max_results:
                    break

                if not isinstance(raw, dict):
                    continue

                # Inject company slug so normalize() can derive company name
                raw["_company_slug"] = company_slug

                if role_keywords and not self._matches_roles(raw, role_keywords):
                    continue

                normalized = self.normalize(raw)
                if normalized is not None:
                    jobs.append(normalized)

        except httpx.HTTPStatusError as exc:
            self.logger.error(
                f"[_fetch_company] HTTP error for company={company_slug!r}: "
                f"{exc.response.status_code} {exc!r}"
            )
        except Exception as exc:
            self.logger.error(
                f"[_fetch_company] unexpected error for company={company_slug!r}: {exc!r}",
                exc_info=True,
            )

    def _build_description(self, raw: Dict[str, Any]) -> str:
        """
        Assembles the job description from available text sources in order:
          1. descriptionPlain (preferred — already plain text)
          2. lists  (array of { text: heading, content: html })
          3. additional
        Returns a combined plain-text string.
        """
        # Prefer plain description
        plain: str = str(raw.get("descriptionPlain", "") or "").strip()
        if plain:
            return plain

        parts: List[str] = []

        # Assemble from structured lists
        raw_lists: Any = raw.get("lists")
        if isinstance(raw_lists, list):
            for item in raw_lists:
                if not isinstance(item, dict):
                    continue
                heading = str(item.get("text", "") or "").strip()
                content = str(item.get("content", "") or "").strip()
                if heading:
                    parts.append(heading)
                if content:
                    parts.append(content)

        # Append additional freeform block
        additional: str = str(raw.get("additional", "") or "").strip()
        if additional:
            parts.append(additional)

        return "\n\n".join(parts)

    def _matches_roles(
        self, raw: Dict[str, Any], role_keywords: List[str]
    ) -> bool:
        """
        Returns True if the posting title, team, or description matches
        at least one role keyword.
        """
        title_lower = str(raw.get("text", "")).lower()
        categories: Dict[str, Any] = raw.get("categories") or {}
        team_lower = str(categories.get("team", "")).lower()
        desc_lower = str(raw.get("descriptionPlain", "")).lower()[:2000]
        haystack = f"{title_lower} {team_lower} {desc_lower}"
        return any(kw in haystack for kw in role_keywords)
