import json
import logging
from typing import Dict, Any
from .prompt import RESUME_EXTRACTION_PROMPT
from .schemas import ResumeProfileSchema
from ...registry.agent_registry import agent_registry
from ...agent_runtime.execution_context import AgentExecutionContext
from ...packages.model_client.client import AppAIClient

logger = logging.getLogger("ai_os.agents.resume_agent.agent")

@agent_registry.register(
    name="resume_agent",
    description="Extracts structural profile data (experience, skills, education) from raw resume text.",
    role_instruction="Evaluate resume profiles and extract clean parameters.",
    tools_allowed=["upload_resume_pdf", "analyze_resume_ats"]
)
class ResumeAgent:
    """
    Autonomous agent designed to extract structural profiles from candidate resumes.
    """
    def __init__(self):
        pass

    async def run(self, task_input: str, context: AgentExecutionContext, memory: Any) -> Dict[str, Any]:
        """
        Main execution workflow. Calls Groq API to parse raw text and validates output.
        """
        logger.info(f"Resume Agent: Analyzing resume text for user: '{context.user_id}'")
        
        # 1. Fetch AI client from memory manager or app config context
        # In vertical slice, instantiate a local client wrapper or pull from context
        # (Assuming model client api_key is configured)
        api_key = context.preferences.get("api_key", "mock_key")
        ai_client = AppAIClient(api_key=api_key)

        # 2. Query Groq with extraction prompt
        response_text = await ai_client.get_completion(
            prompt=task_input,
            system_prompt=RESUME_EXTRACTION_PROMPT,
            json_mode=True,
            temperature=0.1
        )

        # 3. Validate output matches Pydantic profile schema
        try:
            parsed_data = json.loads(response_text)
            profile = ResumeProfileSchema.model_validate(parsed_data)
            logger.info(f"Resume Agent: Profile parsing complete. Extracted {len(profile.skills)} skills.")
            
            # Save extracted profile directly to the Blackboard
            # (Enforcing Blackboard-based agent communication)
            # await memory.blackboard.update_variables(context.session_id, {"extracted_profile": profile.model_dump()})
            
            return profile.model_dump()
        except Exception as e:
            logger.error(f"Resume Agent failed schema validation: {e}. Output was: '{response_text}'")
            raise ValueError(f"Resume Agent failed to extract structured profile: {e}")
