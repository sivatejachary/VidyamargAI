"""
LinkedIn Jobs connector.
Searches Yahoo for LinkedIn India job listings and extracts structured data.
"""
import re
import logging
from typing import List
from .base import (
    LiveJob, yahoo_search, extract_yahoo_results,
    infer_location, infer_work_mode, infer_experience, COMMON_HEADERS
)

logger = logging.getLogger(__name__)

SOURCE = "LinkedIn"


def _clean_title(raw: str) -> str:
    """Strip LinkedIn boilerplate from job titles."""
    title = re.sub(r'\s*\|\s*LinkedIn.*', '', raw, flags=re.IGNORECASE)
    title = re.sub(r'\s*-\s*in\.linkedin\.com.*', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\bLinkedIn\b.*', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s*-\s*LinkedIn.*', '', title, flags=re.IGNORECASE)
    return title.strip(' -|')


def _extract_company_from_linkedin_url(url: str) -> str:
    """
    Try to extract company name from a LinkedIn job URL like:
    /jobs/view/senior-python-developer-at-razorpay-12345
    """
    try:
        path = url.split("/view/")[-1].split("?")[0].strip("/")
        path = re.sub(r'-\d+$', '', path)
        if "-at-" in path:
            slug = path.split("-at-")[-1]
            return slug.replace("-", " ").title()
        if "-hiring-" in path:
            slug = path.split("-hiring-")[-1]
            return slug.replace("-", " ").title()
    except Exception:
        pass
    return ""


def _extract_company_from_title(title: str) -> tuple:
    """Split 'Software Engineer at Razorpay' → ('Software Engineer', 'Razorpay')"""
    if " at " in title:
        parts = title.split(" at ", 1)
        return parts[0].strip(), parts[1].strip()
    if " - " in title:
        parts = title.split(" - ", 1)
        company = parts[1].strip()
        if " - " in company:
            company = company.split(" - ", 1)[0].strip()
        return parts[0].strip(), company
    return title, ""


def fetch(queries: List[str]) -> List[LiveJob]:
    """
    Fetch LinkedIn India jobs for the given list of search queries.
    Returns a list of LiveJob objects.
    """
    jobs: List[LiveJob] = []
    seen_urls: set = set()

    for query in queries[:6]:  # Limit concurrent Yahoo requests
        search_query = f'({query}) site:in.linkedin.com/jobs/view/ "India"'
        soup = yahoo_search(search_query, COMMON_HEADERS, timeout=8)
        results = extract_yahoo_results(soup)

        for r in results:
            url = r["url"]
            if "linkedin.com/jobs/view/" not in url:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)

            raw_title = r["title"]
            snippet = r["snippet"]

            # Clean title
            title = _clean_title(raw_title)

            # Extract company
            company = _extract_company_from_linkedin_url(url)
            if not company or len(company) < 2:
                title, company = _extract_company_from_title(title)

            # Clean up company name
            company = re.sub(r'\s+jobs.*', '', company, flags=re.IGNORECASE)
            company = re.sub(r'\s+hiring.*', '', company, flags=re.IGNORECASE)
            company = company.strip(' -|')
            if not company or len(company) < 2:
                company = "Tech Company"

            full_text = f"{raw_title} {snippet}"
            location = infer_location(full_text)
            work_mode = infer_work_mode(full_text)
            experience = infer_experience(f"{title} {snippet}")

            # Extract skills from snippet (words matching common tech terms)
            skill_words = re.findall(
                r'\b(Python|React|Node\.js|Java|SQL|AWS|Docker|Kubernetes|'
                r'FastAPI|Django|Flutter|TypeScript|JavaScript|Go|Rust|'
                r'Machine Learning|DevOps|Kafka|Spark|Redis|MongoDB|'
                r'PostgreSQL|MySQL|TensorFlow|PyTorch)\b',
                full_text, re.IGNORECASE
            )
            skills = list({s.title() for s in skill_words}) or ["Software Development"]

            desc = (
                f"Job listing found on LinkedIn for {title} at {company}.\n\n"
                f"{snippet}\n\n"
                f"View full details and apply on LinkedIn: {url}"
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

    logger.info(f"LinkedIn connector returned {len(jobs)} jobs")
    return jobs
