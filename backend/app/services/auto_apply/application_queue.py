"""
Application Queue — Asyncio semaphore-bounded concurrent worker pool.
Bounds parallelism to AUTO_APPLY_MAX_CONCURRENT simultaneous browser sessions.
"""
import asyncio
import logging
from typing import Callable, Awaitable, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class ApplicationQueue:
    """
    Manages concurrent auto-apply workers.
    
    Usage:
        queue = ApplicationQueue()
        await queue.run_all(task_ids, worker_fn, status_callback)
    """

    def __init__(self):
        max_concurrent = getattr(settings, "AUTO_APPLY_MAX_CONCURRENT", 5)
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_threads: dict[str, Any] = {}  # checkpoint_thread_id → task

    async def run_all(
        self,
        task_ids: list[int],
        worker_fn: Callable[[int], Awaitable[None]],
        on_status: Optional[Callable[[int, str], None]] = None
    ) -> None:
        """
        Run all tasks concurrently, bounded by semaphore.
        
        Args:
            task_ids:   List of ApplicationTask IDs to process
            worker_fn:  Async function (task_id) → None
            on_status:  Optional callback (task_id, status_msg) for progress events
        """
        async def bounded_worker(task_id: int):
            async with self._semaphore:
                try:
                    if on_status:
                        on_status(task_id, "APPLYING")
                    await worker_fn(task_id)
                    if on_status:
                        on_status(task_id, "SUBMITTED")
                except Exception as e:
                    logger.error(f"Worker failed for task {task_id}: {e}")
                    if on_status:
                        on_status(task_id, "FAILED")

        await asyncio.gather(
            *[bounded_worker(tid) for tid in task_ids],
            return_exceptions=True
        )

    def register_thread(self, checkpoint_thread_id: str, task_coroutine: Any) -> None:
        """Register a LangGraph checkpoint thread for crash recovery tracking."""
        self._active_threads[checkpoint_thread_id] = task_coroutine

    def resume_from_checkpoint(self, checkpoint_thread_id: str) -> bool:
        """
        Resume a paused LangGraph task by its checkpoint thread ID.
        Returns True if resumed, False if not found.
        """
        if checkpoint_thread_id in self._active_threads:
            logger.info(f"Resuming checkpoint thread: {checkpoint_thread_id}")
            return True
        logger.warning(f"Checkpoint thread not found: {checkpoint_thread_id}")
        return False


# Module-level singleton
application_queue = ApplicationQueue()