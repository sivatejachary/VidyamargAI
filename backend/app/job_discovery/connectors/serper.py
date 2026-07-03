"""
Serper Jobs Connector — Uses Google Jobs via Serper API.
SERPER_API_KEY already exists in settings.
"""
import hashlib
import logging
import re
from typing import List, Dict, Any, Optional
import requests

from app.core.config import settings

logger = logging.getLogger("app.job_discovery.connectors.serper")

# Serper API: https://serper.dev/jobs
SERPER_JOBS_URL = "https://google.serper.dev/jobs"


def _extract_salary(text: str):
    """Extract salary numbers from text."""
    if not text:
        return None, None
    numbers = re.findall(r"[\d,]+(?:\.\d+)?", text.replace(",", ""))
    nums = []
    for n in numbers:
        try:
            v = float(n)
            if 10000 <= v <= 100000000:  # ₹10K to ₹10Cr range
                nums.append(v)
        except ValueError:
            pass
    if len(nums) >= 2:
        return min(nums), max(nums)
    if len(nums) == 1:
        return nums[0], nums[0] * 1.5
    return None, None


def _parse_experience(text: str):
    """Extract experience range from text."""
    if not text:
        return None, None
    match = re.search(r"(\d+)\s*[-–to]+\s*(\d+)\s*(?:year|yr)", text, re.IGNORECASE)
    if match:
        return float(match.group(1)), float(match.group(2))
    match = re.search(r"(\d+)\+?\s*(?:year|yr)", text, re.IGNORECASE)
    if match:
        return float(match.group(1)), None
    return None, None


class SerperJobsConnector:
    """
    Searches Google Jobs via the Serper API.
    """

    MAX_PER_QUERY = 10

    def search(
        self,
        roles: List[str],
        locations: List[str],
        skills: List[str],
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        if not settings.SERPER_API_KEY:
            logger.warning("[Serper] SERPER_API_KEY not configured. Skipping.")
            return []

        all_jobs = []
        seen = set()

        for role in roles[:5]:
            for location in locations[:2]:
                query = f"{role} jobs {location}"
                try:
                    jobs = self._search_query(query, location)
                    for job in jobs:
                        ext_id = job.get("external_id")
                        if ext_id and ext_id in seen:
                            continue
                        if ext_id:
                            seen.add(ext_id)
                        all_jobs.append(job)
                        if len(all_jobs) >= max_results:
                            return all_jobs
                except Exception as e:
                    logger.error(f"[Serper] Query '{query}' failed: {e}")

        return all_jobs

    def _search_query(self, query: str, location: str) -> List[Dict[str, Any]]:
        headers = {
            "X-API-KEY": settings.SERPER_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {"q": query, "location": location, "num": self.MAX_PER_QUERY}

        resp = requests.post(SERPER_JOBS_URL, headers=headers, json=payload, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"[Serper] HTTP {resp.status_code}: {resp.text[:200]}")
            return []

        data = resp.json()
        jobs_raw = data.get("jobs", [])
        results = []

        for item in jobs_raw:
            try:
                title = item.get("title", "").strip()
                company = item.get("company", "").strip()
                if not title or not company:
                    continue

                # Build external ID from title + company + location
                ext_id = hashlib.md5(f"serper:{title}:{company}:{location}".encode()).hexdigest()

                desc = item.get("description", "")
                salary_raw = item.get("salary", "")
                salary_min, salary_max = _extract_salary(salary_raw)
                exp_min, exp_max = _parse_experience(desc)

                # Location parsing
                job_location = item.get("location", location)
                city = ""
                state_val = ""
                country_val = "IN"
                if job_location:
                    parts = [p.strip() for p in job_location.split(",")]
                    if parts:
                        city = parts[0]
                    if len(parts) >= 2:
                        state_val = parts[-1]

                is_remote = any(w in job_location.lower() for w in ["remote", "work from home", "anywhere", "wfh"])
                posted_str = item.get("date", "")
                posted_at = None
                if posted_str:
                    try:
                        from dateutil import parser as dateparser
                        posted_at = dateparser.parse(posted_str)
                    except Exception:
                        pass

                results.append({
                    "external_id": ext_id,
                    "title": title,
                    "company_name": company,
                    "description": desc,
                    "apply_url": item.get("applyLink") or item.get("shareLink", ""),
                    "job_url": item.get("shareLink", ""),
                    "location": job_location,
                    "city": city,
                    "state": state_val,
                    "country": country_val,
                    "is_remote": is_remote,
                    "salary_raw": salary_raw,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "salary_currency": "INR",
                    "experience_min_years": exp_min,
                    "experience_max_years": exp_max,
                    "required_skills": [],
                    "preferred_skills": [],
                    "posted_at": posted_at,
                    "source_name": "serper_jobs",
                })
            except Exception as e:
                logger.warning(f"[Serper] Failed to parse job item: {e}")

        return results
