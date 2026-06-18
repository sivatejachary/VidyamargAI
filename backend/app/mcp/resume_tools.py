"""
Resume MCP Server — tools for AI to access resume data.
"""
import json
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.mcp.base import BaseMCPServer
from app.models.models import Candidate, CandidateResume, CandidateProfile

logger = logging.getLogger("app.mcp.resume")


class ResumeMCPServer(BaseMCPServer):
    required_permission = "read"
    server_name = "ResumeMCP"

    def get_resume(self, candidate_id: int, db: Session) -> dict:
        """Returns the candidate's latest parsed resume text and structured sections."""
        self._log_call("get_resume", candidate_id)
        profile = db.query(CandidateProfile).filter(
            CandidateProfile.candidate_id == candidate_id
        ).order_by(CandidateProfile.created_at.desc()).first()
        cand = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not cand:
            return {"error": "Candidate not found"}
        parsed_meta = {}
        if profile and profile.parsed_metadata:
            try:
                parsed_meta = json.loads(profile.parsed_metadata)
            except Exception:
                pass
        return {
            "resume_text": profile.resume_text[:3000] if profile and profile.resume_text else "",
            "summary": cand.summary or "",
            "skills": cand.skills or "",
            "experience": cand.experience or "",
            "education": cand.education or "",
            "projects": cand.projects or "",
            "certifications": cand.certifications or "",
            "languages": cand.languages or "",
            "parsed_meta": parsed_meta,
        }

    def get_ats_score(self, candidate_id: int, db: Session) -> dict:
        """Returns the latest ATS analysis score and suggestions."""
        self._log_call("get_ats_score", candidate_id)
        profile = db.query(CandidateProfile).filter(
            CandidateProfile.candidate_id == candidate_id
        ).order_by(CandidateProfile.created_at.desc()).first()
        if not profile or not profile.parsed_metadata:
            return {"ats_score": None, "message": "No resume analyzed yet"}
        try:
            meta = json.loads(profile.parsed_metadata)
            return {
                "ats_score": meta.get("ats_score"),
                "completeness": meta.get("completeness"),
                "missing_keywords": meta.get("missing_keywords", []),
                "suggestions": meta.get("suggestions", []),
                "strengths": meta.get("strengths", []),
                "improvements": meta.get("improvements", []),
            }
        except Exception:
            return {"ats_score": None, "message": "Could not parse analysis"}

    def get_resume_versions(self, candidate_id: int, db: Session) -> list:
        """Returns all uploaded resume versions with upload dates."""
        self._log_call("get_resume_versions", candidate_id)
        resumes = db.query(CandidateResume).filter(
            CandidateResume.candidate_id == candidate_id
        ).order_by(CandidateResume.uploaded_at.desc()).all()
        return [
            {"id": r.id, "url": r.resume_url, "uploaded_at": r.uploaded_at.isoformat()}
            for r in resumes
        ]

    def get_profile_completeness(self, candidate_id: int, db: Session) -> dict:
        """Returns profile completeness score and missing sections."""
        self._log_call("get_profile_completeness", candidate_id)
        cand = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not cand:
            return {"score": 0, "missing": []}
        fields = {
            "summary": cand.summary,
            "skills": cand.skills,
            "experience": cand.experience,
            "education": cand.education,
            "projects": cand.projects,
            "phone": cand.phone,
            "linkedin": cand.linkedin,
            "github": cand.github,
        }
        filled = sum(1 for v in fields.values() if v)
        total = len(fields)
        missing = [k for k, v in fields.items() if not v]
        return {
            "score": round((filled / total) * 100),
            "filled": filled,
            "total": total,
            "missing_sections": missing,
        }

    def get_improvement_tips(self, candidate_id: int, db: Session) -> list:
        """Returns AI-generated improvement tips from the latest analysis."""
        self._log_call("get_improvement_tips", candidate_id)
        ats = self.get_ats_score(candidate_id, db)
        tips = []
        if ats.get("suggestions"):
            tips.extend(ats["suggestions"][:5])
        if ats.get("improvements"):
            tips.extend(ats["improvements"][:3])
        completeness = self.get_profile_completeness(candidate_id, db)
        for section in completeness.get("missing_sections", [])[:3]:
            tips.append(f"Add your {section} to improve profile completeness")
        return tips[:8]


resume_mcp = ResumeMCPServer()
