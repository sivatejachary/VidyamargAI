import logging
import re
from typing import List
from app.services.job_connectors.base import LiveJob

logger = logging.getLogger(__name__)

class VerificationAgent:
    def __init__(self, jobs: List[LiveJob]):
        self.jobs = jobs
        self.stats = {
            "jobs_found": len(jobs),
            "duplicates_removed": 0,
            "non_india_removed": 0,
            "stale_removed": 0,
            "invalid_removed": 0,
            "final_matches": 0
        }

    def verify_and_deduplicate(self, log_fn=None) -> List[LiveJob]:
        """
        Filters out low-quality listings:
        - Removes duplicate listings (fuzzy checking on Title + Company + Location).
        - Enforces India-only locations (is_indian_job).
        - Enforces freshness (posted within 30 days).
        - Rejects listings with scam/expired indicators.
        """
        if log_fn:
            log_fn("Verifying jobs and detecting duplicates...", "info")

        from app.services.job_connectors.base import (
            is_indian_job, is_fresh_job, infer_source_from_url
        )

        scam_patterns = [
            r'pay\s+deposit', r'telegram\s+task', r'whatsapp\s+job', r'subscribe\s+to', 
            r'deposit\s+fee', r'registration\s+fee', r'buy\s+training', r'data\s+entry\s+scam'
        ]
        
        expired_patterns = [
            r'no\s+longer\s+accepting', r'expired\b', r'closed\b', r'broken\s+link', r'job\s+is\s+inactive'
        ]

        priority_order = ["LinkedIn", "Instahyre", "Wellfound", "Naukri", "Indeed", "Telegram", "Greenhouse", "Lever", "RSS"]
        def get_priority(src: str) -> int:
            s_clean = (src or "").split(" ")[0].strip()
            for idx, p in enumerate(priority_order):
                if p.lower() in s_clean.lower():
                    return idx
            return 99

        # Group jobs by fuzzy key: company + title + location
        grouped_jobs = {}
        scam_count = 0
        invalid_count = 0
        non_india_count = 0
        stale_count = 0

        for job in self.jobs:
            title = job.title or ""
            company = job.company or ""
            location = job.location or ""
            desc = job.description or ""
            
            # Check basic validity
            if not title or not company or len(title) < 3:
                invalid_count += 1
                continue

            # India Job Filter
            if not is_indian_job(location, desc):
                non_india_count += 1
                continue

            # Freshness Filter
            if not is_fresh_job(job.posted_date):
                stale_count += 1
                continue

            # Scam check
            desc_lower = desc.lower()
            title_lower = title.lower()
            full_text = f"{title_lower} {desc_lower}"
            if any(re.search(pat, full_text) for pat in scam_patterns):
                scam_count += 1
                continue

            # Expired check
            if any(re.search(pat, full_text) for pat in expired_patterns):
                invalid_count += 1
                continue

            # Group key
            key = (title.lower().strip(), company.lower().strip(), location.lower().strip())
            if key not in grouped_jobs:
                grouped_jobs[key] = []
            grouped_jobs[key].append(job)

        verified_jobs = []
        duplicate_removed_count = 0

        for key, job_list in grouped_jobs.items():
            if len(job_list) > 1:
                duplicate_removed_count += len(job_list) - 1
                job_list.sort(key=lambda j: get_priority(j.source))
                
            best_job = job_list[0]
            
            # Merge sources and descriptions
            all_sources = []
            seen_src = set()
            for j in job_list:
                src = infer_source_from_url(j.apply_url, j.source)
                if src not in seen_src:
                    seen_src.add(src)
                    all_sources.append(src)
                
                if j.description and len(j.description) > len(best_job.description or ""):
                    best_job.description = j.description
            
            best_job.source = best_job.source or all_sources[0]
            # Store structured all_sources and primary_source details on the object
            best_job.all_sources = all_sources
            
            verified_jobs.append(best_job)

        # Update statistics
        self.stats = {
            "jobs_found": len(self.jobs),
            "duplicates_removed": duplicate_removed_count,
            "non_india_removed": non_india_count,
            "stale_removed": stale_count,
            "invalid_removed": invalid_count + scam_count,
            "final_matches": len(verified_jobs)
        }

        if log_fn:
            log_fn(f"Verification stats: {self.stats}", "success")
            log_fn(f"Verified {len(verified_jobs)} high-quality jobs.", "success")

        logger.info(f"VerificationAgent stats: {self.stats}")
        return verified_jobs
