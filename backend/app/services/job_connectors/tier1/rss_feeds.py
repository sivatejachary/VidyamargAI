"""
RSS/Atom job feed aggregator — free, fast, no blocking.
Indeed, RemoteOK, Hacker News Who's Hiring, Stack Overflow Jobs.
"""
import feedparser
import asyncio
import httpx
import logging
from typing import List
from app.services.job_connectors.base import LiveJob
from app.services.job_connectors.tier1.greenhouse_api import _strip_html, _detect_work_mode, _extract_skills_from_content

logger = logging.getLogger("app.job_connectors.rss")

RSS_FEEDS = {
    "indeed_india": "https://in.indeed.com/rss?q={query}&l=India",
    "remoteok": "https://remoteok.com/remote-{skill}-jobs.rss",
    "hackernews_jobs": "https://hnrss.org/jobs",
    "we_work_remotely": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
}


async def fetch_rss_jobs(queries: List[str], skills: List[str]) -> List[LiveJob]:
    """Parse multiple RSS/Atom feeds in parallel."""
    tasks = []
    seen_urls = set()
    for name, url_template in RSS_FEEDS.items():
        if "{query}" in url_template or "{skill}" in url_template:
            for query in queries[:3]:
                skill_val = skills[0].lower() if skills else "python"
                url = url_template.format(
                    query=query.replace(" ", "+"),
                    skill=skill_val
                )
                if url not in seen_urls:
                    seen_urls.add(url)
                    tasks.append(_parse_feed(name, url))
        else:
            url = url_template
            if url not in seen_urls:
                seen_urls.add(url)
                tasks.append(_parse_feed(name, url))


    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_jobs = []
    for r in results:
        if isinstance(r, list):
            all_jobs.extend(r)
    return all_jobs


async def _parse_feed(feed_name: str, url: str) -> List[LiveJob]:
    """Fetch and parse a single RSS feed."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return []
            
            # Parse feed content
            feed = feedparser.parse(resp.text)
            jobs = []
            for entry in feed.entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary") or entry.get("description") or ""
                clean_desc = _strip_html(summary)

                # Parse company name from title depending on feed
                company = "Unknown"
                job_title = title
                if "indeed" in feed_name:
                    # e.g., "Software Engineer - Google - Bangalore"
                    parts = title.split(" - ")
                    if len(parts) >= 2:
                        job_title = parts[0]
                        company = parts[1]
                elif "remoteok" in feed_name:
                    # e.g., "Software Engineer at Google"
                    if " at " in title:
                        job_title, company = title.split(" at ", 1)
                elif "we_work_remotely" in feed_name:
                    # e.g., "Google: Software Engineer"
                    if ":" in title:
                        company, job_title = title.split(":", 1)
                
                jobs.append(LiveJob(
                    title=job_title.strip(),
                    company=company.strip(),
                    location="Remote" if "remote" in feed_name else "India",
                    experience="",
                    skills=_extract_skills_from_content(clean_desc),
                    apply_url=link,
                    posted_date="",
                    source=feed_name.replace("_", " ").title(),
                    description=clean_desc,
                    work_mode=_detect_work_mode(entry),
                    company_logo=None,
                ))
            return jobs
    except Exception as e:
        logger.warning(f"Failed to parse RSS feed {feed_name} from {url}: {e}")
        return []
