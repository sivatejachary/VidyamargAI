"""
Workflow Engine — durable, crash-resilient step execution with state checkpointing.
Enables workflows to resume execution from the last successful checkpoint after restarts.
"""
import logging
import asyncio
from typing import Callable, Any, Dict, Optional
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.workflow_models import WorkflowRun, WorkflowStep, WorkflowEvent

logger = logging.getLogger("app.workflow_engine")

# Registry for resuming workflows: { workflow_type: executor_callable }
_WORKFLOW_REGISTRY: Dict[str, Callable[[int, dict], Any]] = {}


def register_workflow(workflow_type: str, executor: Callable[[int, dict], Any]):
    """Registers a workflow executor to allow startup recovery."""
    _WORKFLOW_REGISTRY[workflow_type] = executor
    logger.info(f"Registered workflow executor for type: {workflow_type}")


class WorkflowEngine:
    """Manages execution, checkpointing, and recovery of stateful workflows."""

    def start_run(self, user_id: int, workflow_type: str, context: dict, db: Session) -> WorkflowRun:
        """Start a new workflow run and persist it."""
        run = WorkflowRun(
            user_id=user_id,
            workflow_type=workflow_type,
            status="pending",
            context=context
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        self.log_event(run.id, "workflow_started", {"user_id": user_id, "workflow_type": workflow_type}, db)
        return run

    async def execute_step(
        self,
        run_id: int,
        step_name: str,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Executes a workflow step with checkpoint recovery.
        If the step was already successfully executed, retrieves the cached result.
        """
        db = SessionLocal()
        try:
            # 1. Fetch or create step model
            step = db.query(WorkflowStep).filter(
                WorkflowStep.run_id == run_id,
                WorkflowStep.step_name == step_name
            ).first()

            if not step:
                step = WorkflowStep(
                    run_id=run_id,
                    step_name=step_name,
                    status="pending"
                )
                db.add(step)
                db.commit()
                db.refresh(step)

            # 2. Check if already completed (durable bypass)
            if step.status == "completed":
                logger.info(f"Step '{step_name}' already completed for run {run_id}. Bypassing.")
                return step.result

            # Update status to running
            step.status = "running"
            step.attempts += 1
            db.commit()

            # Update run overall status to running
            run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
            if run and run.status != "running":
                run.status = "running"
                db.commit()

            self.log_event(run_id, "step_started", {"step": step_name, "attempt": step.attempts}, db)

            # 3. Execute step logic
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(None, lambda: func(*args, **kwargs))

                # Persist success checkpoint
                step.status = "completed"
                step.result = result
                step.error = None
                db.commit()

                self.log_event(run_id, "step_completed", {"step": step_name}, db)
                return result

            except Exception as exc:
                # Checkpoint step failure
                step.status = "failed"
                step.error = str(exc)
                db.commit()

                self.log_event(run_id, "step_failed", {"step": step_name, "error": str(exc)}, db)
                raise exc

        finally:
            db.close()

    def complete_run(self, run_id: int, status: str = "completed", db: Session = None):
        """Mark workflow run as completed or failed."""
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
            if run:
                run.status = status
                db.commit()
                self.log_event(run_id, f"workflow_{status}", {}, db)
                logger.info(f"Workflow run {run_id} marked as {status}.")
        finally:
            if should_close_db:
                db.close()

    def log_event(self, run_id: int, event_type: str, payload: dict, db: Session):
        """Create a history trace log for this workflow run."""
        event = WorkflowEvent(
            run_id=run_id,
            event_type=event_type,
            payload=payload
        )
        db.add(event)
        db.commit()

    async def recover_on_startup(self):
        """Scans database for unfinished/interrupted runs and triggers background resumption."""
        db = SessionLocal()
        try:
            active_runs = db.query(WorkflowRun).filter(
                WorkflowRun.status.in_(["pending", "running"])
            ).all()

            if not active_runs:
                logger.info("No interrupted workflow runs found to recover.")
                return

            logger.info(f"Found {len(active_runs)} interrupted workflow runs to recover.")
            for run in active_runs:
                executor = _WORKFLOW_REGISTRY.get(run.workflow_type)
                if executor:
                    logger.info(f"Resuming workflow run {run.id} ({run.workflow_type}) in background...")
                    # Spawn recovery task
                    asyncio.create_task(self._resume_run_safe(run.id, executor, run.user_id, run.context))
                else:
                    logger.warning(f"No executor registered to resume workflow type: {run.workflow_type}")
        finally:
            db.close()

    async def _resume_run_safe(self, run_id: int, executor: Callable, user_id: int, context: dict):
        """Safely resume a recovered workflow executor."""
        try:
            if asyncio.iscoroutinefunction(executor):
                await executor(run_id, user_id, context)
            else:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, executor, run_id, user_id, context)
        except Exception as e:
            logger.error(f"Error resuming workflow run {run_id}: {e}")
            self.complete_run(run_id, "failed")


workflow_engine = WorkflowEngine()
