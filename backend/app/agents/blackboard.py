from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class Evidence(BaseModel):
    fact_id: str
    source_type: str        # "connector", "scraper", "user_input"
    source_ref: str         # URL or source identifier
    confidence_score: float = 1.0
    verified_by: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class GoalNode(BaseModel):
    node_id: str
    label: str
    status: str = "pending" # "pending", "in_progress", "completed", "failed", "blocked"
    priority: int = 50
    dependencies: List[str] = Field(default_factory=list)
    retry_budget: int = 2
    confidence_score: float = 1.0

class Blackboard(BaseModel):
    session_id: str
    known_facts: List[str] = Field(default_factory=list)
    unknown_facts: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    blocked_items: List[str] = Field(default_factory=list)
    completed_tasks: List[str] = Field(default_factory=list)
    pending_tasks: List[str] = Field(default_factory=list)
    
    # Evidence & Goal Graph
    evidence_graph: Dict[str, Evidence] = Field(default_factory=dict)
    goal_graph: Dict[str, GoalNode] = Field(default_factory=dict)
    
    # Plan revisions
    plan_version: int = 1
    plan_history: List[Dict[str, Any]] = Field(default_factory=list)
