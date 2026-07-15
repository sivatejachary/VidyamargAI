"""
LinkedIn Job Connector — Async Guest Search.
=============================================
Discovers jobs through LinkedIn's public guest job search endpoint:
  https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search

No login or OAuth is required.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from app.job_discovery.connectors.base import BaseConnector

logger = logging.getLogger("app.job_discovery.connectors.linkedin")

_GUEST_SEARCH_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
)
_PAGES = [0, 25, 50]  # pagination offsets
_DELAY_BETWEEN_REQUESTS = 3.0  # seconds — conservative to avoid 429


class LinkedInConnector(BaseConnector):
    """
    Async connector for LinkedIn public guest job search.
    Uses BeautifulSoup to parse li.base-card HTML fragments returned by the API.
    """

    SOURCE_NAME = "linkedin"
    DEFAULT_TIMEOUT = 20.0

    def __init__(self) -> None:
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

    async def async_search(
        self,
        roles: List[str],
        locations: List[str],
        skills: List[str],
        max_results: int = 50,
        client: httpx.AsyncClient | None = None,
    ) -> List[Dict[str, Any]]:
        owned_client, owns = await self._get_client(client, headers=self._headers)
        jobs: List[Dict[str, Any]] = []
        target_roles = roles[:3]
        target_location = locations[0] if locations else "India"

        try:
            for role in target_roles:
                if len(jobs) >= max_results:
                    break

                for start in _PAGES:
                    if len(jobs) >= max_results:
                        break

                    page_html = await self._fetch_page(owned_client, role, target_location, start)
                    if page_html is None:
                        logger.warning(
                            f"[LinkedIn] Rate limited or blocked for role='{role}', start={start}. "
                            "Aborting this role's search."
                        )
                        break  # Stop this role's pagination loop

                    page_jobs = self._parse_cards(page_html)
                    logger.debug(
                        f"[LinkedIn] role='{role}' start={start} → found {len(page_jobs)} cards"
                    )

                    for raw in page_jobs:
                        ext_id = hashlib.md5(
                            f"linkedin:{raw['job_url'] or raw['title'] + raw['company']}".encode()
                        ).hexdigest()

                        job = self._build_empty_job()
                        job.update({
                            "external_id": ext_id,
                            "title": raw["title"],
                            "company_name": raw["company"],
                            "location": raw["location"],
                            "apply_url": raw["job_url"],
                            "job_url": raw["job_url"],
                            "is_remote": "remote" in raw["location"].lower(),
                            "source_name": self.SOURCE_NAME,
                        })
                        jobs.append(job)

                        if len(jobs) >= max_results:
                            break

                    if not page_jobs:
                        break  # No more results on this page

                    await asyncio.sleep(_DELAY_BETWEEN_REQUESTS)

            return jobs
        except Exception as exc:
            logger.error(f"[LinkedIn] Search failed: {exc}")
            return []
        finally:
            if owns:
                await owned_client.aclose()

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        role: str,
        location: str,
        start: int,
    ) -> Optional[str]:
        params = {
            "keywords": role,
            "location": location,
            "start": str(start),
            "f_JT": "F",           # Full-time filter
            "sortBy": "DD",        # Date descending
        }
        try:
            resp = await client.get(_GUEST_SEARCH_URL, params=params)
            if resp.status_code in (429, 403):
                return None
            if resp.status_code != 200:
                logger.warning(
                    f"[LinkedIn] Unexpected HTTP {resp.status_code} for role='{role}' start={start}"
                )
                return ""
            return resp.text
        except Exception as exc:
            logger.warning(f"[LinkedIn] Page request failed for role='{role}' start={start}: {exc}")
            return ""

    def _parse_cards(self, html: str) -> List[Dict[str, Any]]:
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all(class_=lambda x: x and ("base-card" in x or "job-search-card" in x or "base-search-card" in x))
        results: List[Dict[str, Any]] = []

        for card in cards:
            try:
                title_tag = (
                    card.find(class_="base-search-card__title")
                    or card.find(class_="job-search-card__title")
                )
                title = title_tag.get_text(strip=True) if title_tag else ""

                company_tag = (
                    card.find(class_="hidden-nested-link")
                    or card.find(class_="base-search-card__subtitle")
                    or card.find(class_="job-search-card__company-name")
                )
                company = company_tag.get_text(strip=True) if company_tag else ""

                location_tag = (
                    card.find(class_="job-search-card__location")
                    or card.find(class_="base-search-card__metadata")
                )
                location = location_tag.get_text(strip=True) if location_tag else ""

                link_tag = card.find("a", class_="base-card__full-link")
                if link_tag is None:
                    link_tag = card.find("a", href=True)
                job_url = link_tag["href"].split("?")[0] if link_tag else ""

                if title or job_url:
                    results.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "job_url": job_url,
                    })
            except Exception as parse_exc:
                logger.debug(f"[LinkedIn] Card parse error: {parse_exc}")
                continue

        return results
