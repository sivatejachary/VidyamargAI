import re
import logging
import urllib.parse
from typing import List
from .base import (
    LiveJob, yahoo_search, extract_yahoo_results,
    infer_location, infer_work_mode, infer_experience, COMMON_HEADERS
)

logger = logging.getLogger(__name__)

SOURCE = "ATS"

def fetch(queries: List[str]) -> List[LiveJob]:
    """
    Dynamically search generic ATS providers using candidate queries.
    """
    jobs: List[LiveJob] = []
    seen_urls = set()

    ats_sites = [
        "boards.greenhouse.io",
        "jobs.lever.co",
        "ashbyhq.com",
        "myworkdayjobs.com"
    ]

    for query in queries[:2]:
        for site in ats_sites:
            search_query = f'{query} site:{site} "India"'
            try:
                soup = yahoo_search(search_query, COMMON_HEADERS, timeout=8)
                results = extract_yahoo_results(soup)
            except Exception as e:
                logger.error(f"ATS search failed for site {site} and query {query}: {e}")
                continue

            for r in results:
                url = r.get("url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                raw_title = r.get("title", "")
                snippet = r.get("snippet", "")
                
                # Extract company name from URL
                company = "Tech Company"
                try:
                    parsed_url = urllib.parse.urlparse(url)
                    netloc = parsed_url.netloc.lower()
                    path_parts = [p for p in parsed_url.path.split("/") if p]
                    
                    if "greenhouse.io" in netloc:
                        if len(path_parts) >= 1:
                            company = path_parts[0].replace("-", " ").title()
                    elif "lever.co" in netloc:
                        if len(path_parts) >= 1:
                            company = path_parts[0].replace("-", " ").title()
                    elif "ashbyhq.com" in netloc:
                        if len(path_parts) >= 1:
                            company = path_parts[0].replace("-", " ").title()
                    elif "myworkdayjobs.com" in netloc:
                        parts = netloc.split(".")
                        if len(parts) >= 3:
                            company = parts[0].replace("-", " ").title()
                except Exception as e:
                    logger.warning(f"Error parsing company from ATS URL {url}: {e}")

                title = raw_title
                if " - " in title:
                    parts = title.split(" - ", 1)
                    title = parts[0].strip()
                elif " | " in title:
                    parts = title.split(" | ", 1)
                    title = parts[0].strip()

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

                ats_source = "ATS"
                if "greenhouse.io" in url:
                    ats_source = "Greenhouse"
                elif "lever.co" in url:
                    ats_source = "Lever"
                elif "ashbyhq.com" in url:
                    ats_source = "Ashby"
                elif "myworkdayjobs.com" in url:
                    ats_source = "Workday"

                jobs.append(LiveJob(
                    title=title or "Software Engineer",
                    company=company,
                    location=location,
                    experience=experience,
                    skills=skills,
                    apply_url=url,
                    posted_date="Recently",
                    source=ats_source,
                    description=f"Opportunity found on {ats_source}:\n\n{snippet}\n\nApply URL: {url}",
                    work_mode=work_mode,
                ))
    logger.info(f"ATS connector returned {len(jobs)} jobs")
    return jobs
