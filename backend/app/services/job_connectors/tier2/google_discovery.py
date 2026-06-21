"""
Google Search/Serper based Job Discovery.
Queries top job portals (LinkedIn, Naukri, Indeed, Wellfound) using search operators.
"""
import httpx
import logging
import urllib.parse
from typing import List
from app.core.config import settings
from app.services.job_connectors.base import LiveJob, google_search, infer_source_from_url

logger = logging.getLogger("app.job_connectors.google")


async def search_google_jobs(queries: List[str]) -> List[LiveJob]:
    """Search for jobs using Serper API (if key exists) or local google search."""
    if not queries:
        return []

    jobs = []
    # Try Serper API if key is available
    serper_key = getattr(settings, "SERPER_API_KEY", None)
    if serper_key:
        logger.info("Using Serper API for Google job discovery")
        jobs = await _search_serper(queries, serper_key)
    else:
        logger.info("Serper API key not found. Using local Google search fallback")
        jobs = _search_local_google(queries)

    return jobs


async def _search_serper(queries: List[str], api_key: str) -> List[LiveJob]:
    jobs = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Search for top 2 queries to avoid high costs
        for q in queries[:2]:
            try:
                resp = await client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                    json={"q": q, "num": 10}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("organic", []):
                        jobs.append(_parse_organic_item(item))
            except Exception as e:
                logger.warning(f"Serper search failed for query '{q}': {e}")
    return [j for j in jobs if j is not None]


def _search_local_google(queries: List[str]) -> List[LiveJob]:
    jobs = []
    for q in queries[:2]:
        results = google_search(q, num_results=10)
        for r in results:
            url = r.get("url", "")
            title = r.get("title", "") or "Software Engineer"
            # Extract company from URL or title
            company = _extract_company_from_url(url)
            jobs.append(LiveJob(
                title=title,
                company=company,
                location="India",
                experience="",
                skills=[],
                apply_url=url,
                posted_date="",
                source=infer_source_from_url(url, "Google"),
                description=r.get("snippet", ""),
                work_mode="On-site",
                company_logo=None,
            ))
    return jobs


def _parse_organic_item(item: dict) -> LiveJob:
    url = item.get("link", "")
    title = item.get("title", "Job Posting")
    snippet = item.get("snippet", "")
    company = _extract_company_from_url(url)
    
    return LiveJob(
        title=title,
        company=company,
        location="India",
        experience="",
        skills=[],
        apply_url=url,
        posted_date="",
        source=infer_source_from_url(url, "Google Search"),
        description=snippet,
        work_mode="On-site",
        company_logo=None,
    )


def _extract_company_from_url(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        parts = domain.split(".")
        if len(parts) >= 2:
            return parts[-2].title()
        return domain.title()
    except Exception:
        return "Unknown"
