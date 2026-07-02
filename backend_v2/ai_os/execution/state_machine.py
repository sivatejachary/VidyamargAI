import logging
from enum import Enum
from typing import Set, Dict

logger = logging.getLogger("ai_os.execution.state_machine")

class TaskState(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    WAITING = "WAITING"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    REFLECTING = "REFLECTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"

# Valid state transitions matrix to prevent race states and corrupt execution chains
ALLOWED_TRANSITIONS: Dict[TaskState, Set[TaskState]] = {
    TaskState.CREATED: {TaskState.PLANNING, TaskState.CANCELLED},
    TaskState.PLANNING: {TaskState.EXECUTING, TaskState.WAITING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.WAITING: {TaskState.EXECUTING, TaskState.PAUSED, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.EXECUTING: {TaskState.OBSERVING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.OBSERVING: {TaskState.REFLECTING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.REFLECTING: {TaskState.VERIFYING, TaskState.PLANNING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.VERIFYING: {TaskState.COMPLETED, TaskState.FAILED, TaskState.WAITING, TaskState.CANCELLED},
    TaskState.RETRYING: {TaskState.EXECUTING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.FAILED: {TaskState.RETRYING, TaskState.CREATED}, # Support clean task restarts
    TaskState.PAUSED: {TaskState.WAITING, TaskState.CANCELLED},
    TaskState.COMPLETED: set(), # Terminal state
    TaskState.CANCELLED: set(), # Terminal state
}

class ExecutionStateMachine:
    """
    Enforces transitions and audits changes for task run lifecycles.
    """
    def __init__(self, task_id: str, initial_state: TaskState = TaskState.CREATED):
        self.task_id = task_id
        self.current_state = initial_state
        logger.info(f"Initialized State Machine for task '{self.task_id}' in state '{self.current_state}'")

    def transition_to(self, new_state: TaskState) -> bool:
        """
        Validates transition rules and updates current state.
        """
        if new_state == self.current_state:
            return True

        allowed = ALLOWED_TRANSITIONS.get(self.current_state, set())
        if new_state not in allowed:
            logger.error(
                f"Invalid transition constraint. Task '{self.task_id}' cannot shift "
                f"from state '{self.current_state}' to state '{new_state}'"
            )
            return False

        logger.info(f"Task '{self.task_id}' transitioned successfully: '{self.current_state}' -> '{new_state}'")
        self.current_state = new_state
        return True

    def get_state(self) -> TaskState:
        return self.current_state
