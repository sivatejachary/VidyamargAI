import unittest
import json
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.models import (
    User, Candidate, CandidateProfile, CandidateResume
)
from app.services.orchestrator import orchestrator

class TestResumeIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Create SQLite in-memory database
        self.test_db_url = "sqlite:///:memory:"
        self.engine = create_engine(self.test_db_url, connect_args={"check_same_thread": False})
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    async def test_resume_deletion_flow(self):
        from app.core.config import settings
        old_key = getattr(settings, "GEMINI_API_KEY", "")
        settings.GEMINI_API_KEY = "mock_test_key"
        try:
            # 1. Create a candidate
            user = User(
                email="delete_test@candidate.com",
                password_hash="pwd",
                full_name="Delete Candidate",
                role="candidate"
            )
            self.db.add(user)
            self.db.commit()
            
            candidate = Candidate(user_id=user.id, status="Registered", current_step="Profile")
            self.db.add(candidate)
            self.db.commit()
            
            # Verify initial state
            self.assertIsNone(candidate.skills)
            
            # 2. Upload first resume
            resume_bytes_1 = b"Skill: Python, FastAPI, SQL. Experience: 3 Years."
            # Patch call_gemini to avoid hitting actual API
            with patch("app.services.orchestrator.call_gemini", return_value='{"name": "Delete Candidate", "email": "delete_test@candidate.com", "phone": "1234567", "skills": "Python, FastAPI, SQL", "experience": [{"role": "Developer", "years": 3}], "summary": "Dev 1", "education": [], "projects": [], "certifications": "", "achievements": [], "languages": "", "github": "", "linkedin": "", "portfolio": ""}'):
                resume1 = await orchestrator.run_resume_collection_agent(self.db, candidate.id, resume_bytes_1, "resume1.pdf")
            
            # Re-fetch candidate and verify parsed details
            self.db.refresh(candidate)
            self.assertEqual(candidate.skills, "Python, FastAPI, SQL")
            self.assertEqual(candidate.summary, "Dev 1")
            
            # 3. Upload second resume (latest version)
            resume_bytes_2 = b"Skill: Go, Docker, Kubernetes. Experience: 5 Years."
            with patch("app.services.orchestrator.call_gemini", return_value='{"name": "Delete Candidate", "email": "delete_test@candidate.com", "phone": "1234567", "skills": "Go, Docker, Kubernetes", "experience": [{"role": "Senior Developer", "years": 5}], "summary": "Dev 2", "education": [], "projects": [], "certifications": "", "achievements": [], "languages": "", "github": "", "linkedin": "", "portfolio": ""}'):
                resume2 = await orchestrator.run_resume_collection_agent(self.db, candidate.id, resume_bytes_2, "resume2.pdf")
                
            self.db.refresh(candidate)
            self.assertEqual(candidate.skills, "Go, Docker, Kubernetes")
            self.assertEqual(candidate.summary, "Dev 2")
            
            # Verify candidate has 2 resumes and 2 profiles
            resumes = self.db.query(CandidateResume).filter(CandidateResume.candidate_id == candidate.id).all()
            self.assertEqual(len(resumes), 2)
            profiles = self.db.query(CandidateProfile).filter(CandidateProfile.candidate_id == candidate.id).all()
            self.assertEqual(len(profiles), 2)
            
            # 4. Delete latest resume (resume2)
            from app.api.endpoints import delete_candidate_resume
            
            with patch("app.services.storage.storage_service.delete_file") as mock_delete:
                delete_candidate_resume(resume_id=resume2.id, current_user=user, db=self.db)
                mock_delete.assert_called_once()
                
            # Re-fetch candidate and check status
            self.db.refresh(candidate)
            # Should revert to resume1's profile: "Python, FastAPI, SQL"
            self.assertEqual(candidate.skills, "Python, FastAPI, SQL")
            self.assertEqual(candidate.summary, "Dev 1")
            
            # 5. Delete the remaining resume (resume1)
            with patch("app.services.storage.storage_service.delete_file") as mock_delete:
                delete_candidate_resume(resume_id=resume1.id, current_user=user, db=self.db)
                mock_delete.assert_called_once()
                
            # Re-fetch candidate and check status
            self.db.refresh(candidate)
            # Should be completely empty/None
            self.assertIsNone(candidate.skills)
            self.assertIsNone(candidate.summary)
            self.assertEqual(candidate.status, "Registered")
            self.assertEqual(candidate.current_step, "Profile")
            
            # Profiles count should be 0
            profiles_count = self.db.query(CandidateProfile).filter(CandidateProfile.candidate_id == candidate.id).count()
            self.assertEqual(profiles_count, 0)
        finally:
            settings.GEMINI_API_KEY = old_key

if __name__ == "__main__":
    unittest.main()
