"""
LinkedIn Hiring Posts connector.
Searches Yahoo for LinkedIn posts with hiring keywords, then uses AI
to extract structured job details from the post text.
"""
import re
import json
import logging
from typing import List, Optional
from .base import (
    LiveJob, yahoo_search, extract_yahoo_results,
    infer_location, infer_work_mode, COMMON_HEADERS
)

logger = logging.getLogger(__name__)

SOURCE = "LinkedIn Post"

HIRING_KEYWORDS = [
    '"hiring" OR "looking for"',
    '"we are hiring" OR "job opening"',
    '"referral available" OR "referral bonus"',
    '"urgent hiring" OR "immediate joining"',
]


def _ai_extract(raw_text: str) -> Optional[dict]:
    """
    Use Gemini/NVIDIA to extract structured job info from a LinkedIn post.
    Bypassed to save time and API rate limits. Returns None.
    """
    return None


def fetch(skills: List[str]) -> List[LiveJob]:
    """
    Search for LinkedIn hiring posts and extract job details via AI.
    """
    jobs: List[LiveJob] = []
    seen_urls: set = set()

    skills_term = skills[0] if skills else "hiring"
    
    for kw in ["hiring", "job opening"]:
        query = f'"{skills_term}" "{kw}" site:linkedin.com/posts/ "India"'
        soup = yahoo_search(query, COMMON_HEADERS, timeout=8)
        results = extract_yahoo_results(soup)

        for r in results[:5]:  # Max 5 posts per keyword
            url = r["url"]
            if "linkedin.com/posts/" not in url:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)

            raw_text = f"{r['title']}\n{r['snippet']}"

            # Try AI extraction
            details = _ai_extract(raw_text)

            if details and details.get("is_job_post", False):
                title = details.get("title") or "Software Engineer"
                company = details.get("company") or "Tech Company"
                location = details.get("location") or infer_location(raw_text)
                work_mode = details.get("work_mode") or infer_work_mode(raw_text)
                experience = details.get("experience") or "Not Specified"
                extracted_skills = details.get("skills") or []
                apply_link = details.get("apply_link") or url
                contact_email = details.get("contact_email")

                desc_parts = [f"LinkedIn Hiring Post by recruiter at {company}.\n"]
                desc_parts.append(raw_text)
                if contact_email:
                    desc_parts.append(f"\n\nContact: {contact_email}")
                desc_parts.append(f"\n\nOriginal Post: {url}")
                if apply_link and apply_link != url:
                    desc_parts.append(f"\nApply Here: {apply_link}")

                jobs.append(LiveJob(
                    title=title,
                    company=company,
                    location=location,
                    experience=experience,
                    skills=extracted_skills or ["Software Development"],
                    apply_url=apply_link,
                    posted_date="Recently",
                    source=SOURCE,
                    description="\n".join(desc_parts),
                    work_mode=work_mode,
                ))
            else:
                # Fallback: use snippet directly without AI extraction
                full_text = raw_text
                title_raw = r["title"].split("|")[0].strip()
                title = re.sub(r'\bLinkedIn\b.*', '', title_raw, flags=re.IGNORECASE).strip(' -|')

                if not title or len(title) < 5:
                    continue

                location = infer_location(full_text)
                work_mode = infer_work_mode(full_text)

                skill_words = re.findall(
                    r'\b(Python|React|Node\.js|Java|SQL|AWS|Docker|FastAPI|'
                    r'Flutter|TypeScript|JavaScript|Machine Learning|DevOps)\b',
                    full_text, re.IGNORECASE
                )
                extracted_skills = list({s.title() for s in skill_words}) or skills[:3]

                jobs.append(LiveJob(
                    title=title,
                    company="LinkedIn Recruiter",
                    location=location,
                    experience="Not Specified",
                    skills=[s.title() for s in extracted_skills],
                    apply_url=url,
                    posted_date="Recently",
                    source=SOURCE,
                    description=f"Hiring post found on LinkedIn.\n\n{r['snippet']}\n\nView post: {url}",
                    work_mode=work_mode,
                ))

    logger.info(f"LinkedIn Hiring Posts connector returned {len(jobs)} jobs")
    return jobs
