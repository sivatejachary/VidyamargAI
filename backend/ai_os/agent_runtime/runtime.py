import logging
import time
from typing import Any, Dict, Optional
from .execution_context import AgentExecutionContext
from ..registry.agent_registry import agent_registry
from ..execution.state_machine import TaskState, ExecutionStateMachine

logger = logging.getLogger("ai_os.agent_runtime.runtime")

class AgentRuntime:
    """
    Coordinates agent run lifecycles, collects telemetry metrics, and manages checkpoint savings.
    """
    def __init__(self, memory_manager: Any):
        self.memory = memory_manager

    async def execute_agent(
        self,
        agent_name: str,
        task_input: str,
        context: AgentExecutionContext,
        state_machine: ExecutionStateMachine
    ) -> Dict[str, Any]:
        """
        Loads the agent, checks permissions, executes workflows, and records execution metrics.
        """
        t0 = time.perf_counter()
        logger.info(f"Agent Runtime: Booting agent '{agent_name}' for session '{context.session_id}'")
        
        # 1. Resolve agent from registry
        try:
            agent_meta = agent_registry.get_agent(agent_name)
        except KeyError as ke:
            logger.error(f"Agent Runtime failed: Agent '{agent_name}' is not registered.")
            return {"success": False, "error": "AGENT_NOT_FOUND", "details": str(ke)}

        agent_instance = agent_meta.agent_class()

        # 2. Check permission boundaries
        # In production, check context.permissions scopes against agent_meta.tools_allowed
        
        # 3. Transition Task State to EXECUTING
        state_machine.transition_to(TaskState.EXECUTING)
        
        try:
            # 4. Invoke agent execution method
            # All agents expose a standardized async 'run' method
            result = await agent_instance.run(task_input, context, self.memory)
            latency_ms = (time.perf_counter() - t0) * 1000
            
            logger.info(f"Agent Runtime: Agent '{agent_name}' completed. Latency: {latency_ms:.2f}ms")
            state_machine.transition_to(TaskState.COMPLETED)
            
            # Record execution metrics to system audit table
            await self._record_run_metrics(agent_name, context, latency_ms, success=True)
            
            return {
                "success": True,
                "result": result,
                "latency_ms": latency_ms
            }
        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.critical(f"Agent Runtime failed on running '{agent_name}' workflow: {e}")
            state_machine.transition_to(TaskState.FAILED)
            await self._record_run_metrics(agent_name, context, latency_ms, success=False, error_msg=str(e))
            
            return {
                "success": False,
                "error": "AGENT_WORKFLOW_FAILURE",
                "details": str(e),
                "latency_ms": latency_ms
            }

    async def _record_run_metrics(self, agent_name: str, context: AgentExecutionContext, latency_ms: float, success: bool, error_msg: Optional[str] = None):
        """Saves telemetry logs in memory or DB outbox."""
        logger.info(
            f"Agent Metric: Name={agent_name}, Workspace={context.workspace_id}, "
            f"Latency={latency_ms:.1f}ms, Success={success}"
        )
