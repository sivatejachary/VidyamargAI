"""
Company Research Agent — performs AI background research on hiring companies.
"""
import json
import logging
from app.services.orchestrator import call_gemini

logger = logging.getLogger("app.agents.company_research")


class CompanyResearchAgent:
    def research_company(self, company_name: str) -> dict:
        """Researches company details, culture, tech stack, and interview tips."""
        prompt = f"""
        Research the company "{company_name}".
        Provide a JSON response with the following keys:
        - "about": a 2-sentence description of what they do.
        - "tech_stack": list of 4 key technologies they use.
        - "culture": a brief summary of their culture or work environment.
        - "interview_tips": 2 bullet points for interviewing there.
        
        Ensure the response is strictly valid JSON format without markdown ticks.
        """
        try:
            response = call_gemini(prompt)
            if response:
                # Remove markdown wraps if present
                clean_res = response.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_res)
        except Exception as e:
            logger.error(f"Error researching company {company_name}: {e}")
            
        return {
            "about": f"{company_name} is a leading player in its market segment.",
            "tech_stack": ["React", "Python", "Cloud Infrastructure"],
            "culture": "Collaborative, remote-first, growth-oriented.",
            "interview_tips": ["Be ready to discuss core engineering values.", "Highlight past team projects."]
        }
