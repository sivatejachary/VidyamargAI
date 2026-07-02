import logging
from typing import Dict, Any
from .runtime import AgentRuntime
from .execution_context import AgentExecutionContext
from ..execution.state_machine import ExecutionStateMachine

logger = logging.getLogger("ai_os.agent_runtime.dispatcher")

class AgentDispatcher:
    """
    Resolves sub-task requirements and routes goals to corresponding specialized agent loops.
    """
    def __init__(self, runtime: AgentRuntime):
        self.runtime = runtime

    async def dispatch_task(
        self,
        target_agent: str,
        task_input: str,
        context: AgentExecutionContext,
        state_machine: ExecutionStateMachine
    ) -> Dict[str, Any]:
        """
        Dispatches execution to target agent.
        """
        logger.info(f"Dispatcher routing task to agent: '{target_agent}'")
        
        # Enforce agent context mapping
        context.task_id = f"task_run_{context.session_id}_{target_agent}"
        
        result = await self.runtime.execute_agent(
            agent_name=target_agent,
            task_input=task_input,
            context=context,
            state_machine=state_machine
        )
        return result
