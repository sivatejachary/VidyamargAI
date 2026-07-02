from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.agents.blackboard import Blackboard

class JobAgentState(BaseModel):
    user_id: int
    user_role: str
    session_id: str
    query: str
    
    # Context / memory
    preferences: Dict[str, Any] = Field(default_factory=dict)
    
    # Goal Stack
    main_goal: str = ""
    subgoal: Optional[str] = None
    current_task: Optional[str] = None
    
    # World State
    world_state: Dict[str, Any] = Field(default_factory=lambda: {
        "known_facts": [],
        "unknown_facts": [],
        "assumptions": [],
        "blocked_items": [],
        "completed_tasks": [],
        "pending_tasks": []
    })
    
    # SOTA shared blackboard
    blackboard: Optional[Blackboard] = None
    
    # Planning
    current_thought: Optional[str] = None
    next_actions: List[Dict[str, Any]] = Field(default_factory=list) # List of {"tool_or_capability": ..., "args": ...}
    confidence_score: float = 1.0
    interactive_card: Optional[Dict[str, Any]] = None
    
    # Execution
    last_observation: Optional[Any] = None
    execution_steps: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Loop control & Budgets
    status: str = "pending" # "pending", "clarifying", "completed", "failed"
    clarification_pending: bool = False
    clarification_question: Optional[str] = None
    
    max_iterations: int = 20
    max_reflection_retries: int = 3
    max_tool_retries: int = 2
    max_planning_depth: int = 5
    
    iteration_count: int = 0
    reflection_retry_count: int = 0
    tool_retry_count: int = 0
    planning_depth: int = 0
    
    # Telemetry / metrics
    metrics: Dict[str, Any] = Field(default_factory=lambda: {
        "total_latency": 0.0,
        "tool_latency": 0.0,
        "retry_count": 0,
        "reflection_count": 0,
        "parallel_execution_time": 0.0,
        "tokens_used": 0
    })
