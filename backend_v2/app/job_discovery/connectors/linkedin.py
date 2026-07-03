"""
VidyaMarg AI — LinkedIn Job Connector
======================================
Discovers jobs through LinkedIn's public guest job search endpoint:
  https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search

No login or OAuth is required for basic job discovery.

Design:
  - Paginates in steps of 25 (start=0, 25, 50) for each role keyword
  - 3-second polite delay between every paginated request
  - 429 / 403 responses cause the connector to return success=False cleanly
  - All network I/O is async (httpx.AsyncClient)
  - All exceptions are caught; failures return ConnectorResult(success=False)

Note: LinkedIn aggressively rate-limits scrapers.  This connector adds
conservative delays and honours HTTP 429 by aborting early rather than
retrying (to avoid IP bans).
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from app.job_discovery.connectors.base import (
    BaseJobConnector,
    ConnectorConfig,
    ConnectorResult,
)
from app.job_discovery.domain.models import RawJob

logger = logging.getLogger("jd.connectors.linkedin")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GUEST_SEARCH_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
)
_PAGES = [0, 25, 50]  # pagination offsets
_DELAY_BETWEEN_REQUESTS = 3.0  # seconds — conservative to avoid 429


class LinkedInConnector(BaseJobConnector):
    """
    Discovers jobs from LinkedIn via the public guest job-search endpoint.
    Uses BeautifulSoup to parse li.base-card HTML fragments returned by the API.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._headers: Dict[str, str] = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.linkedin.com/jobs/",
        }

    # ------------------------------------------------------------------
    # Contract: authenticate
    # ------------------------------------------------------------------

    async def authenticate(self) -> bool:
        """No authentication required for public job search endpoint."""
        return True

    # ------------------------------------------------------------------
    # Contract: health_check
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """
        HEAD https://www.linkedin.com — healthy if not 403/5xx.
        LinkedIn typically returns 200 or a redirect.
        """
        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
            ) as client:
                resp = await client.head(
                    "https://www.linkedin.com", headers=self._headers
                )
                healthy = resp.status_code not in (403, 429, 503)
                self.logger.debug(f"health_check → HTTP {resp.status_code} | healthy={healthy}")
                return healthy
        except Exception as exc:
            self.logger.warning(f"health_check failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Contract: discover_jobs
    # ------------------------------------------------------------------

    async def discover_jobs(self, query_params: Dict[str, Any]) -> ConnectorResult:
        """
        Iterates over the first 3 roles from query_params['roles'], paginates
        through 3 pages per role, parses HTML for base-card job entries, and
        returns up to config.max_results normalized RawJob objects.
        """
        t_start = time.perf_counter()
        jobs: List[RawJob] = []
        roles: List[str] = query_params.get("roles", ["software engineer"])[:3]
        location: str = query_params.get("location", "India")

        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
                headers=self._headers,
            ) as client:
                for role in roles:
                    if len(jobs) >= self.config.max_results:
                        break

                    for start in _PAGES:
                        if len(jobs) >= self.config.max_results:
                            break

                        result = await self._fetch_page(client, role, location, start)

                        # Abort on rate-limit / access-denied
                        if result is None:
                            self.logger.warning(
                                f"Rate-limited or blocked for role='{role}', start={start}. "
                                "Aborting early."
                            )
                            latency_ms = int((time.perf_counter() - t_start) * 1000)
                            return ConnectorResult(
                                connector_name=self.name,
                                jobs=jobs,
                                success=False,
                                error_message="LinkedIn returned 429/403 — rate limited",
                                latency_ms=latency_ms,
                            )

                        page_jobs = self._parse_cards(result)
                        self.logger.debug(
                            f"role='{role}' start={start} → {len(page_jobs)} cards"
                        )

                        for raw in page_jobs:
                            raw_job = self.normalize(raw)
                            if raw_job:
                                jobs.append(raw_job)
                            if len(jobs) >= self.config.max_results:
                                break

                        # Early exit if page returned no results (no more pages)
                        if not page_jobs:
                            break

                        # Polite delay between requests
                        await asyncio.sleep(_DELAY_BETWEEN_REQUESTS)

            jobs = jobs[: self.config.max_results]
            latency_ms = int((time.perf_counter() - t_start) * 1000)
            self.logger.info(
                f"discover_jobs complete: {len(jobs)} jobs in {latency_ms}ms"
            )
            return ConnectorResult(
                connector_name=self.name,
                jobs=jobs,
                success=True,
                latency_ms=latency_ms,
            )

        except Exception as exc:
            latency_ms = int((time.perf_counter() - t_start) * 1000)
            self.logger.error(f"discover_jobs fatal error: {exc}", exc_info=True)
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
        Maps a parsed LinkedIn card dict to a canonical RawJob.
        external_id is derived from the job URL when available, else title+company.
        """
        try:
            title: str = raw_payload.get("title", "").strip()
            company: str = raw_payload.get("company", "").strip()
            location: str = raw_payload.get("location", "").strip()
            job_url: str = raw_payload.get("job_url", "").strip()

            if not title and not job_url:
                return None

            # Use URL as the most stable identifier; fall back to title+company
            id_basis = job_url if job_url else f"{title}{company}"
            external_id = self.make_external_id(id_basis)

            is_remote = "remote" in location.lower()

            return RawJob(
                external_id=external_id,
                source_name="linkedin",
                title=title or "Unknown",
                company_name=company or "Unknown",
                description="",
                apply_url=job_url,
                job_url=job_url,
                location=location,
                country="IN",
                is_remote=is_remote,
                salary_raw="",
                required_skills=self.extract_skills(title),
                raw_payload=raw_payload,
            )
        except Exception as exc:
            self.logger.warning(f"normalize() failed: {exc} | payload={raw_payload}")
            return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        role: str,
        location: str,
        start: int,
    ) -> Optional[str]:
        """
        Fetches one page from the LinkedIn guest search API.
        Returns the HTML body on success, None on 429/403.
        Raises on other errors (caught in discover_jobs).
        """
        params = {
            "keywords": role,
            "location": location,
            "start": str(start),
            "f_JT": "F",           # Full-time filter
            "sortBy": "DD",        # Date descending
        }
        url = _GUEST_SEARCH_URL
        try:
            resp = await client.get(url, params=params)
        except httpx.RequestError as req_err:
            self.logger.warning(f"Request error for role='{role}' start={start}: {req_err}")
            raise

        if resp.status_code in (429, 403):
            return None  # Signal rate-limit to caller

        if resp.status_code != 200:
            self.logger.warning(
                f"Unexpected HTTP {resp.status_code} for role='{role}' start={start}"
            )
            return ""  # Return empty string → parse will yield nothing

        return resp.text

    def _parse_cards(self, html: str) -> List[Dict[str, Any]]:
        """
        Parses LinkedIn guest search HTML.
        Targets li.base-card elements (job cards).

        Field selectors:
          title   → .job-search-card__title
          company → .hidden-nested-link or .job-search-card__company-name
          location→ .job-search-card__location
          url     → a.base-card__full-link[href]
        """
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("li", class_="base-card")
        results: List[Dict[str, Any]] = []

        for card in cards:
            try:
                # Title
                title_tag = card.find(class_="job-search-card__title")
                title = title_tag.get_text(strip=True) if title_tag else ""

                # Company — prefer hidden-nested-link (more precise), fallback to text
                company_tag = (
                    card.find(class_="hidden-nested-link")
                    or card.find(class_="job-search-card__company-name")
                )
                company = company_tag.get_text(strip=True) if company_tag else ""

                # Location
                location_tag = card.find(class_="job-search-card__location")
                location = location_tag.get_text(strip=True) if location_tag else ""

                # Job URL
                link_tag = card.find("a", class_="base-card__full-link")
                if link_tag is None:
                    link_tag = card.find("a", href=True)
                job_url = link_tag["href"].split("?")[0] if link_tag else ""

                if title or job_url:
                    results.append(
                        {
                            "title": title,
                            "company": company,
                            "location": location,
                            "job_url": job_url,
                        }
                    )
            except Exception as parse_exc:
                self.logger.debug(f"Card parse error: {parse_exc}")
                continue

        return results
