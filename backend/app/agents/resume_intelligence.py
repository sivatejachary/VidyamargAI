import json
import logging
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.models.models import Candidate

logger = logging.getLogger(__name__)

class CandidateProfileData(BaseModel):
    skills: List[str]
    experience_years: float
    education: Optional[str] = ""
    projects: Optional[str] = ""
    certifications: List[str] = []
    summary: Optional[str] = ""


class ResumeIntelligenceAgent:
    def __init__(self, db: Session, candidate_id: int):
        self.db = db
        self.candidate_id = candidate_id

    def extract_profile(self) -> CandidateProfileData:
        """
        Loads the candidate from DB and extracts structured profile details.
        """
        candidate = self.db.query(Candidate).filter(Candidate.id == self.candidate_id).first()
        if not candidate:
            logger.warning(f"Candidate {self.candidate_id} not found, using default profile")
            return CandidateProfileData(
                skills=["Python", "JavaScript", "React", "SQL"],
                experience_years=1.0,
                education="B.Tech in Computer Science",
                projects="[]",
                certifications=[],
                summary=""
            )

        # 1. Extract skills
        skills_list = []
        if candidate.skills:
            skills_list = [s.strip() for s in candidate.skills.split(",") if s.strip()]

        # 2. Extract certifications
        certs_list = []
        if candidate.certifications:
            certs_list = [c.strip() for c in candidate.certifications.split(",") if c.strip()]

        # 3. Calculate experience years using our smart calculation
        from backend.app.api.endpoints import calculate_years_from_experience
        exp_years = calculate_years_from_experience(candidate.experience)

        profile = CandidateProfileData(
            skills=skills_list if skills_list else ["Python", "JavaScript", "React", "SQL"],
            experience_years=exp_years,
            education=candidate.education or "",
            projects=candidate.projects or "[]",
            certifications=certs_list,
            summary=candidate.summary or ""
        )
        logger.info(f"ResumeIntelligenceAgent: Extracted {len(profile.skills)} skills, {profile.experience_years} years of experience")
        return profile
