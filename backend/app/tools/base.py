import abc
import asyncio
from typing import Dict, Any, Type
from pydantic import BaseModel
from sqlalchemy.orm import Session

class BaseAgentTool(abc.ABC):
    """
    Base interface that all agent tools must implement.
    """
    
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique identifier for the tool."""
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Detailed description of what the tool does and when to use it."""
        pass

    @property
    @abc.abstractmethod
    def args_schema(self) -> Type[BaseModel]:
        """Pydantic model schema defining the tool's input arguments."""
        pass

    @property
    def requires_auth(self) -> bool:
        """Whether the tool requires an authenticated user session."""
        return True

    @property
    def rate_limit_limit(self) -> int:
        """Maximum number of invocations allowed per window."""
        return 100

    @property
    def rate_limit_period(self) -> int:
        """Window period in seconds (e.g. 60 for 1 minute)."""
        return 60

    # New performance & reliability metadata properties
    @property
    def latency(self) -> float:
        """Estimated latency in seconds."""
        return 1.0

    @property
    def reliability(self) -> float:
        """Estimated success rate (0.0 to 1.0)."""
        return 0.95

    @property
    def estimated_cost(self) -> float:
        """Estimated cost per invocation in credits/dollars."""
        return 0.0

    @property
    def timeout(self) -> float:
        """Timeout in seconds for this tool execution."""
        return 15.0

    @property
    def priority(self) -> int:
        """Priority score (higher is preferred)."""
        return 50

    @property
    def version(self) -> str:
        """Version of the tool."""
        return "1.0.0"

    @property
    def capabilities(self) -> list[str]:
        """Capabilities satisfied by this tool."""
        return [self.name]

    @abc.abstractmethod
    async def _run(self, db: Session, user_id: int, args: BaseModel, **kwargs) -> Any:
        """Internal execution logic of the tool."""
        pass

    async def execute(self, db: Session, user_id: int, arguments: Dict[str, Any], **kwargs) -> Any:
        """
        Executes the tool with safety parsing, validation, timeout enforcement, and error classification.
        """
        # Validate arguments schema
        try:
            parsed_args = self.args_schema.parse_obj(arguments)
        except Exception as e:
            return {
                "status": "error",
                "error_type": "ValidationError",
                "failure_classification": "INVALID_INPUT",
                "message": f"Invalid arguments for tool {self.name}: {str(e)}"
            }

        try:
            # Enforce timeout using wait_for
            result = await asyncio.wait_for(
                self._run(db, user_id, parsed_args, **kwargs),
                timeout=self.timeout
            )
            return {
                "status": "success",
                "data": result
            }
        except asyncio.TimeoutError:
            return {
                "status": "error",
                "error_type": "TimeoutError",
                "failure_classification": "RETRYABLE",
                "message": f"Tool execution timed out after {self.timeout} seconds."
            }
        except Exception as e:
            # Classify errors
            err_msg = str(e).lower()
            failure_classification = "PERMANENT"
            
            if "rate limit" in err_msg or "too many requests" in err_msg or "429" in err_msg:
                failure_classification = "RATE_LIMITED"
            elif "auth" in err_msg or "api key" in err_msg or "unauthorized" in err_msg or "401" in err_msg:
                failure_classification = "AUTH_REQUIRED"
            elif "connection" in err_msg or "timeout" in err_msg or "network" in err_msg:
                failure_classification = "RETRYABLE"
                
            return {
                "status": "error",
                "error_type": type(e).__name__,
                "failure_classification": failure_classification,
                "message": f"Execution failed: {str(e)}"
            }
