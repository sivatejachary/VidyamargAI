import abc
import logging
import time
from typing import Any, Dict, Type
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("ai_os.registry.tool_sdk")

class ToolExecutionError(Exception):
    """Custom exception raised when a tool fails execution."""
    pass

class BaseTool(abc.ABC):
    """
    Standard interface base class for all VidyaMarg AI system tools.
    Every platform capability inherits this class.
    """
    name: str = abc.abstractproperty()
    description: str = abc.abstractproperty()
    input_schema: Type[BaseModel] = abc.abstractproperty()
    permission_required: str = abc.abstractproperty()
    retry_budget: int = 3
    timeout: float = 30.0

    @abc.abstractmethod
    async def execute_action(self, args: BaseModel) -> Any:
        """Core asynchronous action details implemented by domain service wrappers."""
        pass

    async def run(self, raw_args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs validation checks, invokes execution actions, and logs outcomes.
        """
        t0 = time.perf_counter()
        logger.info(f"Invoking tool: '{self.name}' with context validation.")
        
        # 1. Parameter Validation
        try:
            validated_args = self.input_schema.model_validate(raw_args)
        except ValidationError as ve:
            logger.error(f"Tool '{self.name}' input schema validation failed: {ve}")
            return {
                "success": False,
                "error": "INPUT_VALIDATION_ERROR",
                "details": ve.errors()
            }

        # 2. Execute with Retries & Timer
        attempt = 0
        last_error = None
        while attempt < self.retry_budget:
            attempt += 1
            try:
                result = await self.execute_action(validated_args)
                latency_ms = (time.perf_counter() - t0) * 1000
                logger.info(f"Tool '{self.name}' completed on attempt {attempt}. Latency: {latency_ms:.2f}ms")
                return {
                    "success": True,
                    "result": result,
                    "latency_ms": latency_ms,
                    "attempts": attempt
                }
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Tool '{self.name}' failed on attempt {attempt}: {e}")
                if attempt < self.retry_budget:
                    # Apply exponential backoff sleep
                    backoff_delay = 0.5 * (2 ** (attempt - 1))
                    time.sleep(backoff_delay)
                    
        latency_ms = (time.perf_counter() - t0) * 1000
        logger.error(f"Tool '{self.name}' exhausted retry budget of {self.retry_budget}. Final error: {last_error}")
        return {
            "success": False,
            "error": "EXECUTION_FAILURE",
            "details": last_error,
            "latency_ms": latency_ms,
            "attempts": attempt
        }
