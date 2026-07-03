"""
VidyaMarg AI — Connector Registry (Dynamic Factory)
=====================================================
Implements the Open/Closed Principle: new connectors can be added
without modifying any existing code. Simply register the class here.

The registry also manages Circuit Breaker state per connector:
  - CLOSED (healthy): Connector is active
  - HALF_OPEN: Trial request after cooldown
  - OPEN: Connector is disabled due to consecutive failures

The Discovery Orchestrator reads from this registry to determine
which connectors to run on each scheduled discovery pass.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Type

from app.job_discovery.connectors.base import BaseJobConnector, ConnectorConfig
from app.job_discovery import config as cfg
from app.job_discovery.domain.exceptions import ConnectorCircuitOpenError, ConnectorNotFoundError

logger = logging.getLogger("jd.connectors.registry")


class CircuitState(str, Enum):
    CLOSED = "closed"       # Healthy — requests pass through
    HALF_OPEN = "half_open" # Recovering — allow one trial request
    OPEN = "open"           # Broken — reject all requests


@dataclass
class CircuitBreaker:
    """Per-connector circuit breaker state."""
    connector_name: str
    failure_count: int = 0
    state: CircuitState = CircuitState.CLOSED
    threshold: int = cfg.CONNECTOR_CIRCUIT_BREAKER_THRESHOLD
    last_failure_at: Optional[float] = None
    cooldown_seconds: int = 300  # 5 minutes before HALF_OPEN

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        import time
        self.failure_count += 1
        self.last_failure_at = time.time()
        if self.failure_count >= self.threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"[CircuitBreaker] {self.connector_name} OPEN after "
                f"{self.failure_count} consecutive failures"
            )

    def can_attempt(self) -> bool:
        """Returns True if a request should be allowed through."""
        import time
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            # Check if cooldown has passed
            if self.last_failure_at and (time.time() - self.last_failure_at) > self.cooldown_seconds:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"[CircuitBreaker] {self.connector_name} → HALF_OPEN (trial)")
                return True
            return False
        # HALF_OPEN: allow one through
        return True


@dataclass
class RegisteredConnector:
    """Registry entry for a single connector."""
    cls: Type[BaseJobConnector]
    config: ConnectorConfig
    enabled: bool = True
    circuit_breaker: CircuitBreaker = field(init=False)

    def __post_init__(self) -> None:
        self.circuit_breaker = CircuitBreaker(connector_name=self.config.name)


class ConnectorRegistry:
    """
    Central registry of all available job discovery connectors.
    Supports dynamic registration, circuit breaking, and health tracking.

    Usage:
        registry = get_registry()
        connectors = registry.get_enabled_connectors()
    """

    def __init__(self) -> None:
        self._registry: Dict[str, RegisteredConnector] = {}
        self._initialize_default_connectors()

    def _initialize_default_connectors(self) -> None:
        """Registers all built-in connectors from config.ENABLED_CONNECTORS."""
        from app.job_discovery.connectors.remoteok import RemoteOKConnector
        from app.job_discovery.connectors.telegram import TelegramConnector
        from app.job_discovery.connectors.greenhouse import GreenhouseConnector
        from app.job_discovery.connectors.lever import LeverConnector
        from app.job_discovery.connectors.wellfound import WellfoundConnector
        from app.job_discovery.connectors.indeed import IndeedConnector
        from app.job_discovery.connectors.linkedin import LinkedInConnector

        defaults: List[tuple] = [
            (
                "remoteok",
                RemoteOKConnector,
                ConnectorConfig(
                    name="remoteok",
                    display_name="RemoteOK",
                    source_type="api",
                    base_url="https://remoteok.com/api",
                    max_results=100,
                    timeout_seconds=20,
                ),
            ),
            (
                "telegram",
                TelegramConnector,
                ConnectorConfig(
                    name="telegram",
                    display_name="Telegram Jobs",
                    source_type="telegram",
                    api_key=cfg.TELEGRAM_API_ID,
                    api_secret=cfg.TELEGRAM_API_HASH,
                    max_results=200,
                    timeout_seconds=30,
                ),
            ),
            (
                "greenhouse",
                GreenhouseConnector,
                ConnectorConfig(
                    name="greenhouse",
                    display_name="Greenhouse",
                    source_type="api",
                    base_url="https://boards-api.greenhouse.io/v1",
                    max_results=200,
                    timeout_seconds=30,
                ),
            ),
            (
                "lever",
                LeverConnector,
                ConnectorConfig(
                    name="lever",
                    display_name="Lever",
                    source_type="api",
                    base_url="https://api.lever.co/v0/postings",
                    max_results=200,
                    timeout_seconds=30,
                ),
            ),
            (
                "wellfound",
                WellfoundConnector,
                ConnectorConfig(
                    name="wellfound",
                    display_name="Wellfound (AngelList)",
                    source_type="scraper",
                    base_url="https://wellfound.com",
                    max_results=100,
                    timeout_seconds=30,
                ),
            ),
            (
                "indeed",
                IndeedConnector,
                ConnectorConfig(
                    name="indeed",
                    display_name="Indeed",
                    source_type="scraper",
                    base_url="https://indeed.com",
                    max_results=150,
                    timeout_seconds=30,
                ),
            ),
            (
                "linkedin",
                LinkedInConnector,
                ConnectorConfig(
                    name="linkedin",
                    display_name="LinkedIn",
                    source_type="scraper",
                    base_url="https://linkedin.com/jobs",
                    max_results=200,
                    timeout_seconds=40,
                ),
            ),
        ]

        enabled_set = set(cfg.ENABLED_CONNECTORS)
        for name, cls, config in defaults:
            self._registry[name] = RegisteredConnector(
                cls=cls,
                config=config,
                enabled=(name in enabled_set),
            )

        logger.info(
            f"Connector registry initialized: "
            f"{len([r for r in self._registry.values() if r.enabled])} enabled / "
            f"{len(self._registry)} total"
        )

    def register(
        self,
        name: str,
        cls: Type[BaseJobConnector],
        config: ConnectorConfig,
        enabled: bool = True,
    ) -> None:
        """
        Dynamically registers a new connector.
        Allows adding connectors without modifying existing code.
        """
        self._registry[name] = RegisteredConnector(cls=cls, config=config, enabled=enabled)
        logger.info(f"[Registry] Registered new connector: {name}")

    def get_connector(self, name: str) -> BaseJobConnector:
        """Instantiates a connector by name. Raises if not found or circuit is open."""
        if name not in self._registry:
            raise ConnectorNotFoundError(name)
        entry = self._registry[name]
        if not entry.circuit_breaker.can_attempt():
            raise ConnectorCircuitOpenError(name, f"Circuit is OPEN. Skipping {name}.")
        return entry.cls(entry.config)

    def get_enabled_connectors(self) -> List[BaseJobConnector]:
        """
        Returns instantiated connectors for all enabled, circuit-closed connectors.
        Skips connectors with open circuit breakers.
        """
        instances = []
        for name, entry in self._registry.items():
            if not entry.enabled:
                continue
            if not entry.circuit_breaker.can_attempt():
                logger.warning(f"[Registry] Skipping {name} — circuit OPEN")
                continue
            try:
                instances.append(entry.cls(entry.config))
            except Exception as exc:
                logger.error(f"[Registry] Failed to instantiate {name}: {exc}")
        return instances

    def record_success(self, name: str) -> None:
        if name in self._registry:
            self._registry[name].circuit_breaker.record_success()

    def record_failure(self, name: str) -> None:
        if name in self._registry:
            self._registry[name].circuit_breaker.record_failure()

    def get_circuit_states(self) -> Dict[str, str]:
        return {
            name: entry.circuit_breaker.state.value
            for name, entry in self._registry.items()
        }

    def list_all(self) -> List[Dict[str, any]]:
        return [
            {
                "name": name,
                "display_name": entry.config.display_name,
                "source_type": entry.config.source_type,
                "enabled": entry.enabled,
                "circuit_state": entry.circuit_breaker.state.value,
                "failure_count": entry.circuit_breaker.failure_count,
            }
            for name, entry in self._registry.items()
        ]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_registry_instance: Optional[ConnectorRegistry] = None


def get_registry() -> ConnectorRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ConnectorRegistry()
    return _registry_instance
