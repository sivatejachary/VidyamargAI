import logging
from typing import List, Dict, Any
from ..schemas.goal import GoalStatus

logger = logging.getLogger("ai_os.planner.planner")

class Planner:
    """
    Translates user intents and parameters into structured subgoal definitions.
    """
    def __init__(self):
        pass

    async def plan_subgoals(self, intent: str, entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Creates a list of subgoals to execute based on intent.
        """
        logger.info(f"Generating execution subgoal plan for intent: '{intent}'")
        
        subgoals = []
        
        if intent == "INGEST_RESUME":
            subgoals = [
                {
                    "id": "extract_resume_text",
                    "name": "Extract Resume Text",
                    "description": "Read uploaded PDF bytes and extract raw text",
                    "weight": 1.0,
                    "dependencies": []
                },
                {
                    "id": "parse_resume_json",
                    "name": "Parse Resume structured JSON",
                    "description": "Query Groq API to extract skills, experience, and education",
                    "weight": 1.5,
                    "dependencies": ["extract_resume_text"]
                },
                {
                    "id": "upsert_candidate_profile",
                    "name": "Update Candidate Profile",
                    "description": "Save structural profile updates to Postgres and index vectors in Qdrant",
                    "weight": 2.0,
                    "dependencies": ["parse_resume_json"]
                }
            ]
        elif intent == "SEARCH_JOBS":
            role = entities.get("role", "Software Engineer")
            location = entities.get("location", "")
            subgoals = [
                {
                    "id": "fetch_candidate_skills",
                    "name": "Fetch Candidate Skills",
                    "description": "Retrieve candidate skills and preferences from profile memory",
                    "weight": 1.0,
                    "dependencies": []
                },
                {
                    "id": "discover_jobs",
                    "name": "Discover Target Jobs",
                    "description": f"Query database for {role} job listings in {location or 'any location'}",
                    "weight": 2.0,
                    "dependencies": ["fetch_candidate_skills"]
                },
                {
                    "id": "calculate_job_matches",
                    "name": "Calculate Job Matches",
                    "description": "Rank discovered job matches using Qdrant vector similarity scoring",
                    "weight": 1.5,
                    "dependencies": ["discover_jobs"]
                }
            ]
        elif intent == "SCHEDULE_TASK":
            subgoals = [
                {
                    "id": "register_cron_trigger",
                    "name": "Register Cron Trigger",
                    "description": "Add recurring task schedule to the database",
                    "weight": 1.0,
                    "dependencies": []
                }
            ]
        else: # Default GENERAL_CHAT / advice plan
            subgoals = [
                {
                    "id": "generate_career_advice",
                    "name": "Generate Career Advice",
                    "description": "Formulate advice response based on candidate context",
                    "weight": 1.0,
                    "dependencies": []
                }
            ]

        logger.info(f"Subgoals plan compiled. Total nodes: {len(subgoals)}")
        return subgoals
