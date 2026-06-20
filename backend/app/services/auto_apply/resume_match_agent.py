"""
Resume Match Agent — Scores each resume version against a job using LLM.
Keyword pre-filter eliminates obviously wrong types before calling LLM.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Keyword pre-filter map: resume_type → trigger keywords
_TYPE_KEYWORDS = {
    "ai": ["machine learning", "deep learning", "llm", "nlp", "ai", "artificial intelligence", "neural", "transformer"],
    "ml": ["machine learning", "ml engineer", "mlops", "model training", "feature engineering"],
    "ds": ["data science", "data analyst", "analytics", "statistics", "sql", "tableau", "power bi"],
    "swe": ["backend", "api", "fastapi", "django", "flask", "microservices", "devops", "cloud", "kubernetes"],
}


@dataclass
class ResumeScore:
    resume_id: int
    resume_type: str
    score: float       # 0–100
    reason: str


class ResumeMatchAgent:
    """
    Selects the best resume version for a job using LLM scoring.
    Falls back to keyword matching then most-recent-resume if LLM fails.
    """

    def score_all(self, candidate_id: int, job: dict, db: Session) -> List[ResumeScore]:
        """
        Returns sorted list of ResumeScore (highest score first).
        The first entry should be selected for the application.
        """
        from app.models.models import CandidateResume
        resumes = db.query(CandidateResume).filter(
            CandidateResume.candidate_id == candidate_id
        ).order_by(CandidateResume.uploaded_at.desc()).all()

        if not resumes:
            return []

        if len(resumes) == 1:
            return [ResumeScore(
                resume_id=resumes[0].id,
                resume_type=getattr(resumes[0], "resume_type", "general") or "general",
                score=75.0,
                reason="Only one resume version available."
            )]

        # Step 1: Keyword pre-filter — identify best type from job text
        job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
        type_scores: dict[str, float] = {}
        for rtype, keywords in _TYPE_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in job_text)
            if hits > 0:
                type_scores[rtype] = hits / len(keywords) * 100

        # Step 2: Try LLM scoring for each resume
        scores = []
        for resume in resumes:
            rtype = getattr(resume, "resume_type", "general") or "general"
            keyword_boost = type_scores.get(rtype, 0) * 0.3  # 30% weight
            llm_score, reason = self._llm_score(resume, job)
            final_score = min(100.0, llm_score * 0.7 + keyword_boost)
            scores.append(ResumeScore(
                resume_id=resume.id,
                resume_type=rtype,
                score=round(final_score, 1),
                reason=reason
            ))

        scores.sort(key=lambda s: s.score, reverse=True)
        return scores

    def _llm_score(self, resume, job: dict):
        """Call LLM chain to score resume vs job. Returns (score, reason)."""
        from app.services.orchestrator import call_gemini, call_nvidia
        import json
        rtype = getattr(resume, "resume_type", "general") or "general"
        prompt = f"""Score this resume type for the given job from 0 to 100. Be concise.

Job Title: {job.get('title', '')}
Job Description (first 300 chars): {str(job.get('description', ''))[:300]}
Resume Type: {rtype}
Resume Skills Focus: {rtype.upper()} domain

Return JSON: {{"score": <0-100>, "reason": "<one sentence>"}}"""
        try:
            raw = call_gemini(prompt, json_mode=True)
            if raw:
                data = json.loads(raw)
                return float(data.get("score", 50)), data.get("reason", "LLM scored.")
        except Exception:
            pass
        try:
            raw = call_nvidia(prompt)
            if raw:
                import re
                m = re.search(r'\{.*?\}', raw, re.DOTALL)
                if m:
                    data = json.loads(m.group())
                    return float(data.get("score", 50)), data.get("reason", "NVIDIA scored.")
        except Exception:
            pass
        # Heuristic fallback
        rtype = getattr(resume, "resume_type", "general") or "general"
        job_title_lower = job.get("title", "").lower()
        score = 60.0
        if rtype == "general":
            score = 55.0
        elif any(kw in job_title_lower for kw in _TYPE_KEYWORDS.get(rtype, [])):
            score = 75.0
        return score, f"Heuristic score for {rtype} resume."


# Module-level singleton
resume_match_agent = ResumeMatchAgent()