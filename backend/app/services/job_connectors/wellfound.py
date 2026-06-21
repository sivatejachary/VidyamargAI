"""
Wellfound (formerly AngelList) connector — great for startup roles.
Searches Yahoo for Wellfound India job listings.
"""
import re
import logging
from typing import List
from .base import (
    LiveJob, yahoo_search, extract_yahoo_results,
    infer_location, infer_work_mode, infer_experience, COMMON_HEADERS
)

logger = logging.getLogger(__name__)

SOURCE = "Wellfound"


def _clean_title(raw: str) -> str:
    title = re.sub(r'\s*[-|]\s*wellfound.*', '', raw, flags=re.IGNORECASE)
    title = re.sub(r'\s*[-|]\s*angellist.*', '', title, flags=re.IGNORECASE)
    return title.strip(' -|')


def fetch(queries: List[str]) -> List[LiveJob]:
    jobs: List[LiveJob] = []
    seen_urls: set = set()

    for query in queries[:4]:
        search_query = f'{query} site:wellfound.com/jobs "India"'
        soup = yahoo_search(search_query, COMMON_HEADERS, timeout=8)
        results = extract_yahoo_results(soup)

        for r in results:
            url = r["url"]
            if "wellfound.com" not in url and "angel.co" not in url:
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

            # Try to get company from Wellfound URL e.g. /l/startup-name/role
            if company == "Startup":
                try:
                    path_parts = url.rstrip("/").split("/")
                    if len(path_parts) > 4:
                        slug = path_parts[-2]
                        company = slug.replace("-", " ").title()
                except Exception:
                    pass

            full_text = f"{raw_title} {snippet}"
            location = infer_location(full_text, default="India")
            work_mode = infer_work_mode(full_text)
            experience = infer_experience(f"{title} {snippet}")

            skill_words = re.findall(
                r'\b(Python|React|Node\.js|Java|SQL|AWS|Docker|Kubernetes|'
                r'FastAPI|Django|Flutter|TypeScript|JavaScript|Go|Rust|'
                r'Machine Learning|DevOps|MongoDB|PostgreSQL|Redis|Kafka|'
                r'TensorFlow|PyTorch|Blockchain|Web3|Solidity)\b',
                full_text, re.IGNORECASE
            )
            skills = list({s.title() for s in skill_words}) or ["Software Development"]

            desc = (
                f"Startup job found on Wellfound for {title} at {company}.\n\n"
                f"{snippet}\n\n"
                f"Apply on Wellfound: {url}"
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

    logger.info(f"Wellfound connector returned {len(jobs)} jobs")
    return jobs
