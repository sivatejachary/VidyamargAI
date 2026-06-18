"""
Lever Job Postings API — free, public, no auth required.
Direct JSON feed from Lever-hosted job boards.
"""
import httpx
import asyncio
import logging
import re
from typing import List
from app.services.job_connectors.base import LiveJob
from app.services.job_connectors.tier1.greenhouse_api import _strip_html, _detect_work_mode, _extract_skills_from_content, _filter_relevant

logger = logging.getLogger("app.job_connectors.lever")

LEVER_COMPANIES = [
    "netflix", "stripe", "airbnb", "notion", "figma",
    "razorpay", "phonepe", "groww", "zerodha", "swiggy",
    "delhivery", "ninjacart", "dunzo", "cred", "khatabook",
]


async def fetch_lever_jobs(queries: List[str]) -> List[LiveJob]:
    """Fetch jobs from all Lever-hosted company boards."""
    all_jobs = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [_fetch_board(client, co) for co in LEVER_COMPANIES]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, list):
                all_jobs.extend(r)

    return _filter_relevant(all_jobs, queries)


async def _fetch_board(client, company: str) -> List[LiveJob]:
    """Fetch all postings from a single Lever board."""
    try:
        resp = await client.get(f"https://api.lever.co/v0/postings/{company}?mode=json")
        if resp.status_code != 200:
            return []

        data = resp.json()
        jobs = []
        for job in data:
            categories = job.get("categories", {})
            location = categories.get("location") or "India"
            
            description = _strip_html(job.get("description", ""))
            lists = job.get("lists", [])
            for item in lists:
                content = item.get("content", "")
                if content:
                    description += " " + _strip_html(content)

            jobs.append(LiveJob(
                title=job["title"],
                company=company.replace("-", " ").title(),
                location=location,
                experience="",
                skills=_extract_skills_from_content(description),
                apply_url=job["hostedUrl"],
                posted_date="", # Lever public posting does not reliably provide updated dates in mode=json
                source="Lever",
                description=description,
                work_mode=_detect_work_mode(job),
                company_logo=None,
            ))
        return jobs
    except Exception as e:
        logger.warning(f"Failed to fetch Lever board for {company}: {e}")
        return []
