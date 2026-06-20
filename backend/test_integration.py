import unittest
import json
import os
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.models import (
    User, Candidate, Job, Application, Assessment, AssessmentAttempt,
    Interview, Offer, EmailNotification, CandidateProfile, CandidateResume
)
from app.services.orchestrator import orchestrator

class TestHireAIEngine(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Create Postgres connection for tests
        DATABASE_URL = os.getenv("DATABASE_URL")
        if DATABASE_URL:
            self.test_db_url = DATABASE_URL.rsplit('/', 1)[0] + '/vidyamargai_test'
        else:
            self.test_db_url = "postgresql://postgres:qPKoMqtzapoyltHQVdheOKyldfbnYrPH@thomas.proxy.rlwy.net:20637/vidyamargai_test"
            
        self.engine = create_engine(self.test_db_url)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = TestingSessionLocal()
        
        # Clean up existing test data from previous runs to avoid UniqueViolations
        try:
            self.db.query(EmailNotification).delete()
            self.db.query(Offer).delete()
            self.db.query(Interview).delete()
            self.db.query(AssessmentAttempt).delete()
            self.db.query(Application).delete()
            self.db.query(Job).delete()
            self.db.query(CandidateProfile).delete()
            self.db.query(CandidateResume).delete()
            self.db.query(Candidate).delete()
            self.db.query(User).delete()
            self.db.commit()
        except Exception:
            self.db.rollback()
        
        # Start call_gemini patcher
        def mock_call_gemini(prompt, json_mode=False):
            prompt_lower = prompt.lower()
            if "parse" in prompt_lower or "extract" in prompt_lower or "resume" in prompt_lower:
                return json.dumps({
                    "name": "Alex River",
                    "email": "test@candidate.com",
                    "phone": "1234567890",
                    "skills": "Python, FastAPI, SQLite, React, PostgreSQL",
                    "experience": [{"role": "Backend Developer", "years": 5}],
                    "summary": "Experienced developer",
                    "education": [],
                    "projects": [],
                    "certifications": "",
                    "achievements": [],
                    "languages": "",
                    "github": "",
                    "linkedin": "",
                    "portfolio": ""
                })
            elif "screen" in prompt_lower or "screening" in prompt_lower:
                if "user1@candidate.com" in prompt_lower or "user one" in prompt_lower or "java, php" in prompt_lower:
                    return json.dumps({
                        "skill_match": 40,
                        "experience_match": 50,
                        "education_match": 50,
                        "project_match": 40,
                        "overall_score": 45,
                        "decision": "reject",
                        "raw_reasoning": "Skills do not match React requirements."
                    })
                return json.dumps({
                    "skill_match": 90,
                    "experience_match": 85,
                    "education_match": 80,
                    "project_match": 80,
                    "overall_score": 85,
                    "decision": "shortlist",
                    "raw_reasoning": "Fits criteria."
                })
            elif "generator" in prompt_lower or "mcqs" in prompt_lower:
                return json.dumps({
                    "mcqs": [
                        {"id": 1, "question": "Q1?", "options": ["A", "B", "C", "D"], "correct_option": 1},
                        {"id": 2, "question": "Q2?", "options": ["A", "B", "C", "D"], "correct_option": 1},
                        {"id": 3, "question": "Q3?", "options": ["A", "B", "C", "D"], "correct_option": 1}
                    ],
                    "coding_challenges": [{"id": 1, "title": "C", "description": "D", "template": "def solve(): pass", "test_cases": [{"input": "i", "output": "o"}]}],
                    "english_test": [{"id": 1, "question": "E?"}]
                })
            elif "evaluate" in prompt_lower or "assessment" in prompt_lower:
                return json.dumps({
                    "score": 85.0,
                    "passed": True,
                    "feedback": "Great work!"
                })
            elif "interview" in prompt_lower:
                if "analyze" in prompt_lower or "analysis" in prompt_lower:
                    return json.dumps({
                        "knowledge_score": 80.0,
                        "communication_score": 85.0,
                        "confidence_score": 90.0,
                        "overall_score": 85.0,
                        "passed": True,
                        "feedback": "Solid interview."
                    })
                else:
                    return "Tell me about your Python experience."
            elif "recommendation" in prompt_lower or "hiring" in prompt_lower:
                return "Strong hire recommendation."
            else:
                return "{}"
                
        self.patcher = patch("app.services.orchestrator.call_gemini", side_effect=mock_call_gemini)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    async def test_complete_recruitment_flow(self):
        # 1. Create User & Candidate
        user = User(
            email="test@candidate.com",
            password_hash="mock_hash",
            full_name="Alex River",
            role="candidate"
        )
        self.db.add(user)
        self.db.commit()
        
        candidate = Candidate(user_id=user.id, status="Registered", current_step="Profile")
        self.db.add(candidate)
        self.db.commit()

        self.assertEqual(candidate.status, "Registered")

        # 2. Run Resume Collection (mock file content)
        resume_bytes = b"Candidate Name: Alex River. Skills: Python, FastAPI, SQLite, React, PostgreSQL. Experience: 5 Years as Backend Developer. Education: Master's in Computer Science."
        resume = await orchestrator.run_resume_collection_agent(self.db, candidate.id, resume_bytes, "alex_resume.pdf")
        
        self.assertEqual(candidate.status, "Resume Uploaded")
        self.assertIsNotNone(resume.resume_url)

        # 3. Create a Job & Application
        job = Job(
            title="Backend Engineer",
            description="Python & FastAPI backend developer.",
            required_skills="Python, FastAPI, SQLite",
            experience_level="Mid-Level",
            salary_range="$100k-$130k",
            location="San Francisco, CA",
            department="Engineering"
        )
        self.db.add(job)
        self.db.commit()

        app = Application(
            candidate_id=candidate.id,
            job_id=job.id,
            resume_id=resume.id,
            status="screening"
        )
        self.db.add(app)
        self.db.commit()

        # 4. Run Resume Screening
        await orchestrator.run_resume_screening_agent(self.db, app.id)
        self.db.refresh(app)
        
        # Verify shortlisted status (since SQLite mock defaults overall score >= 80)
        self.assertEqual(app.status, "assessment")

        # Verify EmailNotification was sent
        email_notif = self.db.query(EmailNotification).filter(EmailNotification.candidate_id == candidate.id).first()
        self.assertIsNotNone(email_notif)
        self.assertEqual(email_notif.recipient, "test@candidate.com")
        self.assertEqual(email_notif.sender, "recruiter@hireai.com") # fallback email
        self.assertTrue("Shortlisted" in email_notif.subject)

        # 5. Verify Assessment Generation & Attempt Creation
        attempt = self.db.query(AssessmentAttempt).filter(
            AssessmentAttempt.application_id == app.id
        ).first()
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.status, "started")

        # Mock submit assessment answers
        attempt.answers = '{"mcqs": {"1": 1, "2": 1, "3": 1}, "coding": {"1": "def reverse_words(s): return s"}, "english": {"1": "Hello, my name is Alex. I am a very passionate software developer with extensive experience building scalable backends with FastAPI."}}'
        self.db.commit()

        # 6. Run Assessment Evaluation
        await orchestrator.run_assessment_evaluation_agent(self.db, attempt.id)
        self.db.refresh(app)
        self.assertEqual(app.status, "interview")

        # 7. Tara AI Interview conversational turn
        interview = self.db.query(Interview).filter(Interview.application_id == app.id).first()
        self.assertIsNotNone(interview)
        
        next_q = await orchestrator.run_tara_interview_agent(self.db, interview.id, "I have experience with Python.")
        self.assertIsNotNone(next_q)
        
        # Fast forward questions to finish
        interview.current_question_index = 4 # past max questions (4)
        self.db.commit()
        
        next_q_fin = await orchestrator.run_tara_interview_agent(self.db, interview.id, "Final statement.")
        self.assertEqual(next_q_fin, "TARA_FINISHED")
        self.assertEqual(interview.status, "completed")

        # 8. Check Ranking & Offer stage transitions
        self.db.refresh(app)
        self.assertEqual(app.status, "offer")

        # Verify Offer is created
        offer = self.db.query(Offer).filter(Offer.application_id == app.id).first()
        self.assertIsNotNone(offer)
        self.assertEqual(offer.status, "pending")

        # 9. Respond to Offer (Accept) -> Onboarding
        offer.status = "accepted"
        self.db.commit()
        await orchestrator.run_onboarding_agent(self.db, app.id)
        
        self.db.refresh(app)
        self.assertEqual(app.status, "onboarding")
        self.assertTrue("Onboarding Completed" in candidate.status)

    async def test_rejection_email_paths(self):
        # Setup job
        job = Job(
            title="Frontend Developer",
            description="React description.",
            required_skills="React",
            experience_level="Junior",
            salary_range="$80k-$90k",
            location="Remote",
            department="Engineering"
        )
        self.db.add(job)
        self.db.commit()

        # 1. Test Resume Screening Rejection
        user1 = User(email="user1@candidate.com", password_hash="pwd", full_name="User One", role="candidate")
        self.db.add(user1)
        self.db.commit()
        cand1 = Candidate(user_id=user1.id, status="Registered", current_step="Profile")
        self.db.add(cand1)
        self.db.commit()
        app1 = Application(candidate_id=cand1.id, job_id=job.id, status="screening")
        self.db.add(app1)
        self.db.commit()

        # We mock resume screening to fail by setting mismatching skills
        cand1.skills = "Java, PHP" # does not contain React
        self.db.commit()
        await orchestrator.run_resume_screening_agent(self.db, app1.id)
        
        self.db.refresh(app1)
        self.assertEqual(app1.status, "rejected")
        
        email_notif = self.db.query(EmailNotification).filter(
            EmailNotification.candidate_id == cand1.id,
            EmailNotification.subject.like("%Update regarding your application%")
        ).first()
        self.assertIsNotNone(email_notif)
        self.assertTrue("not meet the screening criteria" in email_notif.body)
        self.assertEqual(email_notif.sender, "recruiter@hireai.com")

        # 2. Test Assessment Evaluation Rejection
        user2 = User(email="user2@candidate.com", password_hash="pwd", full_name="User Two", role="candidate")
        self.db.add(user2)
        self.db.commit()
        cand2 = Candidate(user_id=user2.id, status="Registered", current_step="Profile")
        self.db.add(cand2)
        self.db.commit()
        app2 = Application(candidate_id=cand2.id, job_id=job.id, status="assessment")
        self.db.add(app2)
        self.db.commit()
        
        # Create an assessment and a started attempt
        assess = Assessment(job_id=job.id, title="Test", mcqs="[]", coding_challenges="[]", english_test="[]")
        self.db.add(assess)
        self.db.commit()
        attempt = AssessmentAttempt(application_id=app2.id, assessment_id=assess.id, status="started")
        self.db.add(attempt)
        self.db.commit()
        
        # Set answers to be empty
        attempt.answers = '{"mcqs": {}, "coding": {}, "english": {}}'
        self.db.commit()
        
        # Run assessment evaluation
        await orchestrator.run_assessment_evaluation_agent(self.db, attempt.id)
        
        self.db.refresh(app2)
        self.assertEqual(app2.status, "rejected")
        
        email_notif2 = self.db.query(EmailNotification).filter(
            EmailNotification.candidate_id == cand2.id,
            EmailNotification.subject.like("%assessment%")
        ).first()
        self.assertIsNotNone(email_notif2)
        self.assertTrue("did not meet our passing threshold" in email_notif2.body)

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
