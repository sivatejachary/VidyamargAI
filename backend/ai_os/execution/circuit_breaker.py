import logging
import time
from enum import Enum
from typing import Dict

logger = logging.getLogger("ai_os.execution.circuit_breaker")

class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    """
    Implements a Circuit Breaker pattern to protect tool execution pathways from downstream failures.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()

    def record_success(self):
        """Records a successful execution, closing the circuit if it was half-open."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit Breaker transitioned to CLOSED state after successful test call.")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_state_change = time.time()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self):
        """Records a failed execution, opening the circuit if failure threshold is reached."""
        self.failure_count += 1
        logger.warning(f"Circuit Breaker recorded failure count: {self.failure_count}/{self.failure_threshold}")
        
        if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            logger.critical(f"Circuit Breaker tripped to OPEN state. Restricting tool executions for {self.recovery_timeout}s.")
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
        elif self.state == CircuitState.HALF_OPEN:
            logger.critical("Circuit Breaker test call failed. Returning to OPEN state.")
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()

    def allow_execution(self) -> bool:
        """
        Determines if execution should proceed based on the circuit state and recovery cooldowns.
        """
        now = time.time()
        
        if self.state == CircuitState.OPEN:
            elapsed = now - self.last_state_change
            if elapsed >= self.recovery_timeout:
                logger.info("Circuit Breaker cooldown completed. Transitioning to HALF-OPEN for test execution.")
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                return True
            else:
                logger.warning(f"Execution rejected by Circuit Breaker. Cooldown remaining: {self.recovery_timeout - elapsed:.1f}s")
                return False
                
        return True


class CircuitBreakerRegistry:
    """
    Registry container mapping circuit breakers to specific tool names.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, tool_name: str) -> CircuitBreaker:
        if tool_name not in self.breakers:
            self.breakers[tool_name] = CircuitBreaker(
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout
            )
        return self.breakers[tool_name]

circuit_breaker_registry = CircuitBreakerRegistry()
