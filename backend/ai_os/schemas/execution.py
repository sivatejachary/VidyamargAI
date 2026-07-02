from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from ..execution.state_machine import TaskState

class ExecutionStep(BaseModel):
    step_index: int = Field(..., description="Chronological execution index")
    agent_name: str = Field(..., description="Specialized agent name executing the sub-task")
    state: TaskState = Field(..., description="State of the step at logs execution")
    action_description: str = Field(..., description="Action description details")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="List of tools invoked")
    observation: Optional[str] = Field(default=None, description="Standardized result or error logs gathered")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AgentState(BaseModel):
    session_id: str = Field(..., description="Correlation active chat session ID")
    candidate_id: str = Field(..., description="Candidate profile ID")
    current_goal_id: Optional[str] = Field(default=None, description="Active subgoal ID node")
    blackboard: Dict[str, Any] = Field(default_factory=dict, description="In-memory shared blackboard facts")
    steps: List[ExecutionStep] = Field(default_factory=list, description="Historical execution path logs")
    status: TaskState = Field(default=TaskState.CREATED)
    retry_count: int = Field(default=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
