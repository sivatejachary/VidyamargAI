"""
LinkedIn Posts Job Connector — Serper Search API.
==================================================
Discovers job postings by querying LinkedIn hiring posts using Google Search via Serper API.
No cookies or LinkedIn account authentication required.

Query pattern:
  site:linkedin.com/posts "hiring" "{role}" "{location}"
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

logger = logging.getLogger("app.job_discovery.connectors.linkedin_posts")

SERPER_SEARCH_URL = "https://google.serper.dev/search"


def _clean_title(text: str) -> str:
    """Cleans google search title for posts to extract name/headline/role."""
    # Example: "Rahul Sharma on LinkedIn: Hiring Python Developers!"
    text = re.sub(r"\s*on LinkedIn\s*:\s*", " | ", text, flags=re.IGNORECASE)
    return text.strip()


def _parse_job_from_post(title_raw: str, snippet: str, link: str, location: str) -> Dict[str, Any]:
    """Extracts job metadata from Google Search snippet and title."""
    title_clean = _clean_title(title_raw)
    
    # 1. Attempt to extract poster name and role
    poster_name = "LinkedIn Poster"
    if " | " in title_clean:
        parts = title_clean.split(" | ", 1)
        poster_name = parts[0].strip()
        headline_role = parts[1].strip()
    else:
        headline_role = title_clean

    # Clean up the role title
    job_title = headline_role
    for prefix in ["hiring", "we are hiring", "urgent hiring", "we're hiring", "open role"]:
        if job_title.lower().startswith(prefix):
            job_title = job_title[len(prefix):].strip(" :-–|,")

    # 2. Extract company from snippet/title
    company = "LinkedIn Hiring Post"
    m_co = re.search(r"\b(?:at|with|join|joining)\s+([A-Z][A-Za-z0-9\s&\.]{1,40}?)(?:\s*[,|\n\.]|\bfor\b)", snippet)
    if m_co:
        company = m_co.group(1).strip()
    else:
        # Check title for company
        m_co_title = re.search(r"\bat\s+([A-Z][A-Za-z0-9\s&\.]{1,40})", title_raw)
        if m_co_title:
            company = m_co_title.group(1).strip()

    # 3. Extract apply URL (prefer link found inside snippet, fallback to post link)
    apply_url = link
    m_url = re.search(r"https?://[^\s\)>\"\']+", snippet)
    if m_url:
        apply_url = m_url.group(0).strip()

    # 4. Extract experience
    m_exp = re.search(r"(\d+)\s*[-–to]+\s*(\d+)\s*(?:years?|yrs?)", snippet, re.IGNORECASE)
    exp_min = float(m_exp.group(1)) if m_exp else None
    exp_max = float(m_exp.group(2)) if m_exp else None

    # 5. Remote indicator
    is_remote = "remote" in snippet.lower() or "wfh" in snippet.lower() or "work from home" in snippet.lower()

    return {
        "title": job_title[:200] or "Software Engineer",
        "company_name": company[:150],
        "description": f"Posted by {poster_name}.\n\nSnippet:\n{snippet}",
        "apply_url": apply_url,
        "job_url": link,
        "location": location,
        "is_remote": is_remote,
        "experience_min_years": exp_min,
        "experience_max_years": exp_max,
    }


class LinkedInPostsConnector(BaseConnector):
    """
    Async connector that searches LinkedIn posts via Serper Google Search API.
    Concurrently searches for the first 3 roles × locations.
    """

    SOURCE_NAME = "linkedin_posts"
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
            logger.warning("[LinkedInPosts] SERPER_API_KEY not configured. Skipping.")
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
                    logger.error(f"[LinkedInPosts] Query task failed: {result}")
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
        query = f'site:linkedin.com/posts "hiring" "{role}" "{location}"'
        payload = {
            "q": query,
            "num": self.MAX_RESULTS_PER_QUERY,
        }

        try:
            resp = await client.post(SERPER_SEARCH_URL, json=payload)
            if resp.status_code != 200:
                logger.warning(
                    f"[LinkedInPosts] HTTP {resp.status_code} for query '{query}': {resp.text[:200]}"
                )
                return []

            data = resp.json()
            organic_results = data.get("organic", [])
            return self._parse_organic_results(organic_results, location)

        except httpx.TimeoutException:
            logger.warning(f"[LinkedInPosts] Timeout on query '{query}'")
            return []
        except Exception as e:
            logger.error(f"[LinkedInPosts] Query '{query}' failed: {e}")
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

                parsed = _parse_job_from_post(title, snippet, link, location)
                ext_id = hashlib.md5(
                    f"linkedin_post:{parsed['job_url']}:{parsed['title']}".encode()
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
                logger.warning(f"[LinkedInPosts] Failed to parse item: {e}")

        return results
