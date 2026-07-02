import logging
from typing import Dict, Any, Type, List
from pydantic import BaseModel
import threading

logger = logging.getLogger("ai_os.registry.agent_registry")

class AgentMetadata(BaseModel):
    name: str
    description: str
    role_instruction: str
    agent_class: Type[Any]
    tools_allowed: List[str]

class AgentRegistry:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AgentRegistry, cls).__new__(cls)
                cls._instance._registry = {}
        return cls._instance

    def register(self, name: str, description: str, role_instruction: str, tools_allowed: List[str]) -> Any:
        """
        Decorator to register a specialized agent class in the agent registry.
        """
        def decorator(cls: Type[Any]) -> Type[Any]:
            agent_meta = AgentMetadata(
                name=name,
                description=description,
                role_instruction=role_instruction,
                agent_class=cls,
                tools_allowed=tools_allowed
            )
            self._registry[name] = agent_meta
            logger.info(f"Registered agent role: '{name}' with {len(tools_allowed)} allowed tools.")
            return cls
        return decorator

    def get_agent(self, name: str) -> AgentMetadata:
        """Retrieves registered agent metadata and class reference."""
        if name not in self._registry:
            raise KeyError(f"Registry agent lookup failed. Agent '{name}' is not registered.")
        return self._registry[name]

    def list_agents(self) -> List[Dict[str, Any]]:
        """Returns JSON schema definitions of registered agents."""
        return [
            {
                "name": v.name,
                "description": v.description,
                "tools_allowed": v.tools_allowed
            } for k, v in self._registry.items()
        ]

agent_registry = AgentRegistry()
