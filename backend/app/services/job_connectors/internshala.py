"""
Internshala connector — great for fresher / entry-level roles.
Searches Yahoo for Internshala job listings.
"""
import re
import logging
from typing import List
from .base import (
    LiveJob, yahoo_search, extract_yahoo_results,
    infer_location, infer_work_mode, COMMON_HEADERS
)

logger = logging.getLogger(__name__)

SOURCE = "Internshala"


def _clean_title(raw: str) -> str:
    title = re.sub(r'\s*[-|]\s*internshala.*', '', raw, flags=re.IGNORECASE)
    title = re.sub(r'\s*internship\s*$', '', title, flags=re.IGNORECASE)
    return title.strip(' -|')


def fetch(queries: List[str]) -> List[LiveJob]:
    jobs: List[LiveJob] = []
    seen_urls: set = set()

    # For Internshala we use fresher-focused queries
    fresher_queries = [
        f'{q} fresher' if "intern" not in q.lower() else q
        for q in queries[:3]
    ]
    fresher_queries.append('"software developer" internship India site:internshala.com')

    for query in fresher_queries[:4]:
        search_query = f'{query} site:internshala.com/jobs/'
        soup = yahoo_search(search_query, COMMON_HEADERS, timeout=8)
        results = extract_yahoo_results(soup)

        for r in results:
            url = r["url"]
            if "internshala.com" not in url:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)

            raw_title = r["title"]
            snippet = r["snippet"]
            title = _clean_title(raw_title)

            company = "Startup"
            if " at " in title:
                parts = title.split(" at ", 1)
                title = parts[0].strip()
                company = parts[1].strip()
            elif " - " in title:
                parts = title.split(" - ", 1)
                title = parts[0].strip()
                company = parts[1].strip()

            full_text = f"{raw_title} {snippet}"
            location = infer_location(full_text, default="India (Remote Friendly)")
            work_mode = infer_work_mode(full_text)

            # Internshala is mostly fresher/intern roles
            experience = "Fresher / 0-1 Yrs"
            if "job" in url.lower() and "intern" not in title.lower():
                experience = "0-2 Years"

            skill_words = re.findall(
                r'\b(Python|React|Node\.js|Java|SQL|Django|Flutter|'
                r'TypeScript|JavaScript|Machine Learning|PHP|WordPress|'
                r'Android|iOS|Data Science|Excel|Figma)\b',
                full_text, re.IGNORECASE
            )
            skills = list({s.title() for s in skill_words}) or ["Programming"]

            desc = (
                f"Job/Internship listing on Internshala for {title} at {company}.\n\n"
                f"{snippet}\n\n"
                f"Apply on Internshala: {url}"
            )

            jobs.append(LiveJob(
                title=title or "Software Developer",
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

    logger.info(f"Internshala connector returned {len(jobs)} jobs")
    return jobs
