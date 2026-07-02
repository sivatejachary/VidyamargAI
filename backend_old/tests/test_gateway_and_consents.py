import pytest
import asyncio
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.models import User, UserConsent, Candidate
from app.models.mcp_models import ToolPermission, CircuitBreakerState
import app.mcp.servers
from app.mcp.gateway import gateway, _get_breaker_state, _record_breaker_failure, _record_breaker_success
from app.core.events import subscribe, unsubscribe, publish_event


class TestGatewayAndConsents(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Use isolated in-memory SQLite database for test runs
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        self.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    async def test_event_bus_integration(self):
        """Verify that event bus publishes events and subscribers execute."""
        event_called = False
        payload_received = None
        
        async def mock_handler(payload):
            nonlocal event_called, payload_received
            event_called = True
            payload_received = payload

        subscribe("test_event_run", mock_handler)
        await publish_event("test_event_run", {"status": "success"})
        unsubscribe("test_event_run", mock_handler)
        
        self.assertTrue(event_called)
        self.assertEqual(payload_received, {"status": "success"})

    async def test_gateway_permissions_and_consent(self):
        """Verify consents correctly block high-risk tool calls."""
        user = User(email="test_gate@example.com", password_hash="hash", full_name="Gate User", role="candidate")
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Seed tool permissions for candidate
        perm = ToolPermission(role="candidate", tool="*", grants="read,write,apply")
        self.db.add(perm)
        self.db.commit()

        # Seed Candidate for user
        cand = Candidate(user_id=user.id, skills="react, node")
        self.db.add(cand)
        self.db.commit()

        # Test tool get_resume (does not require consent)
        res = await gateway.call_tool(
            user_id=user.id,
            server_name="mcp-server-resume",
            tool_name="get_resume",
            arguments={},
            db=self.db
        )
        self.assertEqual(res.get("status"), "success")

        # Test high-risk tool call (verify_consent check)
        res_high = await gateway.call_tool(
            user_id=user.id,
            server_name="mcp-server-audit",
            tool_name="verify_consent",
            arguments={"action": "app_submission"},
            db=self.db
        )
        self.assertEqual(res_high.get("status"), "success")
        self.assertFalse(res_high["result"]["authorized"])

    def test_circuit_breaker_flow(self):
        """Verify circuit breaker opens after failures and closes upon success."""
        server_name = "test-cb-server"
        
        # 1. CLOSED at start
        state = _get_breaker_state(server_name, self.db)
        self.assertEqual(state, "CLOSED")
        
        # 2. Record 3 failures
        _record_breaker_failure(server_name, self.db)
        _record_breaker_failure(server_name, self.db)
        _record_breaker_failure(server_name, self.db)
        
        state_open = _get_breaker_state(server_name, self.db)
        self.assertEqual(state_open, "OPEN")
        
        # 3. Success resets to CLOSED
        _record_breaker_success(server_name, self.db)
        state_closed = _get_breaker_state(server_name, self.db)
        self.assertEqual(state_closed, "CLOSED")
