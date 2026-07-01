from typing import List, Dict, Any, Optional
from app.tools.base import BaseAgentTool
from app.services.tool_memory import tool_memory

class ToolUtilityEngine:
    @staticmethod
    def calculate_utility(
        tool: BaseAgentTool,
        w_reliability: float = 0.4,
        w_freshness: float = 0.2,
        w_latency: float = 0.2,
        w_cost: float = 0.2
    ) -> float:
        """
        Calculates utility: Utility = w_reliability * reliability + w_freshness * freshness - w_latency * latency - w_cost * cost
        """
        if not tool_memory.is_healthy(tool.name):
            # Return very low utility if tool is currently marked unhealthy/rate-limited
            return -9999.0
            
        reliability = tool_memory.get_reliability_score(tool.name, getattr(tool, "reliability", 0.95))
        latency = getattr(tool, "latency", 1.0)
        cost = getattr(tool, "estimated_cost", 0.0)
        
        # Freshness heuristic
        freshness = 1.0
        
        # Normalize and scale
        scaled_latency = min(1.0, latency / 15.0)
        scaled_cost = min(1.0, cost / 10.0)
        
        utility = (
            (w_reliability * reliability) +
            (w_freshness * freshness) -
            (w_latency * scaled_latency) -
            (w_cost * scaled_cost)
        )
        return round(utility, 3)

    @classmethod
    def resolve_best_tool(cls, matching_tools: List[BaseAgentTool]) -> Optional[BaseAgentTool]:
        """Selects the matching tool with the highest calculated utility score."""
        if not matching_tools:
            return None
        # Sort by utility descending
        matching_tools.sort(key=lambda x: cls.calculate_utility(x), reverse=True)
        return matching_tools[0]
