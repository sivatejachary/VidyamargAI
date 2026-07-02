import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ai_os.agent_runtime.communication")

class AgentBlackboardCommunication:
    """
    Enforces Blackboard-based agent data exchanges.
    Direct communication between agents is strictly prohibited to keep agents decoupled.
    """
    def __init__(self, blackboard: Any):
        self.blackboard = blackboard

    async def write_observation(self, session_id: str, agent_name: str, key: str, value: Any):
        """
        Allows an agent to publish observations or variables to the shared Blackboard.
        """
        logger.info(f"Agent '{agent_name}' publishing variable '{key}' to Blackboard.")
        
        # Structure payload to include metadata about the publishing agent
        payload = {
            f"{agent_name}:{key}": value,
            f"metadata:{agent_name}:last_updated_key": key
        }
        await self.blackboard.update_variables(session_id, payload)

    async def read_observation(self, session_id: str, requesting_agent: str, key: str) -> Optional[Any] if 'Optional' in globals() else Any:
        """
        Allows an agent to read values published by other agents from the Blackboard.
        """
        logger.info(f"Agent '{requesting_agent}' reading variable '{key}' from Blackboard.")
        blackboard_state = await self.blackboard.get_blackboard(session_id)
        
        # Check standard format variables
        if key in blackboard_state.variables:
            return blackboard_state.variables[key]
            
        # Check if the key was published by a specific agent (format: "agent_name:key")
        for k, v in blackboard_state.variables.items():
            if k.endswith(f":{key}"):
                logger.info(f"Found match variable '{k}' published by: '{k.split(':')[0]}'")
                return v
                
        return None
