import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from app.tools.base import BaseAgentTool
from app.tools.registry import tool_registry
from app.services.policy_engine import PolicyEngine
from app.services.goal_manager import GoalManager
from app.agents.supervisor_agent import supervisor_agent
from app.agents.blackboard import Blackboard, Evidence, GoalNode
from pydantic import BaseModel, Field

@pytest.fixture
def anyio_backend():
    return 'asyncio'

# Define a Mock Tool for Testing
class MockToolArgs(BaseModel):
    query: str = Field(..., description="Test query")

class MockTestTool(BaseAgentTool):
    @property
    def name(self) -> str:
        return "mock_test_tool"

    @property
    def description(self) -> str:
        return "A mock tool for unit testing."

    @property
    def args_schema(self):
        return MockToolArgs

    async def _run(self, db, user_id, args, **kwargs):
        return f"Processed query: {args.query}"

@pytest.mark.anyio
async def test_tool_registry():
    tool = MockTestTool()
    tool_registry._tools.clear()
    tool_registry.register(tool)
    with pytest.raises(ValueError):
        tool_registry.register(tool)
        
    assert tool_registry.get_tool("mock_test_tool") == tool
    assert len(tool_registry.list_tools()) == 1
    assert tool_registry.get_schemas()[0]["name"] == "mock_test_tool"

@pytest.mark.anyio
async def test_policy_engine():
    tool = MockTestTool()
    
    # Test Permission Check
    allowed, msg = PolicyEngine.check_permissions("candidate", "mock_test_tool")
    assert allowed is True
    
    allowed, msg = PolicyEngine.check_permissions("candidate", "db_wipe")
    assert allowed is False
    assert "Permission denied" in msg
    
    # Test Rate Limit Check
    allowed, msg = PolicyEngine.check_rate_limits(999, tool)
    assert allowed is True
    
    # Test Domain Check
    allowed, msg = PolicyEngine.check_domain_scope("mock_test_tool", "google.com")
    assert allowed is False
    assert "Domain scope violation" in msg
    
    allowed, msg = PolicyEngine.check_domain_scope("mock_test_tool", "integrate.api.nvidia.com")
    assert allowed is True

@pytest.mark.anyio
async def test_goal_manager():
    res = GoalManager.classify_goal("Please monitor react developer jobs every week")
    assert res["is_recurring"] is True
    assert res["schedule"] == "0 9 * * 1"
    assert res["requires_approval"] is False
    
    res = GoalManager.classify_goal("Please apply to python jobs")
    assert res["is_recurring"] is False
    assert res["requires_approval"] is True

@pytest.mark.anyio
async def test_blackboard_initialization():
    bb = Blackboard(session_id="test_session")
    assert bb.plan_version == 1
    assert len(bb.known_facts) == 0
    assert len(bb.evidence_graph) == 0

@pytest.mark.anyio
async def test_supervisor_loop():
    db_mock = MagicMock(spec=Session)
    
    cand_mock = MagicMock()
    cand_mock.skills = "Python, SQL"
    db_mock.query().filter().first.return_value = cand_mock
    
    mock_responses = [
        '{"thought": "Searching database", "progress_updates": ["Planning search...", "Searching PostgreSQL"], "goal_stack": {"main_goal": "Find Python jobs", "subgoal": "Search PostgreSQL", "current_task": "Execute postgres search"}, "blackboard": {"session_id": "test_session_123", "known_facts": ["Candidate wants Python jobs"], "unknown_facts": [], "assumptions": [], "blocked_items": [], "completed_tasks": [], "pending_tasks": ["Search database"], "evidence_graph": {}, "goal_graph": {}, "plan_version": 1, "plan_history": []}, "next_actions": [{"tool_or_capability": "postgres_job_search", "args": {"query": "Python"}}], "confidence": 0.9, "clarification_question": null}',
        '{"thought": "Finished searching", "progress_updates": ["Finished search"], "goal_stack": {"main_goal": "Find Python jobs", "subgoal": null, "current_task": null}, "blackboard": {"session_id": "test_session_123", "known_facts": ["Candidate wants Python jobs"], "unknown_facts": [], "assumptions": [], "blocked_items": [], "completed_tasks": ["Search database"], "pending_tasks": [], "evidence_graph": {}, "goal_graph": {}, "plan_version": 1, "plan_history": []}, "next_actions": [{"tool_or_capability": "finish", "args": {}}], "confidence": 1.0, "clarification_question": null}'
    ]
    
    search_result = {
        "status": "success",
        "data": [{"id": 1, "title": "Python Dev", "company_name": "AI Corp", "apply_url": "http://example.com"}]
    }
    
    from app.tools.job_search import PostgresJobSearchTool
    tool_registry._tools.clear()
    tool_registry.register(PostgresJobSearchTool())
    
    with patch("app.agents.supervisor_agent.call_nvidia", side_effect=mock_responses), \
         patch("app.agents.supervisor_agent.call_gemini", side_effect=mock_responses), \
         patch("app.tools.job_search.PostgresJobSearchTool.execute", return_value=search_result):
         
        result = await supervisor_agent.route(
            db=db_mock,
            user_id=1,
            user_role="candidate",
            session_id="test_session_123",
            query="Find Python jobs"
        )
        
        assert result["status"] == "completed"
        assert len(result["steps_executed"]) == 1
        assert result["steps_executed"][0]["actions"][0]["tool"] == "postgres_job_search"
        
        # Verify that facts evidence was captured in the blackboard!
        # The route loop mutates the state blackboard during execute_actions
        assert len(result["steps_executed"][0]["responses"]) == 1
        assert result["steps_executed"][0]["responses"][0]["status"] == "success"

@pytest.mark.anyio
async def test_tool_utility_and_memory():
    from app.services.tool_memory import tool_memory
    from app.services.utility_engine import ToolUtilityEngine
    from app.tools.job_search import PostgresJobSearchTool
    
    tool = PostgresJobSearchTool()
    
    # Reset tool memory state
    tool_memory._health_state.clear()
    tool_memory._execution_stats.clear()
    
    assert tool_memory.is_healthy(tool.name) is True
    
    tool_memory.record_execution(tool.name, success=True)
    assert tool_memory.get_reliability_score(tool.name) == 1.0
    
    utility = ToolUtilityEngine.calculate_utility(tool)
    assert utility > 0.0
    
    tool_memory.mark_rate_limited(tool.name, block_duration_seconds=10)
    assert tool_memory.is_healthy(tool.name) is False
    
    utility_blocked = ToolUtilityEngine.calculate_utility(tool)
    assert utility_blocked == -9999.0
