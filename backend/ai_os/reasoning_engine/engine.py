import json
import logging
from typing import Dict, Any, Optional
from packages.model_client.client import AppAIClient

logger = logging.getLogger("ai_os.reasoning_engine.engine")

class ReasoningEngine:
    """
    Coordinates reasoning prompts and structured chain-of-thought evaluations.
    """
    def __init__(self, ai_client: AppAIClient):
        self.ai = ai_client

    async def execute_reasoning_step(self, system_prompt: str, user_query: str) -> Dict[str, Any]:
        """
        Queries Llama model with active context and query, returning the logical next step.
        """
        logger.info("Initiating reasoning step evaluation loop...")
        
        reasoning_instructions = (
            "You are the Reasoning Engine of VidyaMarg AI. Your goal is to guide the candidate's career track.\n"
            "Analyze the Blackboard state and the user query to decide the next logical step.\n"
            "Format your response as a JSON object with the following fields:\n"
            "1. 'thought': Explain your reasoning steps and assumptions.\n"
            "2. 'action': Specify what action to take: 'CALL_TOOL', 'WAIT_FOR_INPUT', or 'COMPLETE_GOAL'.\n"
            "3. 'target_tool': If action is 'CALL_TOOL', provide the exact name of the tool to execute.\n"
            "4. 'arguments': If action is 'CALL_TOOL', specify the arguments mapping for the tool.\n"
            "5. 'response_message': If action is 'COMPLETE_GOAL' or 'WAIT_FOR_INPUT', provide the message text to show the user.\n\n"
            "Respond ONLY with raw JSON."
        )

        full_system_prompt = f"{system_prompt}\n\n{reasoning_instructions}"
        
        response_text = await self.ai.get_completion(
            prompt=user_query,
            system_prompt=full_system_prompt,
            json_mode=True,
            temperature=0.2
        )

        try:
            parsed_reasoning = json.loads(response_text)
            logger.info(f"Reasoning complete. Thought: '{parsed_reasoning.get('thought')[:60]}...', Action: '{parsed_reasoning.get('action')}'")
            return parsed_reasoning
        except Exception as e:
            logger.error(f"Reasoning Engine failed to parse model JSON completion: {e}. Output was: '{response_text}'")
            return {
                "thought": "Error parsing output",
                "action": "WAIT_FOR_INPUT",
                "response_message": "I encountered an error processing your query. Could you please rephrase?"
            }
