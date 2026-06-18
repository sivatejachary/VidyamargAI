"""
Job Discovery Agent — aggregates job listings from portals and Telegram channels.
"""
import asyncio
import logging
from sqlalchemy.orm import Session
from app.agents.search import SearchAgent
from app.agents.telegram import TelegramCommunityAgent
from app.agents.verification import VerificationAgent

logger = logging.getLogger("app.agents.job_discovery")


class JobDiscoveryAgent:
    def __init__(self, db: Session, queries: list, skills: list, experience_years: float):
        self.db = db
        self.queries = queries
        self.skills = skills
        self.experience_years = experience_years

    async def discover(self, log_cb) -> list:
        log_cb("Starting portal and Telegram community scans...", "info")
        
        search_agent = SearchAgent(self.queries, self.skills, self.experience_years)
        telegram_agent = TelegramCommunityAgent(self.db)

        def portal_log(msg, status="info"):
            log_cb(f"[Portal] {msg}", status)

        def telegram_log(msg, status="info"):
            log_cb(f"[Telegram] {msg}", status)

        loop = asyncio.get_event_loop()
        portal_task = loop.run_in_executor(None, lambda: search_agent.execute_search(portal_log))
        tg_task = loop.run_in_executor(None, lambda: telegram_agent.collect_jobs(telegram_log))

        portal_jobs, tg_jobs = await asyncio.gather(portal_task, tg_task)
        raw_jobs = portal_jobs + tg_jobs

        log_cb(f"Aggregated {len(portal_jobs)} portal jobs and {len(tg_jobs)} Telegram jobs. Verifying...", "info")
        
        verification_agent = VerificationAgent(raw_jobs)
        verified_jobs = verification_agent.verify_and_deduplicate(lambda m, s="info": log_cb(f"[Verification] {m}", s))
        
        return verified_jobs
