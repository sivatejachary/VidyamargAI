import logging
import concurrent.futures
from typing import List
from app.services.job_connectors.base import LiveJob
from app.services.job_connectors import (
    linkedin_jobs, naukri, foundit, internshala, wellfound, hiring_posts,
    indeed, instahyre, cutshort, hirist
)

logger = logging.getLogger(__name__)

class SearchAgent:
    def __init__(self, queries: List[str], skills_raw: List[str], exp_years: float = 1.0):
        # Limit to the top 2 queries to ensure concurrent execution completes under 10 seconds
        self.queries = queries[:2]
        self.skills_raw = skills_raw
        self.exp_years = exp_years

    def execute_search(self, log_fn=None) -> List[LiveJob]:
        """
        Executes concurrent job searches across 10 sources:
        LinkedIn, Naukri, Foundit, Indeed, Wellfound, Internshala, Instahyre, CutShort, Hirist, and LinkedIn Hiring Posts.
        """
        all_jobs = []
        connectors = {
            "LinkedIn": lambda: linkedin_jobs.fetch(self.queries),
            "Naukri": lambda: naukri.fetch(self.queries),
            "Foundit": lambda: foundit.fetch(self.queries),
            "Indeed": lambda: indeed.fetch(self.queries),
            "Wellfound": lambda: wellfound.fetch(self.queries),
            "Internshala": lambda: internshala.fetch(self.queries),
            "Instahyre": lambda: instahyre.fetch(self.queries),
            "CutShort": lambda: cutshort.fetch(self.queries),
            "Hirist": lambda: hirist.fetch(self.queries),
            "HiringPosts": lambda: hiring_posts.fetch(self.skills_raw)
        }

        def _run_connector(name, func):
            if log_fn:
                log_fn(f"Searching {name}...", "info")
            try:
                res = func()
                logger.info(f"SearchAgent: {name} returned {len(res)} jobs")
                if log_fn:
                    log_fn(f"Found {len(res)} jobs on {name}", "success")
                return res
            except Exception as e:
                logger.error(f"SearchAgent: {name} failed: {e}")
                if log_fn:
                    log_fn(f"Failed to fetch from {name}: {e}", "warning")
                return []

        # Run concurrent searches in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(_run_connector, name, func): name 
                for name, func in connectors.items()
            }
            for fut in concurrent.futures.as_completed(futures):
                all_jobs.extend(fut.result())

        logger.info(f"SearchAgent: Completed aggregation. Total aggregated raw jobs: {len(all_jobs)}")

        # Returns real jobs only (no synthetic fallback jobs allowed)
        return all_jobs
