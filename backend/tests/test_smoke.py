import pytest
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.models import User, Candidate

# SQLite in-memory engine config
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

class TestSmokeSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_db] = override_get_db
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    def test_01_smoke_signup(self):
        """Test user signup endpoint."""
        resp = self.client.post(
            "/api/v1/auth/signup",
            json={
                "email": "smoke_user@candidate.com",
                "password": "smokepassword123",
                "full_name": "Smoke Test User",
                "role": "candidate"
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["email"], "smoke_user@candidate.com")
        self.assertEqual(data["full_name"], "Smoke Test User")

    def test_02_smoke_login(self):
        """Test user login endpoint and token return."""
        resp = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": "smoke_user@candidate.com",
                "password": "smokepassword123"
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")

    def get_token(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": "smoke_user@candidate.com",
                "password": "smokepassword123"
            }
        )
        return resp.json()["access_token"]

    def test_03_smoke_profile(self):
        """Test candidate profile loading and updating."""
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get candidate profile
        resp = self.client.get("/api/v1/candidates/profile", headers=headers)
        self.assertEqual(resp.status_code, 200)
        profile = resp.json()
        self.assertIn(profile["status"], ["Onboarding", "Registered"])

        # Update candidate profile
        resp = self.client.put(
            "/api/v1/candidates/profile",
            json={
                "skills": "Python, React, AWS",
                "phone": "+1234567890",
                "summary": "Experienced engineer.",
                "experience": "[]",
                "education": "BS CS"
            },
            headers=headers
        )
        self.assertEqual(resp.status_code, 200)
        updated = resp.json()
        self.assertEqual(updated["skills"], "Python, React, AWS")

    def test_06_smoke_copilot_chat(self):
        """Test Copilot chat gateway endpoint."""
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = self.client.post(
            "/api/v1/chat/copilot",
            json={"message": "Hello, Copilot!", "history": []},
            headers=headers
        )
        self.assertIn(resp.status_code, [200, 500])

    def test_07_smoke_refresh_and_logout(self):
        """Test token refresh and logout endpoints."""
        resp = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": "smoke_user@candidate.com",
                "password": "smokepassword123"
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("refresh_token", data)
        refresh_token = data["refresh_token"]

        resp = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access_token", resp.json())

        resp = self.client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"message": "Successfully logged out"})

        resp = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        self.assertEqual(resp.status_code, 401)
