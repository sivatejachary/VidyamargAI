"""
Agent Registry — plug-and-play agent lookup.
Unified registry of core runtime agents and supervisor pipelines.
"""
import logging
from typing import Type, Dict, Any

logger = logging.getLogger("app.agents.registry")

_AGENT_REGISTRY: Dict[str, Any] = {}


def register_agent(mode: str, agent_cls):
    """Registers an agent class for a given mode."""
    _AGENT_REGISTRY[mode] = agent_cls
    logger.info(f"Registered agent mode '{mode}': {agent_cls.__name__}")


def get_agent(mode: str):
    """Returns the agent class for a given mode, loading defaults if empty."""
    if not _AGENT_REGISTRY:
        _init_default_registry()
    if mode not in _AGENT_REGISTRY:
        raise ValueError(f"Unknown agent mode: {mode}")
    return _AGENT_REGISTRY[mode]


def list_agents() -> list:
    """Returns a list of all registered agent modes."""
    if not _AGENT_REGISTRY:
        _init_default_registry()
    return list(_AGENT_REGISTRY.keys())


def _init_default_registry():
    # 1. Base Workspace Supervisors
    try:
        from app.agents.resume_intelligence import ResumeIntelligenceAgent
        register_agent("resume", ResumeIntelligenceAgent)
    except ImportError as e:
        logger.warning(f"Could not import ResumeIntelligenceAgent: {e}")

    try:
        from app.agents.learning_os import LearningOSAgent
        register_agent("skill-lab", LearningOSAgent)
    except ImportError as e:
        logger.warning(f"Could not import LearningOSAgent: {e}")

    try:
        from app.agents.job_supervisor_agent import JobSupervisorAgent
        register_agent("job-agent", JobSupervisorAgent)
    except ImportError as e:
        logger.warning(f"Could not import JobSupervisorAgent: {e}")

    # 2. Consolidated 7 Core Runtime Client Agents
    try:
        from app.agents.discovery_agent import DiscoveryAgent
        register_agent("discovery", DiscoveryAgent)
    except ImportError as e:
        logger.warning(f"Could not import DiscoveryAgent: {e}")

    try:
        from app.agents.matching_agent import MatchingAgent
        register_agent("matching", MatchingAgent)
    except ImportError as e:
        logger.warning(f"Could not import MatchingAgent: {e}")

    try:
        from app.agents.application_agent import ApplicationAgent
        register_agent("application", ApplicationAgent)
    except ImportError as e:
        logger.warning(f"Could not import ApplicationAgent: {e}")

    try:
        from app.agents.tracking_agent import TrackingAgent
        register_agent("tracking", TrackingAgent)
    except ImportError as e:
        logger.warning(f"Could not import TrackingAgent: {e}")

    try:
        from app.agents.intelligence_agent import IntelligenceAgent
        register_agent("intelligence", IntelligenceAgent)
    except ImportError as e:
        logger.warning(f"Could not import IntelligenceAgent: {e}")

    try:
        from app.agents.human_queue_agent import HumanQueueAgent
        register_agent("human_queue", HumanQueueAgent)
    except ImportError as e:
        logger.warning(f"Could not import HumanQueueAgent: {e}")
