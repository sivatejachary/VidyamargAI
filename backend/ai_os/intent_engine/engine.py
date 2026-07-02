import json
import logging
from typing import Dict, Any
from packages.model_client.client import AppAIClient

logger = logging.getLogger("ai_os.intent_engine.engine")

class IntentEngine:
    """
    Parses natural language user inputs and extracts system intent and entities.
    """
    def __init__(self, ai_client: AppAIClient):
        self.ai = ai_client

    async def parse_intent(self, user_query: str) -> Dict[str, Any]:
        """
        Queries Groq to classify the input query.
        """
        logger.info(f"Classifying user intent for: '{user_query}'")
        
        system_prompt = (
            "You are the Intent Engine of VidyaMarg AI, an AI-first Career Operating System.\n"
            "Your task is to classify the user's input into one of the following system intents:\n"
            "- INGEST_RESUME: Upload, parse, or evaluate a resume.\n"
            "- SEARCH_JOBS: Discover, match, or list job recommendations.\n"
            "- BUILD_ROADMAP: Create learning roadmaps, skills gap charts, or suggest courses.\n"
            "- PREP_INTERVIEW: Start mock interviews or grade answers.\n"
            "- SCHEDULE_TASK: Schedule cron reports, automated monitoring, or reminders.\n"
            "- GENERAL_CHAT: Career advice, advice chats, or platform information.\n\n"
            "Return a JSON object containing:\n"
            "1. 'intent': The matched classification string.\n"
            "2. 'confidence': A confidence score from 0.0 to 1.0.\n"
            "3. 'entities': Extracted parameters like roles, locations, technologies, companies, or schedules.\n"
            "Respond ONLY with raw JSON."
        )

        response_text = await self.ai.get_completion(
            prompt=user_query,
            system_prompt=system_prompt,
            json_mode=True,
            temperature=0.0
        )

        try:
            parsed_result = json.loads(response_text)
            logger.info(f"Intent classified: {parsed_result.get('intent')} (Confidence: {parsed_result.get('confidence')})")
            return parsed_result
        except Exception as e:
            logger.error(f"Failed to parse Intent Engine JSON output: {e}. Output was: '{response_text}'")
            return {
                "intent": "GENERAL_CHAT",
                "confidence": 0.5,
                "entities": {}
            }
