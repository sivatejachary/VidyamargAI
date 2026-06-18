"""
Application Agent — handles job application forms, cover letters, and raises OTP/CAPTCHA blocker alerts.
"""
import logging
from app.services.orchestrator import call_gemini
from app.services.human_action_queue import HumanActionRequired

logger = logging.getLogger("app.agents.application")


class ApplicationAgent:
    def apply(self, candidate_id: int, job: dict) -> dict:
        """
        Attempts to apply for a job. Raises HumanActionRequired if it hits a blocker.
        """
        apply_url = job.get("apply_url", "")
        # OTP / CAPTCHA simulator for demonstration
        if apply_url and ("google" in apply_url.lower() or "form" in apply_url.lower()):
            raise HumanActionRequired(
                action_type="captcha",
                title=f"Google CAPTCHA Needed for {job['company']}",
                description=f"Our autonomous agent is blocked by a CAPTCHA while applying for '{job['title']}'. Please solve it to continue.",
                payload={"url": apply_url, "job_id": job["id"]}
            )
            
        return {"status": "success", "message": "Applied successfully"}

    def generate_cover_letter(self, profile, job: dict) -> str:
        """Generates a customized, professional cover letter."""
        prompt = f"""
        Write a professional 200-word cover letter for this candidate:
        Skills: {', '.join(profile.skills)}
        Experience: {profile.experience_years} years
        
        For this job:
        Title: {job['title']}
        Company: {job['company']}
        Description: {job['description'][:300]}
        
        Keep it direct, compelling, and highlighting relevant skills.
        """
        response = call_gemini(prompt)
        if not response:
            response = "Dear Hiring Team,\n\nI am excited to apply for the position. My skills match your requirements perfectly.\n\nBest regards."
        return response
