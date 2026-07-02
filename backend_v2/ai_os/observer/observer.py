import logging
from datetime import datetime
from typing import Dict, Any
from ..schemas.tool import ToolResultPayload

logger = logging.getLogger("ai_os.observer.observer")

class Observer:
    """
    Standardizes tool execution results and updates the active Blackboard state.
    """
    def __init__(self, memory_manager: Any):
        self.memory = memory_manager

    async def record_observation(self, session_id: str, tool_name: str, execution_result: Dict[str, Any]):
        """
        Formats output results and appends them to Blackboard variables.
        """
        logger.info(f"Observer logging results for tool: '{tool_name}'")
        
        success = execution_result.get("success", False)
        
        observation_data = {
            "last_tool_run": tool_name,
            "last_tool_success": success,
            "last_tool_timestamp": datetime.utcnow().isoformat() if 'datetime' in globals() else ""
        }

        if success:
            tool_payload = execution_result.get("result", {})
            # Merge tool outcomes directly into Blackboard variables
            observation_data["tool_output"] = tool_payload
            logger.info(f"Observer recorded success data: '{str(tool_payload)[:100]}...'")
        else:
            error_details = execution_result.get("details", "Unknown execution error")
            observation_data["tool_error"] = error_details
            logger.warning(f"Observer recorded tool error: '{error_details}'")

        # Update the Blackboard variables
        await self.memory.update_blackboard_variables(session_id, observation_data)
