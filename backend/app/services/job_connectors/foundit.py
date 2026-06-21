"""
Foundit.in (formerly Monster India) connector.
Searches Yahoo for Foundit India job listings.
"""
import re
import logging
from typing import List
from .base import (
    LiveJob, yahoo_search, extract_yahoo_results,
    infer_location, infer_work_mode, infer_experience, COMMON_HEADERS
)

logger = logging.getLogger(__name__)

SOURCE = "Foundit"


def _clean_title(raw: str) -> str:
    title = re.sub(r'\s*[-|]\s*foundit.*', '', raw, flags=re.IGNORECASE)
    title = re.sub(r'\s*[-|]\s*monster.*', '', title, flags=re.IGNORECASE)
    return title.strip(' -|')


def fetch(queries: List[str]) -> List[LiveJob]:
    jobs: List[LiveJob] = []
    seen_urls: set = set()

    for query in queries[:4]:
        search_query = f'{query} site:foundit.in "India"'
        soup = yahoo_search(search_query, COMMON_HEADERS, timeout=8)
        results = extract_yahoo_results(soup)

        for r in results:
            url = r["url"]
            if "foundit.in" not in url:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)

            raw_title = r["title"]
            snippet = r["snippet"]
            title = _clean_title(raw_title)

            company = "Tech Company"
            if " at " in title:
                parts = title.split(" at ", 1)
                title = parts[0].strip()
                company = parts[1].strip()
            elif " - " in title:
                parts = title.split(" - ", 1)
                title = parts[0].strip()
                company = parts[1].strip()

            full_text = f"{raw_title} {snippet}"
            location = infer_location(full_text)
            work_mode = infer_work_mode(full_text)
            experience = infer_experience(f"{title} {snippet}")

            skill_words = re.findall(
                r'\b(Python|React|Node\.js|Java|SQL|AWS|Docker|Kubernetes|'
                r'FastAPI|Django|Flutter|TypeScript|JavaScript|Go|'
                r'Machine Learning|DevOps|MongoDB|PostgreSQL|MySQL|Spring|Angular)\b',
                full_text, re.IGNORECASE
            )
            skills = list({s.title() for s in skill_words}) or ["Software Development"]

            desc = (
                f"Job listing found on Foundit.in for {title} at {company}.\n\n"
                f"{snippet}\n\n"
                f"View full details and apply: {url}"
            )

            jobs.append(LiveJob(
                title=title or "Software Engineer",
                company=company,
                location=location,
                experience=experience,
                skills=skills,
                apply_url=url,
                posted_date="Recently",
                source=SOURCE,
                description=desc,
                work_mode=work_mode,
            ))

    logger.info(f"Foundit connector returned {len(jobs)} jobs")
    return jobs
