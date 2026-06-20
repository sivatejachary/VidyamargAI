"""
Screening Answer Engine — Answers ATS screening questions using LLM + rule-based extraction.
Covers both factual questions (salary/notice/experience) and open-ended questions.
Accepts cover letter text as context for coherent cross-referencing.
"""
import re
import hashlib
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Factual question patterns → rule-based extraction from candidate profile
_FACTUAL_PATTERNS = [
    (r"(notice\s+period|availability|when\s+can\s+you\s+start)", "notice_period"),
    (r"(salary|compensation|expected\s+ctc|expected\s+pay|expected\s+salary)", "salary"),
    (r"(years\s+of\s+experience|how\s+many\s+years|total\s+experience)", "experience"),
    (r"(current\s+(ctc|salary|compensation))", "current_salary"),
    (r"(linkedin|portfolio|github|website|url)", "links"),
    (r"(willing\s+to\s+relocate|open\s+to\s+relocation)", "relocation"),
    (r"(remote|hybrid|on.?site|work\s+from\s+home)", "work_mode"),
]


class ScreeningAnswerEngine:
    """
    Answers screening questions using:
    1. Rule-based extraction for factual questions (no LLM needed)
    2. LLM chain (Gemini → NVIDIA NIM → template) for open-ended questions
    3. Cache per (candidate_id, task_id, question_hash)
    """

    def answer(
        self,
        question: str,
        profile: dict,
        job: dict,
        db: Session,
        candidate_id: Optional[int] = None,
        task_id: Optional[int] = None,
        cover_letter_text: Optional[str] = None
    ) -> str:
        """
        Returns best answer for the screening question.
        cover_letter_text is used as context for consistent LLM responses.
        """
        q_hash = hashlib.sha256(question.strip().lower().encode()).hexdigest()

        # Check cache
        if candidate_id:
            cached = self._get_cached(candidate_id, q_hash, db)
            if cached:
                return cached

        # Route: factual vs open-ended
        factual_type = self._classify_factual(question)
        if factual_type:
            answer = self._rule_based_answer(factual_type, profile)
        else:
            answer = self._llm_answer(question, profile, job, cover_letter_text)

        # Cache
        if candidate_id:
            self._cache_answer(candidate_id, task_id, q_hash, question, answer, db)

        return answer

    def _classify_factual(self, question: str) -> Optional[str]:
        q_lower = question.lower()
        for pattern, qtype in _FACTUAL_PATTERNS:
            if re.search(pattern, q_lower):
                return qtype
        return None

    def _rule_based_answer(self, qtype: str, profile: dict) -> str:
        if qtype == "notice_period":
            return profile.get("notice_period") or "Immediately available / 30 days notice."
        if qtype == "experience":
            yrs = profile.get("experience_years", 0)
            return f"{yrs} years"
        if qtype == "salary":
            s = profile.get("expected_salary") or profile.get("salary_expectation")
            return str(s) if s else "Open to discussion based on industry standards."
        if qtype == "current_salary":
            s = profile.get("current_salary")
            return str(s) if s else "As per industry standards."
        if qtype == "links":
            parts = []
            if profile.get("linkedin"): parts.append(f"LinkedIn: {profile['linkedin']}")
            if profile.get("github"): parts.append(f"GitHub: {profile['github']}")
            if profile.get("portfolio"): parts.append(f"Portfolio: {profile['portfolio']}")
            return " | ".join(parts) if parts else "Available upon request."
        if qtype == "relocation":
            return "Yes, open to relocation." if profile.get("open_to_relocation") else "Prefer remote or current location."
        if qtype == "work_mode":
            return profile.get("preferred_work_mode") or "Open to remote, hybrid, or on-site."
        return "Yes."

    def _llm_answer(self, question: str, profile: dict, job: dict, cover_letter_text: Optional[str]) -> str:
        from app.services.orchestrator import call_gemini, call_nvidia
        skills = ", ".join((profile.get("skills") or [])[:8])
        ctx = f"\nCover letter context: {cover_letter_text[:300]}" if cover_letter_text else ""
        prompt = f"""Answer this job application screening question briefly and professionally.

Question: {question}

Candidate profile:
- Skills: {skills}
- Experience: {profile.get('experience_years', 0)} years
- Domain: {profile.get('domain', 'Technology')}

Job: {job.get('title', '')} at {job.get('company', '')}{ctx}

Answer in 1-3 sentences. Be specific and confident. Do not start with 'I would'."""

        try:
            result = call_gemini(prompt)
            if result and len(result) > 5:
                return result.strip()
        except Exception:
            pass
        try:
            result = call_nvidia(prompt)
            if result and len(result) > 5:
                return result.strip()
        except Exception:
            pass
        return f"With {profile.get('experience_years', 0)} years of experience in {profile.get('domain', 'technology')}, I am well-suited for this role."

    def _get_cached(self, candidate_id: int, q_hash: str, db: Session) -> Optional[str]:
        try:
            from app.models.auto_apply_models import ApplicationAnswer
            entry = db.query(ApplicationAnswer).filter(
                ApplicationAnswer.candidate_id == candidate_id,
                ApplicationAnswer.question_hash == q_hash
            ).order_by(ApplicationAnswer.created_at.desc()).first()
            return entry.answer_text if entry else None
        except Exception:
            return None

    def _cache_answer(self, candidate_id: int, task_id: Optional[int], q_hash: str,
                      question: str, answer: str, db: Session) -> None:
        try:
            from app.models.auto_apply_models import ApplicationAnswer
            entry = ApplicationAnswer(
                candidate_id=candidate_id,
                task_id=task_id,
                question_hash=q_hash,
                question_text=question[:1000],
                answer_text=answer,
                created_at=datetime.utcnow()
            )
            db.add(entry)
            db.commit()
        except Exception as e:
            logger.warning(f"Could not cache screening answer: {e}")


# Module-level singleton
screening_answer_engine = ScreeningAnswerEngine()