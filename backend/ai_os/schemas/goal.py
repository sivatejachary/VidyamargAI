from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from enum import Enum

class GoalStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class SubGoal(BaseModel):
    id: str = Field(..., description="Unique subgoal node ID")
    name: str = Field(..., description="Short name of the subgoal")
    description: str = Field(..., description="Detailed description of the target subgoal result")
    weight: float = Field(default=1.0, description="Goal weight in the progress calculation index")
    dependencies: List[str] = Field(default_factory=list, description="IDs of prerequisite subgoals")
    status: GoalStatus = Field(default=GoalStatus.PENDING, description="Current execution status of the subgoal node")
    progress: float = Field(default=0.0, description="Completion percentage (0.0 to 100.0)")

class GoalTree(BaseModel):
    id: str = Field(..., description="Unique Goal Tree execution instance ID")
    candidate_id: str = Field(..., description="Candidate profile ID tracking the career goals")
    target_career: str = Field(..., description="Target career role target (e.g. NVIDIA AI Engineer)")
    status: GoalStatus = Field(default=GoalStatus.PENDING)
    overall_progress: float = Field(default=0.0, description="Calculated weighted progress index")
    subgoals: Dict[str, SubGoal] = Field(..., description="Flat map of ID to SubGoal objects in the execution tree")
