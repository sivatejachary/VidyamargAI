import json
import logging
from typing import Dict, Any
from packages.model_client.client import AppAIClient

logger = logging.getLogger("ai_os.reflection.reflection")

class ReflectionEngine:
    """
    Evaluates execution outcomes against user objectives to check goals completion status.
    """
    def __init__(self, ai_client: AppAIClient):
        self.ai = ai_client

    async def evaluate_progress(self, user_goal: str, blackboard_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Queries Groq to evaluate if the current blackboard variables satisfy user's goal parameters.
        """
        logger.info(f"Reflecting on blackboard outcomes for goal: '{user_goal}'")
        
        prompt = (
            f"User Target Career Goal: '{user_goal}'\n\n"
            f"Current Blackboard State Variables: {blackboard_state.get('variables', {})}\n"
            f"Verified Blackboard Facts: {blackboard_state.get('facts', [])}\n"
            f"Assumptions: {blackboard_state.get('assumptions', [])}\n"
        )

        system_prompt = (
            "You are the Reflection Engine of VidyaMarg AI.\n"
            "Analyze the execution context and state variables to determine if the candidate's career goal is complete.\n"
            "Return a JSON object containing:\n"
            "1. 'is_completed': Boolean indicating if the main goal is satisfied.\n"
            "2. 'gaps_identified': List of missing skills, projects, or applications that remain unresolved.\n"
            "3. 'critique': Structured explanation of what needs adjustment in the plan.\n"
            "4. 'recommended_adjustments': List of new sub-tasks or parameter corrections.\n\n"
            "Respond ONLY with raw JSON."
        )

        response_text = await self.ai.get_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=True,
            temperature=0.1
        )

        try:
            parsed_reflection = json.loads(response_text)
            logger.info(f"Reflection complete. Goal Completed: {parsed_reflection.get('is_completed')}")
            return parsed_reflection
        except Exception as e:
            logger.error(f"Reflection Engine failed to parse model JSON: {e}. Response was: '{response_text}'")
            return {
                "is_completed": False,
                "gaps_identified": ["Error parsing reflection"],
                "critique": "Failed to analyze state variables",
                "recommended_adjustments": []
            }
