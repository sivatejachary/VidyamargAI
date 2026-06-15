import logging
import json
import re
from typing import List, Tuple, Dict, Any
from backend.app.agents.resume_intelligence import CandidateProfileData
from backend.app.services.job_connectors.base import LiveJob
from backend.app.services.match_engine import _parse_years

logger = logging.getLogger(__name__)

class MatchingAgent:
    def __init__(self, profile: CandidateProfileData):
        self.profile = profile

    def match_job(self, job: LiveJob) -> Dict[str, Any]:
        """
        Calculates compatibility score based on candidate resume vs job posting.
        Formula:
          Match Score = (Skills * 0.60) + (Experience * 0.20) + (Project * 0.10) + (Education * 0.10)
        
        Returns a dictionary containing Match Score, Matched Skills, Missing Skills, and Reasoning.
        """
        cand_skills_lower = [s.lower().strip() for s in self.profile.skills]
        job_skills = job.skills or []

        # 1. Skills Match Score (60%)
        matched_skills = []
        missing_skills = []
        if job_skills:
            for js in job_skills:
                js_l = js.lower().strip()
                # Check exact or fuzzy matching (substring match in candidate skills)
                found = any(js_l in cs or cs in js_l for cs in cand_skills_lower)
                if found:
                    matched_skills.append(js)
                else:
                    missing_skills.append(js)
            skills_score = (len(matched_skills) / len(job_skills)) * 100.0
        else:
            # If job specifies no skills, assume neutral 80% matching
            skills_score = 80.0

        # 2. Experience Match Score (20%)
        req_years = _parse_years(job.experience)
        cand_years = self.profile.experience_years
        
        if req_years == 0:  # Fresher/Intern role
            exp_score = 100.0 if cand_years <= 2.0 else 80.0  # slightly overqualified
        else:
            diff = cand_years - req_years
            if diff >= 0:
                exp_score = 100.0 if diff <= 2.0 else 90.0
            elif diff == -1.0:
                exp_score = 75.0
            elif diff == -2.0:
                exp_score = 50.0
            else:
                exp_score = 25.0

        # 3. Project Relevance Score (10%)
        proj_score = 50.0
        projects_str = self.profile.projects or ""
        if projects_str and projects_str != "[]" and job_skills:
            try:
                proj_lower = projects_str.lower()
                hits = sum(1 for s in job_skills if s.lower() in proj_lower)
                if hits >= 3:
                    proj_score = 100.0
                elif hits >= 2:
                    proj_score = 80.0
                elif hits >= 1:
                    proj_score = 65.0
            except Exception:
                pass

        # 4. Education Match Score (10%)
        edu_score = 50.0
        edu_str = self.profile.education or ""
        if edu_str:
            edu_lower = edu_str.lower()
            job_desc_lower = (job.description or "").lower()
            
            # check if job specifies education
            specifies_edu = any(kw in job_desc_lower for kw in ["degree", "bachelor", "btech", "mtech", "ms ", "b.e", "m.e"])
            if not specifies_edu:
                edu_score = 85.0
            elif any(kw in edu_lower for kw in ["b.tech", "btech", "b.e", "bachelor", "m.tech", "mtech", "m.s", "master", "mca", "bca"]):
                edu_score = 100.0
            else:
                edu_score = 60.0

        # Compute Final Weighted Match Score
        final_score = (
            (skills_score * 0.60) +
            (exp_score * 0.20) +
            (proj_score * 0.10) +
            (edu_score * 0.10)
        )
        final_score = min(100, int(round(final_score)))

        # Build reasoning explanation string
        reason_parts = []
        reason_parts.append(f"Matched {len(matched_skills)} of {len(job_skills)} required skills ({int(skills_score)}% skill match).")
        
        if req_years == 0:
            reason_parts.append(f"Experience required: Fresher (You have {cand_years} years).")
        else:
            reason_parts.append(f"Experience required: {job.experience} (You have {cand_years} years).")
            
        if proj_score >= 80.0:
            reason_parts.append("Your projects strongly align with the technologies in this role.")
        elif proj_score >= 65.0:
            reason_parts.append("Your projects mention relevant technologies used in this role.")
            
        if edu_score >= 100.0:
            reason_parts.append("Your education level fits the role requirements perfectly.")

        reasoning = " ".join(reason_parts)

        return {
            "match_score": final_score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "reasoning": reasoning,
            "skills_score": skills_score,
            "exp_score": exp_score,
            "proj_score": proj_score,
            "edu_score": edu_score
        }
