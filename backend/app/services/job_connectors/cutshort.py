import re
import logging
from typing import List
from .base import (
    LiveJob, yahoo_search, extract_yahoo_results,
    infer_location, infer_work_mode, infer_experience, COMMON_HEADERS
)

logger = logging.getLogger(__name__)
SOURCE = "CutShort"

def fetch(queries: List[str]) -> List[LiveJob]:
    jobs: List[LiveJob] = []
    seen_urls = set()

    for query in queries[:3]:
        search_query = f'{query} site:cutshort.io/job/ OR site:cutshort.io/jobs "India"'
        soup = yahoo_search(search_query, COMMON_HEADERS, timeout=8)
        results = extract_yahoo_results(soup)

        for r in results:
            url = r["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)

            raw_title = r["title"]
            snippet = r["snippet"]
            
            title = re.sub(r'\s*-\s*Cutshort.*', '', raw_title, flags=re.IGNORECASE).strip()
            if " at " in title.lower():
                parts = re.split(r'\s+at\s+', title, flags=re.IGNORECASE)
                title = parts[0].strip()
                company = parts[1].strip()
            else:
                company = "Startup Partner"

            full_text = f"{raw_title} {snippet}"
            location = infer_location(full_text)
            work_mode = infer_work_mode(full_text)
            experience = infer_experience(full_text)

            skill_words = re.findall(
                r'\b(Python|React|Node\.js|Java|SQL|AWS|Docker|Kubernetes|'
                r'FastAPI|Django|Flutter|TypeScript|JavaScript|Go|Rust|'
                r'Machine Learning|DevOps|Kafka|Spark|Redis|MongoDB|'
                r'PostgreSQL|MySQL|TensorFlow|PyTorch)\b',
                full_text, re.IGNORECASE
            )
            skills = list({s.title() for s in skill_words}) or ["Software Development"]

            jobs.append(LiveJob(
                title=title or "Software Engineer",
                company=company,
                location=location,
                experience=experience,
                skills=skills,
                apply_url=url,
                posted_date="Recently",
                source=SOURCE,
                description=f"Opportunity found on CutShort:\n\n{snippet}\n\nApply on CutShort: {url}",
                work_mode=work_mode,
            ))
    logger.info(f"CutShort connector returned {len(jobs)} jobs")
    return jobs
