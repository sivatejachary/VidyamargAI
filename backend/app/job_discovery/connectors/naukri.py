"""
Naukri Job Connector — Serper Search API.
==========================================
Discovers jobs from Naukri.com by querying search index via Serper.
Bypasses Naukri's anti-scraping walls.

Query pattern:
  site:naukri.com "{role}" "{location}"
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import datetime
from typing import Any, Dict, List

import httpx
from dateutil import parser as dateparser

from app.core.config import settings
from app.job_discovery.connectors.base import BaseConnector

logger = logging.getLogger("app.job_discovery.connectors.naukri")

SERPER_SEARCH_URL = "https://google.serper.dev/search"


def _clean_naukri_title(title_raw: str) -> tuple[str, str]:
    """
    Cleans Naukri search result title.
    Usually: "Python Developer Jobs in Bangalore - Naukri.com"
    or "Python Developer - [Company] - Bangalore - Naukri.com"
    """
    text = re.sub(r"\s*-\s*Naukri\.com\s*$", "", title_raw, flags=re.IGNORECASE)
    parts = [p.strip() for p in text.split("-") if p.strip()]
    
    if len(parts) >= 2:
        # Title - Company
        role = parts[0]
        company = parts[1]
    else:
        role = parts[0] if parts else "Software Engineer"
        company = "Naukri Hiring Company"

    # Clean "Jobs in..." from role
    role = re.sub(r"\s+Jobs\s+in\s+.*$", "", role, flags=re.IGNORECASE)
    return role.strip(), company.strip()


def _parse_job_from_result(title_raw: str, snippet: str, link: str, location: str) -> Dict[str, Any]:
    role, company = _clean_naukri_title(title_raw)

    # Remote check
    is_remote = "remote" in snippet.lower() or "wfh" in snippet.lower() or "work from home" in snippet.lower()
    
    # Skills extraction from snippet
    skills = []
    m_skills = re.search(r"(?:skills|key skills|keywords):?\s*([^\.]+)", snippet, re.IGNORECASE)
    if m_skills:
        skills = [s.strip() for s in re.split(r"[,|/•]", m_skills.group(1)) if len(s.strip()) > 1][:10]

    return {
        "title": role or "Software Engineer",
        "company_name": company or "Naukri Partner Company",
        "description": snippet,
        "apply_url": link,
        "job_url": link,
        "location": location,
        "is_remote": is_remote,
        "required_skills": skills,
    }


class NaukriConnector(BaseConnector):
    """
    Async connector that searches Naukri.com postings via Serper Google Search API.
    Concurrently searches for roles and locations.
    """

    SOURCE_NAME = "naukri"
    MAX_RESULTS_PER_QUERY = 10
    DEFAULT_TIMEOUT = 15.0

    async def async_search(
        self,
        roles: List[str],
        locations: List[str],
        skills: List[str],
        max_results: int = 50,
        client: httpx.AsyncClient | None = None,
    ) -> List[Dict[str, Any]]:
        if not settings.SERPER_API_KEY:
            logger.warning("[Naukri] SERPER_API_KEY not configured. Skipping.")
            return []

        headers = {
            "X-API-KEY": settings.SERPER_API_KEY,
            "Content-Type": "application/json",
        }
        owned_client, owns = await self._get_client(client, headers=headers)

        try:
            # Pair roles and locations (max 3 roles × 2 locations)
            queries = [
                (role, location)
                for role in roles[:3]
                for location in locations[:2]
            ]

            tasks = [
                self._search_query(owned_client, role, location)
                for role, location in queries
            ]
            results_per_query = await asyncio.gather(*tasks, return_exceptions=True)

            all_jobs: List[Dict[str, Any]] = []
            seen: set[str] = set()

            for result in results_per_query:
                if isinstance(result, Exception):
                    logger.error(f"[Naukri] Query task failed: {result}")
                    continue
                for job in result:
                    ext_id = job.get("external_id")
                    if ext_id and ext_id in seen:
                        continue
                    if ext_id:
                        seen.add(ext_id)
                    all_jobs.append(job)
                    if len(all_jobs) >= max_results:
                        return all_jobs

            return all_jobs
        finally:
            if owns:
                await owned_client.aclose()

    async def _search_query(
        self,
        client: httpx.AsyncClient,
        role: str,
        location: str,
    ) -> List[Dict[str, Any]]:
        query = f'site:naukri.com "{role}" "{location}"'
        payload = {
            "q": query,
            "num": self.MAX_RESULTS_PER_QUERY,
        }

        try:
            resp = await client.post(SERPER_SEARCH_URL, json=payload)
            if resp.status_code != 200:
                logger.warning(
                    f"[Naukri] HTTP {resp.status_code} for query '{query}': {resp.text[:200]}"
                )
                return []

            data = resp.json()
            organic_results = data.get("organic", [])
            return self._parse_organic_results(organic_results, location)

        except httpx.TimeoutException:
            logger.warning(f"[Naukri] Timeout on query '{query}'")
            return []
        except Exception as e:
            logger.error(f"[Naukri] Query '{query}' failed: {e}")
            return []

    def _parse_organic_results(
        self, items: List[Dict[str, Any]], location: str
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for item in items:
            try:
                title = item.get("title", "").strip()
                snippet = item.get("snippet", "").strip()
                link = item.get("link", "").strip()
                if not title or not snippet or not link:
                    continue

                parsed = _parse_job_from_result(title, snippet, link, location)
                ext_id = hashlib.md5(
                    f"naukri:{parsed['job_url']}:{parsed['title']}".encode()
                ).hexdigest()

                posted_at = None
                date_str = item.get("date", "")
                if date_str:
                    try:
                        posted_at = dateparser.parse(date_str)
                    except Exception:
                        pass

                job = self._build_empty_job()
                job.update(parsed)
                job.update({
                    "external_id": ext_id,
                    "posted_at": posted_at,
                    "source_name": self.SOURCE_NAME,
                })
                results.append(job)
            except Exception as e:
                logger.warning(f"[Naukri] Failed to parse item: {e}")

        return results
