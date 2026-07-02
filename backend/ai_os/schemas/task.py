from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from ..execution.state_machine import TaskState

class TaskTriggerType(str, Enum):
    CRON = "CRON"
    EVENT = "EVENT"
    MANUAL = "MANUAL"

class TaskDefinition(BaseModel):
    id: str = Field(..., description="Unique task rule record ID")
    candidate_id: str = Field(..., description="Target candidate profile ID")
    name: str = Field(..., description="User-friendly name of the automation task")
    trigger_type: TaskTriggerType = Field(default=TaskTriggerType.MANUAL)
    trigger_config: Dict[str, Any] = Field(default_factory=dict, description="Parameters for triggers (e.g. cron string, event name)")
    workflow_steps: List[Dict[str, Any]] = Field(..., description="JSON list of tools and arguments to execute")
    status: TaskState = Field(default=TaskState.CREATED)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    next_run_at: Optional[datetime] = None

class TaskRunHistory(BaseModel):
    run_id: str = Field(..., description="Execution instance ID")
    task_id: str = Field(..., description="Reference task configuration ID")
    status: TaskState = Field(..., description="Final run status")
    started_at: datetime
    completed_at: Optional[datetime] = None
    step_logs: List[Dict[str, Any]] = Field(default_factory=list, description="Audit logs of execution steps")
