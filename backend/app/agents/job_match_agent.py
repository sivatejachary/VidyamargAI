"""
Job Match Agent — calculates match scores and ranks jobs by relevance.
"""
import logging
from app.agents.matching import MatchingAgent
from app.agents.ranking import RankingAgent

logger = logging.getLogger("app.agents.job_match")


class JobMatchAgent:
    def __init__(self, profile):
        self.profile = profile

    def match_and_rank(self, verified_jobs: list, log_cb) -> list:
        log_cb("Calculating profile compatibility match scores...", "info")
        matching_agent = MatchingAgent(self.profile)
        
        matched_jobs = []
        for j in verified_jobs:
            match_res = matching_agent.match_job(j)
            job_dict = {
                "id": j.stable_id,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "experience": j.experience,
                "work_mode": j.work_mode,
                "skills": j.skills,
                "apply_url": j.apply_url,
                "posted_date": j.posted_date,
                "source": j.source,
                "description": j.description,
                "company_logo": j.company_logo,
                "match_score": match_res["match_score"],
                "matched_skills": match_res["matched_skills"],
                "missing_skills": match_res["missing_skills"],
                "reasoning": match_res["reasoning"],
                "verification_score": getattr(j, "verification_score", 100),
                "verification_status": getattr(j, "verification_status", "Fully Verified")
            }
            matched_jobs.append(job_dict)

        log_cb("Ranking compatibility scores...", "info")
        ranking_agent = RankingAgent(matched_jobs)
        ranked_jobs = ranking_agent.rank_jobs(lambda m, s="info": log_cb(f"[Ranking] {m}", s))
        
        return ranked_jobs
