"""
VidyaMarg AI — Indeed Job Connector
=====================================
Discovers jobs from Indeed's public job search pages.

URL pattern:
  https://www.indeed.com/jobs?q={query}&l={location}&sort=date

Design:
  - Sends browser-like headers to avoid basic bot detection
  - Parses HTML with BeautifulSoup, targeting jobsearch-ResultsList items
    that carry data-jk job-key attributes
  - 2-second polite delay between successive role requests
  - HTTP 403 is caught cleanly and returns success=False
  - All network I/O is async (httpx.AsyncClient)
  - All exceptions are caught; failures return ConnectorResult(success=False)

Note: Indeed uses Cloudflare and aggressive bot-detection in practice.
      This connector uses best-effort browser emulation; persistence in
      production should employ a rotating-proxy or Playwright layer.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlencode

import httpx
from bs4 import BeautifulSoup

from app.job_discovery.connectors.base import (
    BaseJobConnector,
    ConnectorConfig,
    ConnectorResult,
)
from app.job_discovery.domain.models import RawJob

logger = logging.getLogger("jd.connectors.indeed")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_URL = "https://www.indeed.com/jobs"
_VIEW_JOB_URL = "https://www.indeed.com/viewjob?jk={jk}"
_DELAY_BETWEEN_REQUESTS = 2.0  # seconds

# Browser-like headers to reduce detection likelihood
_BROWSER_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
    "Referer": "https://www.indeed.com/",
}


class IndeedConnector(BaseJobConnector):
    """
    Discovers jobs from Indeed public search pages.
    Parses job cards from jobsearch-ResultsList HTML.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)

    # ------------------------------------------------------------------
    # Contract: authenticate
    # ------------------------------------------------------------------

    async def authenticate(self) -> bool:
        """No authentication required for public Indeed search."""
        return True

    # ------------------------------------------------------------------
    # Contract: health_check
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """
        HEAD https://www.indeed.com — healthy if response status < 400.
        """
        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
            ) as client:
                resp = await client.head(
                    "https://www.indeed.com", headers=_BROWSER_HEADERS
                )
                healthy = resp.status_code < 400
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
        Iterates over the first 3 roles from query_params['roles'],
        fetches and parses Indeed search result pages, and returns
        up to config.max_results normalized RawJob objects.
        """
        t_start = time.perf_counter()
        jobs: List[RawJob] = []
        roles: List[str] = query_params.get("roles", ["software engineer"])[:3]
        location: str = query_params.get("location", "")

        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
                headers=_BROWSER_HEADERS,
            ) as client:
                for role in roles:
                    if len(jobs) >= self.config.max_results:
                        break

                    result = await self._fetch_search_page(client, role, location)

                    # Handle 403 gracefully
                    if result is None:
                        self.logger.warning(
                            f"Indeed blocked request for role='{role}'. "
                            "Returning partial results with success=False."
                        )
                        latency_ms = int((time.perf_counter() - t_start) * 1000)
                        return ConnectorResult(
                            connector_name=self.name,
                            jobs=jobs,
                            success=False,
                            error_message="Indeed returned 403 — access denied",
                            latency_ms=latency_ms,
                        )

                    raw_cards = self._parse_job_cards(result)
                    self.logger.debug(
                        f"role='{role}' → {len(raw_cards)} job cards parsed"
                    )

                    for raw in raw_cards:
                        raw_job = self.normalize(raw)
                        if raw_job:
                            jobs.append(raw_job)
                        if len(jobs) >= self.config.max_results:
                            break

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
        Maps a parsed Indeed job card dict to a canonical RawJob.

        external_id is based on the jk (job key) if present; otherwise
        derived from title + company.
        apply_url is the canonical Indeed view URL using the jk parameter.
        """
        try:
            jk: str = raw_payload.get("jk", "").strip()
            title: str = raw_payload.get("title", "").strip()
            company: str = raw_payload.get("company", "").strip()
            location: str = raw_payload.get("location", "").strip()
            raw_url: str = raw_payload.get("job_url", "").strip()

            if not title and not jk:
                return None

            # Prefer jk for stable deduplication
            id_basis = jk if jk else f"{title}{company}"
            external_id = self.make_external_id(id_basis)

            # Construct the canonical apply URL
            apply_url = (
                _VIEW_JOB_URL.format(jk=jk)
                if jk
                else raw_url
            )

            is_remote = "remote" in location.lower()

            return RawJob(
                external_id=external_id,
                source_name="indeed",
                title=title or "Unknown",
                company_name=company or "Unknown",
                description="",
                apply_url=apply_url,
                job_url=apply_url,
                location=location,
                country="US",
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

    async def _fetch_search_page(
        self,
        client: httpx.AsyncClient,
        role: str,
        location: str,
    ) -> Optional[str]:
        """
        Fetches a single Indeed search page.
        Returns HTML string on success, None on 403 (access denied),
        empty string on other non-200 responses.
        Raises on network errors (caught in discover_jobs).
        """
        params: Dict[str, str] = {
            "q": role,
            "sort": "date",
        }
        if location:
            params["l"] = location

        url = _BASE_URL
        try:
            resp = await client.get(url, params=params)
        except httpx.RequestError as req_err:
            self.logger.warning(f"Request error for role='{role}': {req_err}")
            raise

        if resp.status_code == 403:
            return None  # Signal access-denied to caller

        if resp.status_code != 200:
            self.logger.warning(
                f"Indeed returned HTTP {resp.status_code} for role='{role}'"
            )
            return ""  # Empty → parse yields nothing

        return resp.text

    def _parse_job_cards(self, html: str) -> List[Dict[str, Any]]:
        """
        Parses Indeed search results HTML.

        Targeting strategy (Indeed DOM as of 2024):
          Container: ul#mosaic-provider-jobcards or div.jobsearch-ResultsList
          Card: li[data-jk] elements (each has a unique job key)

          Fields extracted:
            jk       → data-jk attribute on the li element
            title    → .jobTitle a span text
            company  → .companyName text
            location → .companyLocation text
            job_url  → href on .jobTitle a or base card anchor
        """
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        results: List[Dict[str, Any]] = []

        # Strategy 1: li elements with data-jk attribute (most common)
        cards = soup.find_all("li", attrs={"data-jk": True})

        # Strategy 2: fall back to any li inside jobsearch-ResultsList
        if not cards:
            result_list = (
                soup.find("ul", id="mosaic-provider-jobcards")
                or soup.find("div", class_="jobsearch-ResultsList")
            )
            if result_list:
                cards = result_list.find_all("li", recursive=False)

        for card in cards:
            try:
                jk = card.get("data-jk", "")

                # Title — .jobTitle a span or just .jobTitle a text
                title_container = card.find(class_="jobTitle")
                title = ""
                job_url = ""
                if title_container:
                    link = title_container.find("a")
                    if link:
                        span = link.find("span")
                        title = span.get_text(strip=True) if span else link.get_text(strip=True)
                        href = link.get("href", "")
                        if href:
                            job_url = (
                                f"https://www.indeed.com{href}"
                                if href.startswith("/")
                                else href
                            )

                # Company
                company_tag = card.find(class_="companyName")
                company = company_tag.get_text(strip=True) if company_tag else ""

                # Location
                location_tag = card.find(class_="companyLocation")
                location = location_tag.get_text(strip=True) if location_tag else ""

                if title or jk:
                    results.append(
                        {
                            "jk": jk,
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
