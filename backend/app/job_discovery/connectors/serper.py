"""
Serper Jobs Connector — Async rewrite using httpx.

Replaces the blocking `requests.post` with a true async httpx call.
SERPER_API_KEY is sourced from settings. Falls back gracefully if
the key is missing or if the API returns a non-200 response.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from typing import Any, Dict, List

import httpx

from app.core.config import settings
from app.job_discovery.connectors.base import BaseConnector

logger = logging.getLogger("app.job_discovery.connectors.serper")

SERPER_JOBS_URL = "https://google.serper.dev/jobs"


def _extract_salary(text: str):
    """Extract min/max salary from raw text."""
    if not text:
        return None, None
    numbers = re.findall(r"[\d,]+(?:\.\d+)?", text.replace(",", ""))
    nums: List[float] = []
    for n in numbers:
        try:
            v = float(n)
            if 10_000 <= v <= 100_000_000:
                nums.append(v)
        except ValueError:
            pass
    if len(nums) >= 2:
        return min(nums), max(nums)
    if len(nums) == 1:
        return nums[0], nums[0] * 1.5
    return None, None


def _parse_experience(text: str):
    """Extract experience range in years from description text."""
    if not text:
        return None, None
    m = re.search(r"(\d+)\s*[-–to]+\s*(\d+)\s*(?:year|yr)", text, re.IGNORECASE)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"(\d+)\+?\s*(?:year|yr)", text, re.IGNORECASE)
    if m:
        return float(m.group(1)), None
    return None, None


class SerperJobsConnector(BaseConnector):
    """
    Async connector for Google Jobs via Serper API.

    Fires all (role × location) queries concurrently with asyncio.gather,
    then deduplicates results by external_id before returning.
    """

    SOURCE_NAME = "serper_jobs"
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
            logger.warning("[Serper] SERPER_API_KEY not configured. Skipping.")
            return []

        headers = {
            "X-API-KEY": settings.SERPER_API_KEY,
            "Content-Type": "application/json",
        }
        owned_client, owns = None, False
        if client is None:
            owned_client = httpx.AsyncClient(
                timeout=self.DEFAULT_TIMEOUT,
                headers=headers,
                follow_redirects=True,
            )
            owns = True
        else:
            owned_client = client

        try:
            # Build all (role × location) query pairs
            queries = [
                (role, location)
                for role in roles[:5]
                for location in locations[:2]
            ]

            # Execute all queries concurrently
            tasks = [
                self._search_query(owned_client, role, location)
                for role, location in queries
            ]
            results_per_query = await asyncio.gather(*tasks, return_exceptions=True)

            all_jobs: List[Dict[str, Any]] = []
            seen: set = set()

            for result in results_per_query:
                if isinstance(result, Exception):
                    logger.error(f"[Serper] Query task raised: {result}")
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
        query = f"{role} jobs {location}"
        payload = {
            "q": query,
            "location": location,
            "num": self.MAX_RESULTS_PER_QUERY,
        }
        headers = {
            "X-API-KEY": settings.SERPER_API_KEY,
            "Content-Type": "application/json",
        }

        try:
            resp = await client.post(
                SERPER_JOBS_URL,
                json=payload,
                headers=headers,
            )
            if resp.status_code != 200:
                logger.warning(
                    f"[Serper] HTTP {resp.status_code} for query '{query}': {resp.text[:200]}"
                )
                return []

            data = resp.json()
            return self._parse_jobs(data.get("jobs", []), location)

        except httpx.TimeoutException:
            logger.warning(f"[Serper] Timeout on query '{query}'")
            return []
        except Exception as e:
            logger.error(f"[Serper] Query '{query}' failed: {e}")
            return []

    def _parse_jobs(
        self, items: List[Dict[str, Any]], location: str
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for item in items:
            try:
                title = (item.get("title") or "").strip()
                company = (item.get("company") or "").strip()
                if not title or not company:
                    continue

                ext_id = hashlib.md5(
                    f"serper:{title}:{company}:{location}".encode()
                ).hexdigest()

                desc = item.get("description", "")
                salary_raw = item.get("salary", "")
                salary_min, salary_max = _extract_salary(salary_raw)
                exp_min, exp_max = _parse_experience(desc)

                job_location = item.get("location", location) or location
                parts = [p.strip() for p in job_location.split(",")]
                city = parts[0] if parts else ""
                state_val = parts[-1] if len(parts) >= 2 else ""

                is_remote = any(
                    w in job_location.lower()
                    for w in ["remote", "work from home", "anywhere", "wfh"]
                )

                posted_at = None
                posted_str = item.get("date", "")
                if posted_str:
                    try:
                        from dateutil import parser as dateparser
                        posted_at = dateparser.parse(posted_str)
                    except Exception:
                        pass

                job = self._build_empty_job()
                job.update({
                    "external_id": ext_id,
                    "title": title,
                    "company_name": company,
                    "description": desc,
                    "apply_url": item.get("applyLink") or item.get("shareLink", ""),
                    "job_url": item.get("shareLink", ""),
                    "location": job_location,
                    "city": city,
                    "state": state_val,
                    "country": "IN",
                    "is_remote": is_remote,
                    "salary_raw": salary_raw,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "salary_currency": "INR",
                    "experience_min_years": exp_min,
                    "experience_max_years": exp_max,
                    "posted_at": posted_at,
                    "source_name": self.SOURCE_NAME,
                })
                results.append(job)
            except Exception as e:
                logger.warning(f"[Serper] Failed to parse job item: {e}")

        return results
