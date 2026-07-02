import asyncio
import logging
from typing import Coroutine, Any

logger = logging.getLogger("ai_os.execution.timeout_engine")

class TimeoutEngine:
    """
    Enforces maximum execution durations on async tool operations.
    """
    def __init__(self):
        pass

    async def execute_with_timeout(self, coro: Coroutine[Any, Any, Any], timeout_seconds: float, task_name: str) -> Any:
        """
        Executes an asynchronous coroutine, raising asyncio.TimeoutError if timeout limit is exceeded.
        """
        logger.info(f"Executing task '{task_name}' with a strict timeout limit of {timeout_seconds}s")
        try:
            result = await asyncio.wait_for(coro, timeout=timeout_seconds)
            return result
        except asyncio.TimeoutError:
            logger.error(f"Timeout Exceeded: Task '{task_name}' failed to complete within {timeout_seconds} seconds.")
            raise
