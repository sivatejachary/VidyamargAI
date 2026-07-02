import pytest
from ai_os.kernel import AIOSKernel
from ai_os.registry.tool_registry import tool_registry
from ai_os.registry.agent_registry import agent_registry
from packages.core_lib.database import DatabaseManager
from packages.model_client.client import AppAIClient
# Explicitly import decorated modules to trigger tool/agent registration
from ai_os.agents.resume_agent.agent import ResumeAgent
from ai_os.agents.supervisor_agent.agent import SupervisorAgent
from ai_os.tools.resume_tool.tool import upload_resume_pdf_tool

def test_imports_correctness():
    """Verify that all core AI OS modules can be imported without errors."""
    assert AIOSKernel is not None
    assert tool_registry is not None
    assert agent_registry is not None
    assert DatabaseManager is not None
    assert AppAIClient is not None

def test_registry_initialization():
    """Verify that specialized agents and tools are registered."""
    # Check that tools are registered in the global registry
    registered_tools = list(tool_registry._registry.keys())
    assert len(registered_tools) > 0
    assert "upload_resume_pdf" in registered_tools

    # Check that agents are registered
    registered_agents = list(agent_registry._registry.keys())
    assert len(registered_agents) > 0
    assert "resume_agent" in registered_agents
    assert "supervisor_agent" in registered_agents
