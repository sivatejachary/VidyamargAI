from typing import Dict, Type, List, Any, Optional
from app.tools.base import BaseAgentTool

class ToolRegistry:
    """
    Registry to store and retrieve all available agent tools.
    """
    def __init__(self):
        self._tools: Dict[str, BaseAgentTool] = {}

    def register(self, tool: BaseAgentTool) -> None:
        """Registers a tool instance."""
        if tool.name in self._tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseAgentTool]:
        """Retrieves a registered tool by its name."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseAgentTool]:
        """Lists all registered tools."""
        return list(self._tools.values())

    def resolve_capability(self, capability: str) -> Optional[BaseAgentTool]:
        """Resolves a capability string to the best registered tool matching it using the Tool Utility Engine."""
        matching_tools = []
        for tool in self.list_tools():
            if capability in getattr(tool, "capabilities", []):
                matching_tools.append(tool)
        if not matching_tools:
            return self.get_tool(capability)
            
        from app.services.utility_engine import ToolUtilityEngine
        return ToolUtilityEngine.resolve_best_tool(matching_tools)

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns JSON schemas of all registered tools for LLM tool binding."""
        schemas = []
        for tool in self.list_tools():
            schemas.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.args_schema.schema(),
                "metadata": {
                    "latency": getattr(tool, "latency", 1.0),
                    "reliability": getattr(tool, "reliability", 0.95),
                    "estimated_cost": getattr(tool, "estimated_cost", 0.0),
                    "timeout": getattr(tool, "timeout", 15.0),
                    "priority": getattr(tool, "priority", 50),
                    "version": getattr(tool, "version", "1.0.0"),
                    "capabilities": getattr(tool, "capabilities", [tool.name])
                }
            })
        return schemas

# Global tool registry instance
tool_registry = ToolRegistry()
