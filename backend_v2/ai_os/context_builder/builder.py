import logging
from typing import Dict, Any, List
from ..registry.tool_registry import tool_registry

logger = logging.getLogger("ai_os.context_builder.builder")

class ContextBuilder:
    """
    Assembles prompt contexts by merging active sessions, blackboard variables, and schemas.
    """
    def __init__(self, memory_manager: Any):
        self.memory = memory_manager

    async def build_execution_context(self, session_id: str, candidate_id: str) -> Dict[str, Any]:
        """
        Gathers memory components to build the LLM execution context.
        """
        logger.info(f"Assembling context parameters for session '{session_id}' and candidate '{candidate_id}'")
        
        # 1. Fetch Chat Logs
        chat_history = await self.memory.get_session_chat_history(session_id, limit=20)
        
        # 2. Fetch Blackboard Variables
        blackboard = await self.memory.get_blackboard_state(session_id)
        
        # 3. Retrieve Registered Tool Schemas
        tool_schemas = tool_registry.list_schemas()

        # 4. Compile into structured context payload
        context_payload = {
            "session_id": session_id,
            "candidate_id": candidate_id,
            "chat_history": chat_history,
            "blackboard": {
                "variables": blackboard.variables,
                "facts": blackboard.facts,
                "assumptions": blackboard.assumptions
            },
            "tools": tool_schemas
        }
        
        return context_payload

    def format_system_prompt(self, context: Dict[str, Any]) -> str:
        """
        Formats compiled execution context into a string prompt for the LLM.
        """
        chat_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context["chat_history"]])
        tools_str = "\n".join([
            f"- Tool: '{t['name']}'\n  Description: {t['description']}\n  Input Schema: {t['input_schema']}"
            for t in context["tools"]
        ])
        
        system_prompt = (
            "==================================================\n"
            "CONTEXT SYSTEM PROMPT (VidyaMarg Career Intelligence OS)\n"
            "==================================================\n\n"
            f"Active Session ID: {context['session_id']}\n"
            f"Candidate ID: {context['candidate_id']}\n\n"
            "--------------------------------------------------\n"
            "BLACKBOARD VARIABLES & FACTS:\n"
            "--------------------------------------------------\n"
            f"Variables: {context['blackboard']['variables']}\n"
            f"Facts: {context['blackboard']['facts']}\n"
            f"Assumptions: {context['blackboard']['assumptions']}\n\n"
            "--------------------------------------------------\n"
            "AVAILABLE SYSTEM TOOLS:\n"
            "--------------------------------------------------\n"
            f"{tools_str}\n\n"
            "--------------------------------------------------\n"
            "CONVERSATION HISTORY:\n"
            "--------------------------------------------------\n"
            f"{chat_str}\n"
        )
        return system_prompt
