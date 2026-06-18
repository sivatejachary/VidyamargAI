"""
Greenhouse Job Board API — direct read-only access.
No auth required for public job boards.
Returns 100% real, structured job data.
"""
import httpx
import asyncio
import logging
import re
from typing import List
from app.services.job_connectors.base import LiveJob

logger = logging.getLogger("app.job_connectors.greenhouse")

# Top Indian tech companies on Greenhouse
GREENHOUSE_BOARDS = [
    "razorpay", "paytm", "cred", "swiggy", "meesho",
    "groww", "zerodha", "freshworks", "browserstack",
    "setu", "setu-api", "juspay", "niyo", "jupiter",
    "smallcase", "slice", "cashfree", "decentro", "hyperface",
]


async def fetch_greenhouse_jobs(queries: List[str]) -> List[LiveJob]:
    """Fetch jobs from all Greenhouse-hosted company boards."""
    all_jobs = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [_fetch_board(client, company) for company in GREENHOUSE_BOARDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, list):
                all_jobs.extend(r)

    return _filter_relevant(all_jobs, queries)


async def _fetch_board(client, company: str) -> List[LiveJob]:
    """Fetch all jobs from a single Greenhouse board."""
    try:
        resp = await client.get(
            f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs",
            params={"content": "true"}
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        jobs = []
        for job in data.get("jobs", []):
            jobs.append(LiveJob(
                title=job["title"],
                company=company.replace("-", " ").title(),
                location=_parse_location(job.get("location", {})),
                experience="",
                skills=_extract_skills_from_content(job.get("content", "")),
                apply_url=job["absolute_url"],
                posted_date=job.get("updated_at", "")[:10],
                source="Greenhouse",
                description=_strip_html(job.get("content", "")),
                work_mode=_detect_work_mode(job),
                company_logo=None,
            ))
        return jobs
    except Exception as e:
        logger.warning(f"Failed to fetch Greenhouse board for {company}: {e}")
        return []


def _parse_location(location: dict) -> str:
    if not location:
        return "India"
    return location.get("name") or "India"


def _detect_work_mode(job: dict) -> str:
    text = (job.get("title", "") + job.get("content", "")).lower()
    if "remote" in text:
        return "Remote"
    if "hybrid" in text:
        return "Hybrid"
    return "On-site"


def _strip_html(html_text: str) -> str:
    if not html_text:
        return ""
    # simple regex strip html tags
    clean = re.compile("<.*?>")
    text = re.sub(clean, " ", html_text)
    # decode common html entities
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", text).strip()


def _extract_skills_from_content(content: str) -> List[str]:
    if not content:
        return []
    common_skills = [
        "Python", "Java", "React", "Node.js", "TypeScript", "JavaScript",
        "Next.js", "Django", "FastAPI", "Spring Boot", "AWS", "Docker",
        "Kubernetes", "SQL", "PostgreSQL", "MongoDB", "Redis", "Machine Learning",
        "TensorFlow", "PyTorch", "Git", "CI/CD", "DevOps"
    ]
    found = []
    content_lower = content.lower()
    for s in common_skills:
        # Match word boundaries or symbols like .js, +
        pattern = r"\b" + re.escape(s.lower()) + r"\b"
        if re.search(pattern, content_lower):
            found.append(s)
    return found


def _filter_relevant(jobs: List[LiveJob], queries: List[str]) -> List[LiveJob]:
    if not queries:
        return jobs
    filtered = []
    # compile queries into regexes or simple contains
    query_words = [q.lower().split() for q in queries]
    for job in jobs:
        title_lower = job.title.lower()
        desc_lower = job.description.lower()
        matched = False
        for words in query_words:
            # check if all words in a query are in title or description
            if all(w in title_lower or w in desc_lower for w in words):
                matched = True
                break
        if matched:
            filtered.append(job)
    return filtered
