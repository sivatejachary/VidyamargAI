import asyncio
import logging
from typing import Callable, Any, Dict
from ..execution.state_machine import TaskState, ExecutionStateMachine

logger = logging.getLogger("ai_os.execution.retry_engine")

class RetryEngine:
    """
    Orchestrates retry budgets, backoff delays, and states transitions.
    """
    def __init__(self, retry_budget: int = 3, initial_delay: float = 0.5):
        self.retry_budget = retry_budget
        self.initial_delay = initial_delay

    async def execute_with_retry(
        self,
        task_id: str,
        state_machine: ExecutionStateMachine,
        action: Callable[[], Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Executes action. If fails, transitions state to RETRYING and loops with backoff.
        """
        attempt = 0
        while attempt < self.retry_budget:
            attempt += 1
            try:
                # If we are retrying, set the state machine correctly
                if attempt > 1:
                    state_machine.transition_to(TaskState.RETRYING)
                    delay = self.initial_delay * (2 ** (attempt - 2))
                    logger.info(f"Retrying task '{task_id}' (attempt {attempt}/{self.retry_budget}) after {delay}s backoff...")
                    await asyncio.sleep(delay)

                # Execute action block
                state_machine.transition_to(TaskState.EXECUTING)
                result = await action(*args, **kwargs)
                return result
            except Exception as e:
                logger.warning(f"Execution failed on attempt {attempt} for task '{task_id}': {e}")
                if attempt >= self.retry_budget:
                    state_machine.transition_to(TaskState.FAILED)
                    raise e
