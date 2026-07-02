from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class BaseEvent(BaseModel):
    event_id: str = Field(..., description="Unique event UUID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: str = Field(..., description="Active session correlation key")
    workspace_id: str = Field(..., description="Target workspace ID")

# Agent Lifecycles
class AgentStartedEvent(BaseEvent):
    agent_name: str = Field(..., description="Specialized agent name")
    input_prompt: str = Field(..., description="Task input description query")

class AgentCompletedEvent(BaseEvent):
    agent_name: str = Field(..., description="Specialized agent name")
    latency_ms: float = Field(..., description="Total execution duration")
    result_keys: list = Field(default_factory=list, description="Keys of variables published to Blackboard")

class AgentFailedEvent(BaseEvent):
    agent_name: str = Field(..., description="Specialized agent name")
    error_message: str = Field(..., description="Crashed exception trace log details")

# Tool Lifecycles
class ToolStartedEvent(BaseEvent):
    tool_name: str = Field(..., description="Target tool capability string")
    arguments: Dict[str, Any] = Field(default_factory=dict)

class ToolCompletedEvent(BaseEvent):
    tool_name: str = Field(..., description="Target tool capability string")
    success: bool
    latency_ms: float
    error_message: Optional[str] = None

# Automation & Goal Lifecycles
class TaskCreatedEvent(BaseEvent):
    task_id: str = Field(..., description="Unique task rule key")
    name: str = Field(..., description="Automation task name")
    schedule_cron: Optional[str] = None

class TaskCompletedEvent(BaseEvent):
    task_id: str = Field(..., description="Unique task rule key")
    status: str = Field(..., description="Final task run status")

class GoalCreatedEvent(BaseEvent):
    goal_id: str = Field(..., description="Goal tree root correlation key")
    career_role: str = Field(..., description="Target career role target")

class WorkspaceCreatedEvent(BaseEvent):
    candidate_id: str = Field(..., description="Target candidate owner ID")
