from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class AgentExecutionContext(BaseModel):
    """
    Standard context model passed to agents during execution runtime.
    Enforces that all actions exist inside a workspace boundary.
    """
    user_id: str = Field(..., description="Target candidate user ID owner")
    session_id: str = Field(..., description="Active conversation session ID")
    workspace_id: str = Field(..., description="Target workspace ID grouping goals, tasks, and files")
    goal_id: Optional[str] = Field(default=None, description="Active career subgoal ID in progress")
    task_id: Optional[str] = Field(default=None, description="Active execution task run ID")
    permissions: Dict[str, Any] = Field(default_factory=dict, description="Active auth scopes")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User policy rules")
