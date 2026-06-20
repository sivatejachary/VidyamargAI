import logging
import json
import re
from typing import List, Tuple, Dict, Any
from app.agents.resume_intelligence import CandidateProfileData
from app.services.job_connectors.base import LiveJob
from app.agents.matching_agent import calculate_match_score_and_reasons

logger = logging.getLogger(__name__)

class MatchingAgent:
    def __init__(self, profile: CandidateProfileData):
        self.profile = profile

    def match_job(self, job: LiveJob) -> Dict[str, Any]:
        """
        Calculates compatibility score based on candidate resume vs job posting.
        Formula:
          Role (40%) + Skills (25%) + Experience (20%) + Education (10%) + Certifications (5%)
        """
        res = calculate_match_score_and_reasons(
            profile=self.profile,
            job_title=job.title,
            job_description=job.description,
            job_skills_list=job.skills,
            job_experience_str=job.experience
        )
        
        return {
            "match_score": res["match_score"],
            "matched_skills": res["matched_skills"],
            "missing_skills": res["missing_skills"],
            "reasoning": " ".join(res["reasons"]),
            "skills_score": res["skills_score"],
            "exp_score": res["exp_score"],
            "proj_score": res["cert_score"],  # Map certification score to project score placeholder
            "edu_score": res["edu_score"]
        }
