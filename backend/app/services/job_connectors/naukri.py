"""
Naukri.com connector.
Searches Yahoo for Naukri India job listings and extracts structured data.
"""
import re
import logging
from typing import List
from .base import (
    LiveJob, yahoo_search, extract_yahoo_results,
    infer_location, infer_work_mode, infer_experience, COMMON_HEADERS
)

logger = logging.getLogger(__name__)

SOURCE = "Naukri"


def _clean_title(raw: str) -> str:
    title = re.sub(r'\s*-\s*Naukri\.com.*', '', raw, flags=re.IGNORECASE)
    title = re.sub(r'\s*\|\s*Naukri.*', '', title, flags=re.IGNORECASE)
    return title.strip(' -|')


def _extract_company_from_naukri_url(url: str) -> str:
    """
    Naukri URLs look like:
    /job-listings-python-developer-company-name-bangalore-1-to-3-years-250614007424
    """
    try:
        path = url.split("/job-listings-")[-1].split("?")[0].strip("/")
        path = re.sub(r'-\d{9,}$', '', path)   # strip job ID
        # Remove experience patterns like '-1-to-3-years'
        path = re.sub(r'-\d+-to-\d+-years?', '', path)
        path = re.sub(r'-\d+-years?', '', path)
        parts = path.split("-")
        # Company name usually in the last 2-4 parts
        if len(parts) >= 4:
            # Skip location words
            location_words = {"bangalore", "hyderabad", "mumbai", "pune", "delhi",
                              "chennai", "noida", "gurgaon", "remote", "india"}
            company_parts = []
            for p in reversed(parts):
                if p.lower() in location_words or len(p) <= 2:
                    break
                company_parts.insert(0, p)
                if len(company_parts) >= 3:
                    break
            if company_parts:
                return " ".join(company_parts).title()
    except Exception:
        pass
    return ""


def fetch(queries: List[str]) -> List[LiveJob]:
    """
    Fetch Naukri.com India jobs for the given list of search queries.
    """
    jobs: List[LiveJob] = []
    seen_urls: set = set()

    for query in queries[:5]:
        search_query = f'({query}) site:naukri.com/job-listings- "India"'
        soup = yahoo_search(search_query, COMMON_HEADERS, timeout=8)
        results = extract_yahoo_results(soup)

        for r in results:
            url = r["url"]
            if "naukri.com/job-listings" not in url:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)

            raw_title = r["title"]
            snippet = r["snippet"]

            title = _clean_title(raw_title)
            if " - " in title:
                parts = title.split(" - ", 1)
                title = parts[0].strip()
                company_hint = parts[1].strip()
            else:
                company_hint = ""

            company = _extract_company_from_naukri_url(url)
            if not company or len(company) < 2:
                company = company_hint or "Tech Company"

            full_text = f"{raw_title} {snippet}"
            location = infer_location(full_text)
            work_mode = infer_work_mode(full_text)
            experience = infer_experience(f"{title} {snippet}")

            skill_words = re.findall(
                r'\b(Python|React|Node\.js|Java|SQL|AWS|Docker|Kubernetes|'
                r'FastAPI|Django|Flutter|TypeScript|JavaScript|Go|Rust|'
                r'Machine Learning|DevOps|Kafka|Spark|Redis|MongoDB|'
                r'PostgreSQL|MySQL|TensorFlow|PyTorch|C\+\+|Spring|Angular)\b',
                full_text, re.IGNORECASE
            )
            skills = list({s.title() for s in skill_words}) or ["Software Development"]

            desc = (
                f"Job listing found on Naukri.com for {title} at {company}.\n\n"
                f"{snippet}\n\n"
                f"View full details and apply on Naukri: {url}"
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

    logger.info(f"Naukri connector returned {len(jobs)} jobs")
    return jobs
