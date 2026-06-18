"""
Agent Registry — plug-and-play agent lookup.
Adding a new agent = one line in AGENT_REGISTRY.
"""
import logging
from typing import Type, Optional

logger = logging.getLogger("app.agents.registry")

# Lazy registry populated at startup to avoid circular imports.
_AGENT_REGISTRY = {}


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
