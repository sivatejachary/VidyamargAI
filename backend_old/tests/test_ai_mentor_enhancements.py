import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models import models
from app.models.models import User, AIMentorSession, AIMentorMessage, AIMentorArtifact, AIMentorStudyPlan, AIMentorUsage
from app.core.config import settings

# SQLite in-memory database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

class TestAIMentorEnhancements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        # Create non-Base tables that are created in main.py DDL
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS courses (
                    id VARCHAR PRIMARY KEY,
                    title VARCHAR NOT NULL,
                    instructor VARCHAR DEFAULT 'VidyaMarg Team',
                    rating REAL DEFAULT 4.5,
                    reviews INTEGER DEFAULT 0,
                    duration VARCHAR DEFAULT '4 weeks',
                    thumbnail VARCHAR,
                    description TEXT,
                    category VARCHAR DEFAULT 'Technology',
                    totalmodules INTEGER DEFAULT 0,
                    level VARCHAR DEFAULT 'Beginner',
                    status VARCHAR DEFAULT 'published',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS enrollments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id VARCHAR,
                    user_id INTEGER,
                    progress REAL DEFAULT 0.0,
                    status VARCHAR DEFAULT 'active',
                    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS quiz_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    quiz_id VARCHAR,
                    score REAL,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    def setUp(self):
        # Override dependencies
        app.dependency_overrides[get_db] = override_get_db
        
        self.db = TestingSessionLocal()
        # Clean tables
        self.db.query(AIMentorSession).delete()
        self.db.query(AIMentorMessage).delete()
        self.db.query(AIMentorArtifact).delete()
        self.db.query(AIMentorStudyPlan).delete()
        self.db.query(AIMentorUsage).delete()
        self.db.query(User).delete()
        self.db.commit()

        # Create a test candidate user
        self.user = User(
            email="mentor_test@example.com",
            password_hash="hashedpwd",
            full_name="Mentor Test User",
            role="candidate"
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        # Mock current user dependency
        app.dependency_overrides[get_current_user] = lambda: self.user

        # Reset config to defaults
        self.orig_ai_mentor_enabled = settings.AI_MENTOR_ENABLED
        self.orig_search_enabled = settings.SEARCH_ENABLED
        settings.AI_MENTOR_ENABLED = True
        settings.SEARCH_ENABLED = True

    def tearDown(self):
        self.db.close()
        app.dependency_overrides.clear()
        settings.AI_MENTOR_ENABLED = self.orig_ai_mentor_enabled
        settings.SEARCH_ENABLED = self.orig_search_enabled

    def test_get_config(self):
        # Verify configuration endpoint returns feature flags
        response = self.client.get("/api/v1/ai-mentor/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ai_mentor_enabled", data)
        self.assertIn("voice_mentor_enabled", data)
        self.assertIn("study_plan_enabled", data)
        self.assertIn("artifacts_enabled", data)
        self.assertIn("search_enabled", data)
        self.assertIn("analytics_enabled", data)

    def test_feature_flag_guards(self):
        # Disable AI Mentor
        settings.AI_MENTOR_ENABLED = False
        response = self.client.get("/api/v1/ai-mentor/sessions")
        self.assertEqual(response.status_code, 400)
        self.assertIn("disabled", response.json()["detail"].lower())

        # Enable AI Mentor but disable Search
        settings.AI_MENTOR_ENABLED = True
        settings.SEARCH_ENABLED = False
        response = self.client.get("/api/v1/ai-mentor/search?q=test")
        self.assertEqual(response.status_code, 400)
        self.assertIn("disabled", response.json()["detail"].lower())

    def test_batch_archiving_sessions(self):
        # Create 100 sessions
        for i in range(100):
            session = AIMentorSession(
                id=f"session-{i}",
                user_id=self.user.id,
                title=f"Session {i}",
                created_at=datetime.utcnow()
            )
            self.db.add(session)
        self.db.commit()

        response = self.client.post("/api/v1/ai-mentor/sessions", json={"title": "New Session"})
        self.assertEqual(response.status_code, 200)

        # Check that the oldest 10 sessions are archived
        archived_sessions = self.db.query(AIMentorSession).filter(AIMentorSession.is_archived == True).all()
        self.assertEqual(len(archived_sessions), 10)
        
        # Check active session count is 91 (100 - 10 + 1)
        active_sessions = self.db.query(AIMentorSession).filter(
            AIMentorSession.user_id == self.user.id,
            AIMentorSession.is_archived == False
        ).all()
        self.assertEqual(len(active_sessions), 91)

    def test_batch_archiving_messages(self):
        # Create a session
        session = AIMentorSession(
            id="test-session-msg-archive",
            user_id=self.user.id,
            title="Session for message limit"
        )
        self.db.add(session)
        self.db.commit()

        # Create 1001 messages older than 1 hour to bypass the rate limit
        for i in range(1001):
            msg = AIMentorMessage(
                id=f"msg-{i}",
                session_id=session.id,
                user_id=self.user.id,
                sender="user",
                message=f"Message {i}",
                created_at=datetime.utcnow() - timedelta(hours=2)
            )
            self.db.add(msg)
        self.db.commit()

        # Post another message to trigger archiving
        from unittest.mock import patch
        with patch("app.api.endpoints.call_llm_with_fallback", return_value="Mocked AI Response"):
            response = self.client.post(f"/api/v1/ai-mentor/sessions/{session.id}/chat", json={"message": "New message"})
            self.assertEqual(response.status_code, 200)

        # Verify that oldest 100 messages are archived
        archived_msgs = self.db.query(AIMentorMessage).filter(AIMentorMessage.is_archived == True).all()
        self.assertEqual(len(archived_msgs), 100)

        # Verify active messages count is 903 (1001 - 100 + 2 (1 user message + 1 AI response))
        active_msgs = self.db.query(AIMentorMessage).filter(
            AIMentorMessage.session_id == session.id,
            AIMentorMessage.is_archived == False
        ).all()
        self.assertEqual(len(active_msgs), 903)

    def test_batch_archiving_artifacts(self):
        # Create 501 artifacts
        for i in range(501):
            art = AIMentorArtifact(
                id=f"art-{i}",
                user_id=self.user.id,
                artifact_type="notes",
                title=f"Artifact {i}",
                content=f"Content {i}"
            )
            self.db.add(art)
        self.db.commit()

        # Post another artifact to trigger archiving
        response = self.client.post("/api/v1/ai-mentor/artifacts", json={
            "artifact_type": "notes",
            "title": "New Artifact",
            "content": "New Content",
            "metadata_json": {}
        })
        self.assertEqual(response.status_code, 200)

        # Verify oldest 50 artifacts are archived
        archived_arts = self.db.query(AIMentorArtifact).filter(AIMentorArtifact.is_archived == True).all()
        self.assertEqual(len(archived_arts), 50)

        active_arts = self.db.query(AIMentorArtifact).filter(
            AIMentorArtifact.user_id == self.user.id,
            AIMentorArtifact.is_archived == False
        ).all()
        self.assertEqual(len(active_arts), 452)

    def test_search_and_pagination(self):
        # Populate search items
        session = AIMentorSession(
            id="session-search-1",
            user_id=self.user.id,
            title="Python tutorial chat",
            created_at=datetime.utcnow()
        )
        self.db.add(session)
        
        msg = AIMentorMessage(
            id="msg-search-1",
            session_id=session.id,
            user_id=self.user.id,
            sender="user",
            message="Let's study Python decorator concepts today.",
            created_at=datetime.utcnow()
        )
        self.db.add(msg)

        plan = AIMentorStudyPlan(
            id="plan-search-1",
            user_id=self.user.id,
            duration="7-day",
            title="Complete Python Masterclass",
            content="7 Days guide to learning advanced Python structures.",
            created_at=datetime.utcnow()
        )
        self.db.add(plan)

        art = AIMentorArtifact(
            id="art-search-1",
            user_id=self.user.id,
            artifact_type="notes",
            title="Python interview tips",
            content="Lists of Python OOP and decorator interview questions.",
            created_at=datetime.utcnow()
        )
        self.db.add(art)
        self.db.commit()

        # Search for "Python"
        response = self.client.get("/api/v1/ai-mentor/search?q=Python&type=all&page=1&page_size=2")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["query"], "Python")
        self.assertEqual(data["type"], "all")
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["total"], 4)
        self.assertTrue(data["has_more"])

        # Page 2
        response_page2 = self.client.get("/api/v1/ai-mentor/search?q=Python&type=all&page=2&page_size=2")
        self.assertEqual(response_page2.status_code, 200)
        data2 = response_page2.json()
        self.assertEqual(len(data2["results"]), 2)
        self.assertFalse(data2["has_more"])

        # Check session_id is returned in message result
        all_results = data["results"] + data2["results"]
        msg_result = next(r for r in all_results if r["type"] == "message")
        self.assertEqual(msg_result["session_id"], session.id)

    def test_llm_usage_character_counts(self):
        # Create usage log directly and test
        usage = AIMentorUsage(
            user_id=self.user.id,
            model_name="gemini-1.5-flash",
            prompt_chars=120,
            completion_chars=340
        )
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        self.assertEqual(usage.prompt_chars, 120)
        self.assertEqual(usage.completion_chars, 340)
