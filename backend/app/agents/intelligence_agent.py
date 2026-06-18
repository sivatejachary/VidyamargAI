"""
Intelligence Agent — generates company research briefs, salary benchmarks, and interview questions.
Utilizes LLM services and external query tools.
"""
import logging
from sqlalchemy.orm import Session
from app.mcp.servers import LLMServer

logger = logging.getLogger("app.agents.intelligence")


class IntelligenceAgent:
    
    def generate_company_brief(self, user_id: int, company_name: str, db: Session) -> str:
        """Fetches and caches high-level company profile data."""
        prompt = f"Provide a brief 100-word company research brief including founding, tech stack, and recent news for '{company_name}'."
        llm = LLMServer()
        res = llm.generate(user_id, {"prompt": prompt}, db)
        return res.get("response", "Research unavailable.")

    def benchmark_salary(self, role: str, location: str, experience: str) -> Dict[str, Any]:
        """Provides salary benchmark predictions."""
        # Simple simulated database statistics
        return {
            "median": "₹16 LPA",
            "range": "₹12–22 LPA",
            "advice": "Market supports up to ₹20 LPA for mid-level candidates."
        }

    def generate_interview_prep(self, user_id: int, company: str, role: str, db: Session) -> Dict[str, Any]:
        """Generates STAR answers, checklists, and question bank."""
        prompt = f"Generate 5 interview questions and STAR answer outlines for a '{role}' position at '{company}'."
        llm = LLMServer()
        res = llm.generate(user_id, {"prompt": prompt}, db)
        return {
            "questions": res.get("response", "Question prep unavailable."),
            "checklist": ["Research company history", "Prepare questions for interviewer", "Review technical portfolio"]
        }
