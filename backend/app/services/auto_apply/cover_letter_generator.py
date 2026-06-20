"""
Cover Letter Generator — LLM-powered cover letter generation with caching.
Gemini → NVIDIA NIM → local template fallback.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_LOCAL_TEMPLATE = """Dear Hiring Team,

I am excited to apply for the {title} position at {company}. With {years} years of experience
in {domain}, I bring the skills and dedication your team requires.

I look forward to contributing to {company}'s mission and am confident my background aligns
with this opportunity.

Best regards."""


class CoverLetterGenerator:
    """
    Generates tailored cover letters for each (candidate, task).
    Results are cached in ApplicationCoverLetter — idempotent on retry.
    """

    def generate(self, candidate_profile: dict, job: dict, task_id: int, db: Session) -> str:
        """
        Returns cover letter text. Checks cache first, then calls LLM.
        """
        from app.models.auto_apply_models import ApplicationCoverLetter

        # Check cache
        existing = db.query(ApplicationCoverLetter).filter_by(task_id=task_id).first()
        if existing:
            return existing.content

        content, provider = self._generate_content(candidate_profile, job)

        # Cache result
        try:
            letter = ApplicationCoverLetter(
                candidate_id=candidate_profile.get("candidate_id", 0),
                task_id=task_id,
                job_title=job.get("title", ""),
                company=job.get("company", ""),
                content=content,
                provider=provider,
                created_at=datetime.utcnow()
            )
            db.add(letter)
            db.commit()
        except Exception as e:
            logger.warning(f"Could not cache cover letter for task {task_id}: {e}")

        return content

    def _generate_content(self, candidate_profile: dict, job: dict):
        from app.services.orchestrator import call_gemini, call_nvidia
        skills = ", ".join((candidate_profile.get("skills") or [])[:6])
        prompt = f"""Write a professional, concise 180-word cover letter for this candidate:
- Name: {candidate_profile.get('name', 'Candidate')}
- Skills: {skills}
- Experience: {candidate_profile.get('experience_years', 0)} years
- Domain: {candidate_profile.get('domain', 'Technology')}

For this job:
- Title: {job.get('title', '')}
- Company: {job.get('company', '')}
- Description (first 200 chars): {str(job.get('description', ''))[:200]}

Tone: professional, confident, specific. No generic filler. Start directly."""

        # Gemini
        try:
            result = call_gemini(prompt)
            if result and len(result) > 50:
                return result.strip(), "gemini"
        except Exception:
            pass

        # NVIDIA NIM
        try:
            result = call_nvidia(prompt)
            if result and len(result) > 50:
                return result.strip(), "nvidia"
        except Exception:
            pass

        # Local template fallback
        content = _LOCAL_TEMPLATE.format(
            title=job.get("title", "the position"),
            company=job.get("company", "your company"),
            years=candidate_profile.get("experience_years", 0),
            domain=candidate_profile.get("domain", "technology")
        )
        return content, "template"


# Module-level singleton
cover_letter_generator = CoverLetterGenerator()