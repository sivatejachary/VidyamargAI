"""
VidyaMarg AI — Wellfound (AngelList Talent) Job Connector
==========================================================
Discovers startup jobs from Wellfound's public job listing pages.

URL pattern:
  https://wellfound.com/jobs?role={role}&remote=true

Design:
  - Remote-first by default (Wellfound is predominantly a remote startup platform)
  - Scrapes HTML job listing elements (.job-listing, .styles_component__*)
    with multiple selector fallbacks to handle DOM variations
  - All network I/O is async (httpx.AsyncClient)
  - All exceptions are caught; failures return ConnectorResult(success=False)
  - country='GLOBAL' since Wellfound is international/remote-first

Note: Wellfound uses React SSR; many job details are rendered client-side.
      This connector captures data from the initial HTML payload only.
      For richer data a headless browser (Playwright) layer is recommended.
"""
from __future__ import annotations

import asyncio
import logging
import re
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

logger = logging.getLogger("jd.connectors.wellfound")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_URL = "https://wellfound.com/jobs"
_DELAY_BETWEEN_REQUESTS = 2.5  # seconds

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
    "Referer": "https://wellfound.com/",
}

# Role normalization map — maps common terms to Wellfound role slugs
_ROLE_SLUG_MAP: Dict[str, str] = {
    "software engineer": "software-engineer",
    "frontend engineer": "frontend-engineer",
    "backend engineer": "backend-engineer",
    "fullstack engineer": "full-stack-engineer",
    "full stack engineer": "full-stack-engineer",
    "data scientist": "data-scientist",
    "data engineer": "data-engineer",
    "ml engineer": "machine-learning-engineer",
    "machine learning engineer": "machine-learning-engineer",
    "devops engineer": "devops-engineer",
    "product manager": "product-manager",
    "product designer": "product-designer",
    "mobile engineer": "mobile-engineer",
    "ios engineer": "ios-engineer",
    "android engineer": "android-engineer",
}

# Salary extraction pattern
_RE_SALARY = re.compile(
    r"\$[\d,]+(?:k|K)?(?:\s*[-–]\s*\$[\d,]+(?:k|K)?)?(?:/(?:yr|year|mo|month))?",
    re.IGNORECASE,
)


