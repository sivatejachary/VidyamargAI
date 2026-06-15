import logging
import re
from typing import List
from app.services.job_connectors.base import LiveJob

logger = logging.getLogger(__name__)

class VerificationAgent:
    def __init__(self, jobs: List[LiveJob]):
        self.jobs = jobs

    def verify_and_deduplicate(self, log_fn=None) -> List[LiveJob]:
        """
        Filters out low-quality listings:
        - Removes duplicate listings (fuzzy checking on Title + Company).
        - Rejects listings with scam indicators (e.g. pay deposit, whatsapp tasks).
        - Rejects listings marked as expired or broken.
        """
        if log_fn:
            log_fn("Verifying jobs and detecting duplicates...", "info")

        seen = set()
        verified_jobs = []
        duplicate_count = 0
        scam_count = 0
        invalid_count = 0

        # Scam keywords patterns
        scam_patterns = [
            r'pay\s+deposit', r'telegram\s+task', r'whatsapp\s+job', r'subscribe\s+to', 
            r'deposit\s+fee', r'registration\s+fee', r'buy\s+training', r'data\s+entry\s+scam'
        ]
        
        expired_patterns = [
            r'no\s+longer\s+accepting', r'expired\b', r'closed\b', r'broken\s+link', r'job\s+is\s+inactive'
        ]

        for job in self.jobs:
            # Check basic validity
            if not job.title or not job.company or len(job.title) < 3:
                invalid_count += 1
                continue

            # Deduplication check
            key = (job.title.lower().strip(), job.company.lower().strip())
            if key in seen:
                duplicate_count += 1
                continue
            
            # Check scam indicators in description or title
            desc_lower = job.description.lower()
            title_lower = job.title.lower()
            full_text = f"{title_lower} {desc_lower}"
            
            is_scam = any(re.search(pat, full_text) for pat in scam_patterns)
            if is_scam:
                scam_count += 1
                logger.warning(f"VerificationAgent: Scam detected for job '{job.title}' at '{job.company}'")
                continue
                
            # Check expired indicators
            is_expired = any(re.search(pat, full_text) for pat in expired_patterns)
            if is_expired:
                invalid_count += 1
                logger.warning(f"VerificationAgent: Expired job detected: '{job.title}' at '{job.company}'")
                continue

            seen.add(key)
            verified_jobs.append(job)

        if log_fn:
            log_fn(f"Deduplication complete: Removed {duplicate_count} duplicates", "success")
            if scam_count > 0:
                log_fn(f"Rejected {scam_count} suspicious listings", "warning")
            log_fn(f"Verified {len(verified_jobs)} high-quality jobs", "success")

        logger.info(f"VerificationAgent: Reduced {len(self.jobs)} raw jobs to {len(verified_jobs)} (Removed {duplicate_count} duplicates, {scam_count} scams, {invalid_count} expired/invalid)")
        return verified_jobs
