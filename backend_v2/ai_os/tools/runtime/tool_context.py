from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ToolContext(BaseModel):
    """
    Unified context payload passed to all tools.
    Encapsulates ownership, session variables, and telemetry logs.
    """
    user_id: str = Field(..., description="Candidate user owner ID")
    session_id: str = Field(..., description="Active session ID")
    workspace_id: str = Field(..., description="Target workspace ID")
    goal_id: Optional[str] = Field(default=None, description="Active subgoal ID")
    task_id: Optional[str] = Field(default=None, description="Active task run ID")
    permissions: Dict[str, Any] = Field(default_factory=dict, description="Active user authorization permissions")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="Active candidate preference rules")
    memory: Optional[Any] = Field(default=None, description="Reference to MemoryManager instance")
    logger: Optional[Any] = Field(default=None, description="Reference to execution Logger")
    telemetry: Dict[str, Any] = Field(default_factory=dict, description="Telemetry variables")

    class Config:
        arbitrary_types_allowed = True
