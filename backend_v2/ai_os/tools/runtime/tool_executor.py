import logging
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel

from .tool_context import ToolContext
from ...registry.tool_registry import tool_registry
from ...policy.permission_engine import PermissionEngine
from ...policy.policy_engine import PolicyEngine
from ...security.consent_engine import ConsentEngine
from ...execution.retry_engine import RetryEngine
from ...execution.timeout_engine import TimeoutEngine
from ...execution.circuit_breaker import circuit_breaker_registry
from ...execution.state_machine import TaskState, ExecutionStateMachine

logger = logging.getLogger("ai_os.tools.runtime.tool_executor")

class ToolExecutorRuntime:
    """
    Enforces authorization, input validations, and error budgets on all tool calls.
    """
    def __init__(self):
        self.permission = PermissionEngine()
        self.policy = PolicyEngine()
        self.consent = ConsentEngine()
        self.retry = RetryEngine()
        self.timeout = TimeoutEngine()

    async def run_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: ToolContext,
        state_machine: ExecutionStateMachine
    ) -> Dict[str, Any]:
        """
        Validates context, checks rules, executes the tool action, and returns outcomes.
        """
        t0 = time.perf_counter()
        logger.info(f"Tool Runtime: Executing tool '{tool_name}' in workspace '{context.workspace_id}'")

        # 1. Resolve tool entry
        try:
            tool_entry = tool_registry.get_tool(tool_name)
        except KeyError as ke:
            logger.error(f"Tool Runtime error: Tool '{tool_name}' is not registered.")
            return {"success": False, "error": "TOOL_NOT_FOUND", "details": str(ke)}

        tool_func = tool_entry["func"]
        tool_meta = tool_entry["meta"]

        # Convert context parameters to dict for engines
        auth_context = {
            "user_id": context.user_id,
            "user_role": context.permissions.get("role", "candidate")
        }

        # 2. Consent verification checks
        consent_ok = await self.consent.verify_consent(context.user_id, tool_meta.permission_required, auth_context)
        if not consent_ok:
            return {"success": False, "error": "CONSENT_DENIED", "details": f"Missing consent for scope: {tool_meta.permission_required}"}

        # 3. Authorization checks
        authorized = await self.permission.check_permission(context.user_id, tool_meta.permission_required, auth_context)
        if not authorized:
            return {"success": False, "error": "AUTHORIZATION_DENIED"}

        # 4. Enforce User preference policies
        # In production, rebuild CandidatePreferencesSchema from context.preferences
        
        # 5. Check Circuit Breaker
        breaker = circuit_breaker_registry.get_breaker(tool_name)
        if not breaker.allow_execution():
            return {"success": False, "error": "CIRCUIT_BREAKER_OPEN", "details": f"Tool '{tool_name}' offline."}

        # 6. Execute under retry/timeout budget passing tool context
        async def execute_tool_wrapper():
            # Validate input schema parameters
            validated_args = tool_meta.input_schema.model_validate(arguments)
            # Run async tool func, passing validated args and tool context
            return await tool_func(validated_args, context)

        try:
            result = await self.retry.execute_with_retry(
                task_id=tool_name,
                state_machine=state_machine,
                action=execute_tool_wrapper
            )
            breaker.record_success()
            latency_ms = (time.perf_counter() - t0) * 1000
            
            logger.info(f"Tool Runtime: Tool '{tool_name}' completed. Latency: {latency_ms:.2f}ms")
            return {
                "success": True,
                "result": result,
                "latency_ms": latency_ms
            }
        except Exception as e:
            breaker.record_failure()
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.critical(f"Tool Runtime failed executing tool '{tool_name}': {e}")
            return {
                "success": False,
                "error": "TOOL_EXECUTION_FAILURE",
                "details": str(e),
                "latency_ms": latency_ms
            }
