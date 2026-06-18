"""
Salary Agent — estimates job salary bands and generates salary negotiation scripts.
"""
import logging
from app.services.orchestrator import call_gemini

logger = logging.getLogger("app.agents.salary")


class SalaryAgent:
    def estimate_band(self, job_title: str, experience: str, location: str) -> dict:
        """Estimates the salary band based on market ranges."""
        prompt = f"""
        Estimate the salary band for:
        Job Title: {job_title}
        Required Experience: {experience}
        Location: {location}
        
        Provide the output in 1 sentence detailing the estimated range in LPA (Lakhs Per Annum) for India or USD for remote.
        """
        response = call_gemini(prompt)
        if not response:
            response = "Estimated range: 12 - 18 LPA based on market standards."
        return {"estimated_range": response.strip()}

    def generate_negotiation_script(self, offered_salary: str, target_salary: str, company: str) -> str:
        """Generates a polite negotiation script to request target compensation."""
        prompt = f"""
        Write a polite, professional negotiation email script:
        Company: {company}
        Offered Salary: {offered_salary}
        Target Salary: {target_salary}
        
        Focus on expressing excitement about the role while professional requesting a salary match. Keep it under 150 words.
        """
        response = call_gemini(prompt)
        if not response:
            response = "Dear Team,\n\nThank you for the offer. I am thrilled about the opportunity. Given my skills and market standards, I was hoping we could explore a range closer to our target. Thank you."
        return response.strip()
