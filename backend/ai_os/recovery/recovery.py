import logging
from typing import Dict, Any, Optional
from ..execution.state_machine import TaskState, ExecutionStateMachine

logger = logging.getLogger("ai_os.recovery.recovery")

class RecoveryEngine:
    """
    Coordinates tool failovers, broadens search terms, and manages human escalations.
    """
    def __init__(self, approval_engine: Any):
        self.approval = approval_engine

    async def handle_tool_failure(
        self,
        tool_name: str,
        error_details: str,
        candidate_id: str,
        session_id: str,
        state_machine: ExecutionStateMachine,
        checkpoint_id: str
    ) -> Dict[str, Any]:
        """
        Runs failure recovery routines. Escalates to human approval queue if no recovery exists.
        """
        logger.warning(f"Recovery Engine triggered for failed tool '{tool_name}'. Error details: '{error_details}'")
        
        # 1. Evaluate alternate tool paths
        if tool_name == "discover_jobs_matching":
            logger.info("Direct job discover failed. Attempting recovery: falling back to database query tool 'postgres_job_search'...")
            return {
                "action": "FALLBACK_RUN",
                "alternate_tool": "postgres_job_search",
                "arguments_override": {"limit": 10}
            }
            
        # 2. Human escalation fallbacks
        logger.critical(f"No automated recovery path exists for '{tool_name}'. Halting execution and requesting human validation.")
        
        # Transition state to WAITING
        state_machine.transition_to(TaskState.WAITING)
        
        # Register a pending approval request
        approval_req = await self.approval.register_approval_request(
            request_id=f"approval_{session_id}",
            candidate_id=candidate_id,
            session_id=session_id,
            action_type=f"recover_{tool_name}",
            payload={"error": error_details, "failed_tool": tool_name},
            checkpoint_id=checkpoint_id
        )

        return {
            "action": "WAIT_FOR_HUMAN_APPROVAL",
            "approval_request_id": approval_req.request_id,
            "status": "HALTED"
        }