class WellfoundConnector(BaseJobConnector):
    """
    Discovers startup jobs from Wellfound (formerly AngelList Talent) public pages.
    Defaults to remote=true for all searches (Wellfound's dominant use case).
    """

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)

    # ------------------------------------------------------------------
    # Contract: authenticate
    # ------------------------------------------------------------------

    async def authenticate(self) -> bool:
        """No authentication required for public Wellfound job listings."""
        return True

    # ------------------------------------------------------------------
    # Contract: health_check
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """
        HEAD https://wellfound.com — healthy if status < 400.
        """
        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
            ) as client:
                resp = await client.head(
                    "https://wellfound.com", headers=_BROWSER_HEADERS
                )
                healthy = resp.status_code < 400
                self.logger.debug(
                    f"health_check → HTTP {resp.status_code} | healthy={healthy}"
                )
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
        fetches Wellfound public job pages (remote=true), parses HTML,
        and returns up to config.max_results normalized RawJob objects.
        """
        t_start = time.perf_counter()
        jobs: List[RawJob] = []
        roles: List[str] = query_params.get("roles", ["software engineer"])[:3]

        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
                headers=_BROWSER_HEADERS,
            ) as client:
                for role in roles:
                    if len(jobs) >= self.config.max_results:
                        break

                    html = await self._fetch_jobs_page(client, role)

                    if html is None:
                        # Network error that should abort
                        self.logger.warning(
                            f"Failed to fetch Wellfound page for role='{role}'"
                        )
                        continue  # Try next role rather than aborting entirely

                    raw_listings = self._parse_listings(html)
                    self.logger.debug(
                        f"role='{role}' → {len(raw_listings)} listings parsed"
                    )

                    for raw in raw_listings:
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
        Maps a parsed Wellfound listing dict to a canonical RawJob.

        Wellfound is remote-first, so is_remote=True by default unless an
        explicit non-remote location is found.  country='GLOBAL' since
        most Wellfound roles are international / distributed.
        """
        try:
            title: str = raw_payload.get("title", "").strip()
            company: str = raw_payload.get("company", "").strip()
            location: str = raw_payload.get("location", "").strip()
            salary_raw: str = raw_payload.get("salary_raw", "").strip()
            skills: List[str] = raw_payload.get("skills", [])
            job_url: str = raw_payload.get("job_url", "").strip()
            description: str = raw_payload.get("description", "").strip()

            if not title and not company:
                return None

            external_id = self.make_external_id(title, company)

            # Wellfound is remote-first; mark non-remote only if location
            # explicitly indicates onsite (e.g. "New York, NY" without "remote")
            is_remote: bool = True
            normalized_location = location
            if location:
                is_remote = (
                    "remote" in location.lower()
                    or not any(
                        c.isalpha() and c.isupper()
                        for c in location  # city/state markers
                    )
                )
            normalized_location = "Remote" if is_remote else location

            if not skills:
                skills = self.extract_skills(f"{title} {description}")

            return RawJob(
                external_id=external_id,
                source_name="wellfound",
                title=title or "Unknown",
                company_name=company or "Unknown",
                description=description,
                apply_url=job_url,
                job_url=job_url,
                location=normalized_location,
                country="GLOBAL",
                is_remote=is_remote,
                salary_raw=salary_raw,
                required_skills=skills,
                raw_payload=raw_payload,
            )
        except Exception as exc:
            self.logger.warning(f"normalize() failed: {exc} | payload={raw_payload}")
            return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_jobs_page(
        self, client: httpx.AsyncClient, role: str
    ) -> Optional[str]:
        """
        Fetches the Wellfound jobs page for a given role (remote=true).
        Returns HTML string, or None on error.
        """
        # Map to Wellfound role slug if known, else slugify manually
        role_slug = _ROLE_SLUG_MAP.get(
            role.lower(),
            role.lower().replace(" ", "-"),
        )
        params = {
            "role": role_slug,
            "remote": "true",
        }
        try:
            resp = await client.get(_BASE_URL, params=params)
            if resp.status_code >= 400:
                self.logger.warning(
                    f"Wellfound HTTP {resp.status_code} for role='{role}'"
                )
                return None
            return resp.text
        except httpx.RequestError as req_err:
            self.logger.warning(f"Request error for role='{role}': {req_err}")
            return None
        except Exception as exc:
            self.logger.warning(f"Unexpected error fetching Wellfound page: {exc}")
            return None

    def _parse_listings(self, html: str) -> List[Dict[str, Any]]:
        """
        Parses Wellfound HTML for job listings.

        Wellfound's SSR output includes job listing elements that may appear
        under various class patterns depending on their frontend version.
        This parser tries multiple selector strategies in order:

        Strategy 1: div.job-listing (legacy class)
        Strategy 2: div[class*="styles_component"] (modern CSS-modules class)
        Strategy 3: any a[href*="/jobs/"] anchor within the main content area

        From each card, we attempt to extract:
          title    → h2 or .job-name or first heading
          company  → .company-name or parent startup link text
          location → .location or text containing city/remote
          salary   → text matching $xxx salary pattern
          skills   → comma/slash separated tech keywords in description
          job_url  → href of the job link
        """
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        results: List[Dict[str, Any]] = []

        # Strategy 1: .job-listing divs
        cards = soup.find_all("div", class_="job-listing")

        # Strategy 2: CSS-module styled divs (Wellfound uses css-modules)
        if not cards:
            cards = [
                el
                for el in soup.find_all("div")
                if el.get("class")
                and any("styles_component" in c for c in el.get("class", []))
                and el.find("a", href=lambda h: h and "/jobs/" in h)
            ]

        # Strategy 3: Flat link scan inside main content
        if not cards:
            main = soup.find("main") or soup.find("div", id="content") or soup
            job_links = [
                a
                for a in main.find_all("a", href=True)
                if "/jobs/" in a["href"] and a.get_text(strip=True)
            ]
            for link in job_links:
                title = link.get_text(strip=True)
                job_url = link["href"]
                if not job_url.startswith("http"):
                    job_url = f"https://wellfound.com{job_url}"
                if title:
                    results.append({
                        "title": title,
                        "company": "",
                        "location": "Remote",
                        "salary_raw": "",
                        "skills": [],
                        "job_url": job_url,
                        "description": "",
                    })
            return results

        for card in cards:
            try:
                # Title
                title_tag = (
                    card.find("h2")
                    or card.find(class_=re.compile(r"job.?name|title", re.I))
                    or card.find("h3")
                )
                title = title_tag.get_text(strip=True) if title_tag else ""

                # Company
                company_tag = card.find(class_=re.compile(r"company.?name|startup", re.I))
                company = company_tag.get_text(strip=True) if company_tag else ""

                # Location
                location_tag = card.find(class_=re.compile(r"location|remote", re.I))
                location = location_tag.get_text(strip=True) if location_tag else "Remote"

                # Salary
                card_text = card.get_text(" ", strip=True)
                salary_match = _RE_SALARY.search(card_text)
                salary_raw = salary_match.group(0) if salary_match else ""

                # Skills — look in description or tag lists
                skill_tags = card.find_all(class_=re.compile(r"tag|skill|tech|badge", re.I))
                skills: List[str] = [
                    t.get_text(strip=True)
                    for t in skill_tags
                    if t.get_text(strip=True)
                ]
                if not skills:
                    skills = self.extract_skills(card_text)

                # Job URL
                link_tag = card.find("a", href=lambda h: h and "/jobs/" in str(h))
                job_url = ""
                if link_tag:
                    href = link_tag.get("href", "")
                    job_url = (
                        href
                        if href.startswith("http")
                        else f"https://wellfound.com{href}"
                    )

                # Description (limited — usually not in preview cards)
                desc_tag = card.find(class_=re.compile(r"desc|summary|snippet", re.I))
                description = desc_tag.get_text(strip=True) if desc_tag else ""

                if title or company:
                    results.append(
                        {
                            "title": title,
                            "company": company,
                            "location": location,
                            "salary_raw": salary_raw,
                            "skills": skills,
                            "job_url": job_url,
                            "description": description,
                        }
                    )
            except Exception as parse_exc:
                self.logger.debug(f"Listing parse error: {parse_exc}")
                continue

        return results
