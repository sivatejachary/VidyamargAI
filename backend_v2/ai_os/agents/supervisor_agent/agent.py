import logging
from typing import Dict, Any, List
from ...registry.agent_registry import agent_registry
from ...agent_runtime.execution_context import AgentExecutionContext
from ...agent_runtime.dispatcher import AgentDispatcher
from ...execution.state_machine import TaskState, ExecutionStateMachine

logger = logging.getLogger("ai_os.agents.supervisor_agent.agent")

@agent_registry.register(
    name="supervisor_agent",
    description="Orchestrates high-level goal executions by scheduling sub-tasks across specialized agents.",
    role_instruction="Coordinate execution flows, check milestones, and handle task retry states.",
    tools_allowed=[]
)
class SupervisorAgent:
    """
    Central orchestrator agent. Coordinates workflow execution, dispatches goals to runtime,
    and returns combined subgoal results. Contains NO business logic.
    """
    def __init__(self):
        pass

    async def run_dag(
        self,
        topological_order: List[str],
        subgoals: Dict[str, Any],
        context: AgentExecutionContext,
        dispatcher: AgentDispatcher,
        state_machine: ExecutionStateMachine
    ) -> Dict[str, Any]:
        """
        Executes goals sequentially based on topological dependencies.
        """
        logger.info(f"Supervisor: Beginning DAG execution for workspace '{context.workspace_id}' (Total subgoals: {len(topological_order)})")
        
        results = {}
        state_machine.transition_to(TaskState.EXECUTING)

        for subgoal_id in topological_order:
            node = subgoals.get(subgoal_id)
            if not node:
                logger.error(f"Supervisor: Subgoal '{subgoal_id}' definition missing.")
                continue

            logger.info(f"Supervisor: Dispatching subgoal '{subgoal_id}' ('{node.name}')")
            
            # Map subgoal target agent
            target_agent = self._resolve_target_agent(subgoal_id)
            
            # Create a localized state machine for the subgoal execution run
            sub_state_machine = ExecutionStateMachine(task_id=subgoal_id)
            
            # Dispatch task to Agent Runtime via Dispatcher
            run_result = await dispatcher.dispatch_task(
                target_agent=target_agent,
                task_input=node.description,
                context=context,
                state_machine=sub_state_machine
            )
            
            if not run_result.get("success", False):
                logger.error(f"Supervisor: Subgoal '{subgoal_id}' failed execution. Halting DAG run.")
                state_machine.transition_to(TaskState.FAILED)
                return {
                    "success": False,
                    "failed_subgoal": subgoal_id,
                    "error": run_result.get("error", "SUBGOAL_EXECUTION_FAILURE"),
                    "details": run_result.get("details")
                }

            results[subgoal_id] = run_result.get("result")
            logger.info(f"Supervisor: Subgoal '{subgoal_id}' completed successfully.")

        state_machine.transition_to(TaskState.COMPLETED)
        logger.info(f"Supervisor: DAG execution completed successfully for workspace '{context.workspace_id}'")
        return {
            "success": True,
            "results": results
        }

    def _resolve_target_agent(self, subgoal_id: str) -> str:
        """Maps subgoal IDs to specialized agent names."""
        if subgoal_id in ["extract_resume_text", "parse_resume_json", "upsert_candidate_profile"]:
            return "resume_agent"
        if subgoal_id in ["fetch_candidate_skills", "discover_jobs", "calculate_job_matches"]:
            return "jobs_agent"
        
        # Default fallback
        return "resume_agent"
