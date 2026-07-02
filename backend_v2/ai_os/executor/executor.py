import logging
from typing import Dict, Any, Optional
from ..registry.tool_registry import tool_registry
from ..policy.permission_engine import PermissionEngine
from ..policy.policy_engine import PolicyEngine
from ..security.consent_engine import ConsentEngine
from ..execution.retry_engine import RetryEngine
from ..execution.timeout_engine import TimeoutEngine
from ..execution.circuit_breaker import circuit_breaker_registry
from ..execution.state_machine import ExecutionStateMachine

logger = logging.getLogger("ai_os.executor.executor")

class ToolExecutor:
    """
    Validates, authorizes, and executes registered tools.
    """
    def __init__(self, db_session: Any):
        self.permission = PermissionEngine()
        self.policy = PolicyEngine()
        self.consent = ConsentEngine()
        self.retry = RetryEngine()
        self.timeout = TimeoutEngine()

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        candidate_id: str,
        context: Dict[str, Any],
        state_machine: ExecutionStateMachine,
        preferences: Any
    ) -> Dict[str, Any]:
        """
        Runs tool calls, applying permission checks, policy checks, timeouts, retries, and circuit breakers.
        """
        logger.info(f"Executor routing tool request: '{tool_name}' for candidate '{candidate_id}'")
        
        # 1. Lookup Tool capability in registry
        try:
            tool_entry = tool_registry.get_tool(tool_name)
        except KeyError as ke:
            logger.error(f"Execution failed: Tool '{tool_name}' is not registered.")
            return {"success": False, "error": "TOOL_NOT_FOUND", "details": str(ke)}

        tool_func = tool_entry["func"]
        tool_meta = tool_entry["meta"]

        # 2. Verify Consent permissions
        consent_granted = await self.consent.verify_consent(candidate_id, tool_meta.permission_required, context)
        if not consent_granted:
            return {"success": False, "error": "CONSENT_DENIED", "details": f"No user consent for: {tool_meta.permission_required}"}

        # 3. Verify ABAC permissions
        authorized = await self.permission.check_permission(candidate_id, tool_meta.permission_required, context)
        if not authorized:
            return {"success": False, "error": "AUTHORIZATION_DENIED"}

        # 4. Check user-defined policies
        policy_comply = await self.policy.evaluate_tool_input(tool_name, arguments, preferences)
        if not policy_comply:
            return {"success": False, "error": "POLICY_VIOLATION"}

        # 5. Check Circuit Breaker status
        breaker = circuit_breaker_registry.get_breaker(tool_name)
        if not breaker.allow_execution():
            return {"success": False, "error": "CIRCUIT_BREAKER_OPEN", "details": f"Tool '{tool_name}' is currently offline."}

        # 6. Execute task using Timeout and Retry engines
        async def run_tool_action():
            # Validate input arguments against Pydantic schema
            validated_args = tool_meta.input_schema.model_validate(arguments)
            # Run wrapper function under timeout limits
            coro = tool_func(validated_args)
            return await self.timeout.execute_with_timeout(coro, tool_meta.timeout, tool_name)

        try:
            result = await self.retry.execute_with_retry(
                task_id=tool_name,
                state_machine=state_machine,
                action=run_tool_action
            )
            # Record success in circuit breaker
            breaker.record_success()
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            logger.error(f"Executor failed to complete tool action '{tool_name}': {e}")
            # Record failure in circuit breaker
            breaker.record_failure()
            return {
                "success": False,
                "error": "TOOL_EXECUTION_ERROR",
                "details": str(e)
            }
        
tool_executor = ToolExecutor(db_session=None)
