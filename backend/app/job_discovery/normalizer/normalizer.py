from typing import Dict, Any, List
import logging

logger = logging.getLogger("app.job_discovery.normalizer")

class JobNormalizer:
    def normalize(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maps raw crawled job metadata into a standardized structure.
        """
        title = (raw_job.get("title") or "").strip()
        company = (raw_job.get("company_name") or "").strip()
        
        # Base normalized dictionary
        normalized = {
            "external_id": raw_job.get("external_id"),
            "title": title,
            "title_normalized": title.lower().strip(),
            "company_name": company,
            "description": raw_job.get("description", ""),
            "description_summary": raw_job.get("description_summary") or "",
            "apply_url": raw_job.get("apply_url") or "",
            "job_url": raw_job.get("job_url") or "",
            "location": raw_job.get("location") or "India",
            "city": raw_job.get("city") or "",
            "state": raw_job.get("state") or "",
            "country": raw_job.get("country") or "IN",
            "is_remote": bool(raw_job.get("is_remote", False)),
            "is_hybrid": bool(raw_job.get("is_hybrid", False)),
            "role_category": raw_job.get("role_category") or "",
            "industry": raw_job.get("industry") or "",
            "seniority": raw_job.get("seniority") or "mid",
            "employment_type": raw_job.get("employment_type") or "full_time",
            "required_skills": raw_job.get("required_skills") or [],
            "preferred_skills": raw_job.get("preferred_skills") or [],
            "salary_min": raw_job.get("salary_min"),
            "salary_max": raw_job.get("salary_max"),
            "salary_currency": raw_job.get("salary_currency") or "INR",
            "salary_raw": raw_job.get("salary_raw") or "",
            "experience_min_years": raw_job.get("experience_min_years"),
            "experience_max_years": raw_job.get("experience_max_years"),
            "posted_at": raw_job.get("posted_at"),
            "source_name": raw_job.get("source_name") or "unknown",
            "lifecycle_status": "normalized"
        }
        return normalized
