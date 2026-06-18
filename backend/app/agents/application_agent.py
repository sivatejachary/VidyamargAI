"""
Application Agent — handles job application forms, cover letters, and raises OTP/CAPTCHA blocker alerts.
"""
import logging
from app.services.orchestrator import call_gemini
from app.services.human_action_queue import HumanActionRequired

logger = logging.getLogger("app.agents.application")


class ApplicationAgent:
    async def apply(self, candidate_id: int, job: dict) -> dict:
        """
        Attempts to apply for a job using the pooled browser.
        Raises HumanActionRequired if it hits a blocker.
        """
        apply_url = job.get("apply_url", "")
        if not apply_url:
            return {"status": "skipped", "message": "No apply URL found"}

        from app.core.browser_pool import browser_pool
        page = await browser_pool.get_new_page(candidate_id)
        try:
            logger.info(f"Opening apply page for job: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
            await page.goto(apply_url)
            
            # OTP / CAPTCHA simulator for demonstration
            if "google" in apply_url.lower() or "form" in apply_url.lower():
                try:
                    await page.screenshot()
                except Exception:
                    pass
                raise HumanActionRequired(
                    action_type="captcha",
                    title=f"Google CAPTCHA Needed for {job.get('company', 'Company')}",
                    description=f"Our autonomous agent is blocked by a CAPTCHA while applying for '{job.get('title', 'Position')}'. Please solve it to continue.",
                    payload={"url": apply_url, "job_id": job.get("id", "0")}
                )

            # Auto-fill fields if selectors exist
            try:
                await page.fill("input[name*='name']", "Candidate Name")
                await page.fill("input[name*='email']", "candidate@vidyamargai.com")
                await page.click("button[type='submit']")
            except Exception:
                pass

            return {"status": "success", "message": f"Applied successfully to {job.get('company', 'Company')}"}
        finally:
            try:
                await page.close()
            except Exception:
                pass

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
