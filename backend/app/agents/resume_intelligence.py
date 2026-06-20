import json
import logging
from typing import List, Optional
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from app.models.models import Candidate

logger = logging.getLogger(__name__)

class CandidateProfileData(BaseModel):
    skills: List[str]
    experience_years: float
    education: Optional[str] = ""
    projects: Optional[str] = ""
    certifications: List[str] = []
    summary: Optional[str] = ""
    domain: Optional[str] = "Software Engineering"
    confidence: Optional[int] = 85
    subdomains: List[str] = []
    preferred_roles: List[str] = []
    career_level: Optional[str] = "Mid-level"
    locations: List[str] = []

    @field_validator("skills", "certifications", "subdomains", "preferred_roles", "locations", mode="before")
    @classmethod
    def coerce_string_to_list(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        if v is None:
            return []
        return v



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

        # Try loading prebuilt profile from CandidateProfile table first
        from app.models.models import CandidateProfile
        profile_obj = self.db.query(CandidateProfile).filter(CandidateProfile.candidate_id == self.candidate_id).order_by(CandidateProfile.created_at.desc()).first()
        if profile_obj and profile_obj.parsed_metadata:
            try:
                meta = json.loads(profile_obj.parsed_metadata)
                if isinstance(meta, dict) and "skills" in meta:
                    logger.info("ResumeIntelligenceAgent: Loaded prebuilt CandidateProfile from database.")
                    return CandidateProfileData(
                        skills=meta.get("skills", []),
                        experience_years=meta.get("experience_years", 0.0),
                        education=meta.get("education", ""),
                        projects=meta.get("projects", "[]"),
                        certifications=meta.get("certifications", []),
                        summary=meta.get("summary", ""),
                        domain=meta.get("domain", "Software Engineering"),
                        confidence=meta.get("confidence", 85),
                        subdomains=meta.get("subdomains", []),
                        preferred_roles=meta.get("preferred_roles", []),
                        career_level=meta.get("career_level", "Mid-level"),
                        locations=meta.get("locations", [])
                    )
            except Exception as e:
                logger.error(f"Error parsing cached candidate profile: {e}")

        # Fallback if no prebuilt profile exists
        skills_list = []
        if candidate.skills:
            skills_list = [s.strip() for s in candidate.skills.split(",") if s.strip()]

        certs_list = []
        if candidate.certifications:
            certs_list = [c.strip() for c in candidate.certifications.split(",") if c.strip()]

        from app.api.endpoints import calculate_years_from_experience
        exp_years = calculate_years_from_experience(candidate.experience)

        from app.services.orchestrator import classify_candidate_domain
        domain_info = classify_candidate_domain(skills_list, candidate.summary or "")

        locations = []
        if candidate.address:
            locations = [candidate.address]

        profile = CandidateProfileData(
            skills=skills_list if skills_list else ["Python", "JavaScript", "React", "SQL"],
            experience_years=exp_years,
            education=candidate.education or "",
            projects=candidate.projects or "[]",
            certifications=certs_list,
            summary=candidate.summary or "",
            domain=domain_info["domain"],
            confidence=domain_info["confidence"],
            subdomains=domain_info["subdomains"],
            preferred_roles=domain_info["preferred_roles"],
            career_level=domain_info["career_level"],
            locations=locations
        )
        logger.info(f"ResumeIntelligenceAgent: Extracted {len(profile.skills)} skills, {profile.experience_years} years of experience")
        return profile

