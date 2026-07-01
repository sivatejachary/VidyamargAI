from datetime import datetime, timedelta
from typing import Dict, Any

class ToolMemory:
    def __init__(self):
        # Stores rate limited or offline tools: {tool_name: recovery_time}
        self._health_state: Dict[str, datetime] = {}
        # Stores historical success rates: {tool_name: {success: int, fail: int}}
        self._execution_stats: Dict[str, Dict[str, int]] = {}

    def mark_rate_limited(self, tool_name: str, block_duration_seconds: int = 1800):
        """Bypasses a rate-limited tool for a block duration."""
        self._health_state[tool_name] = datetime.utcnow() + timedelta(seconds=block_duration_seconds)

    def mark_offline(self, tool_name: str, block_duration_seconds: int = 300):
        """Bypasses an offline tool temporarily."""
        self._health_state[tool_name] = datetime.utcnow() + timedelta(seconds=block_duration_seconds)

    def is_healthy(self, tool_name: str) -> bool:
        """Checks if the tool is healthy to run (i.e. not in blocked health state)."""
        block_until = self._health_state.get(tool_name)
        if block_until and datetime.utcnow() < block_until:
            return False
        return True

    def record_execution(self, tool_name: str, success: bool):
        """Records tool outcomes to build historical performance profiles."""
        if tool_name not in self._execution_stats:
            self._execution_stats[tool_name] = {"success": 0, "fail": 0}
        if success:
            self._execution_stats[tool_name]["success"] += 1
        else:
            self._execution_stats[tool_name]["fail"] += 1

    def get_reliability_score(self, tool_name: str, default: float = 0.95) -> float:
        """Calculates historical reliability score based on previous execution success rates."""
        stats = self._execution_stats.get(tool_name)
        if not stats or (stats["success"] + stats["fail"]) == 0:
            return default
        total = stats["success"] + stats["fail"]
        return round(stats["success"] / total, 2)

# Global tool memory instance
tool_memory = ToolMemory()
