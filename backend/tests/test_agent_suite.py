import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.models import User, Candidate
from app.agents.resume_intelligence import ResumeIntelligenceAgent

class TestResumeIntelligenceSuite(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Create SQLite in-memory test database
        self.engine = create_engine("sqlite:///:memory:")
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_resume_intelligence_parsing(self):
        # Create candidate in memory db
        user = User(
            email="test@candidate.com",
            password_hash="pwd",
            full_name="Alex River",
            role="candidate"
        )
        self.db.add(user)
        self.db.commit()

        candidate = Candidate(
            user_id=user.id,
            skills="python, react, docker",
            summary="Passionate Python developer with 3+ years experience. Built FastAPI web applications.",
            experience='[{"title": "Backend Engineer", "company": "Tech Corp", "years": "3"}]',
            education="Bachelor of Technology in Computer Science",
            certifications="AWS Cloud Practitioner, Docker Certified Associate"
        )
        self.db.add(candidate)
        self.db.commit()

        agent = ResumeIntelligenceAgent(self.db, candidate.id)
        profile = agent.extract_profile()

        self.assertEqual(profile.experience_years, 3.0)
        self.assertIn("python", profile.skills)
        self.assertIn("react", profile.skills)
        self.assertIn("docker", profile.skills)
        self.assertIn("AWS Cloud Practitioner", profile.certifications)

    def test_fast_job_agent_run(self):
        # Import job models to register them with Base metadata
        import app.models.job_models
        from app.agents.career_supervisor import career_supervisor
        from app.models.job_models import CandidateAgent, AgentRun, Match, SkillGapAnalysis, Recommendation, CareerInsight, InterviewPreparation, Job

        # Recreate all tables to ensure job_models tables are created
        Base.metadata.create_all(bind=self.engine)

        user = User(
            email="test_fast@candidate.com",
            password_hash="pwd",
            full_name="Fast Test Candidate",
            role="candidate"
        )
        self.db.add(user)
        self.db.commit()

        candidate = Candidate(
            user_id=user.id,
            skills="React, TypeScript, Node.js",
            summary="Frontend engineer.",
            experience='[{"title": "Frontend dev", "company": "ReactCorp", "years": "2"}]',
        )
        self.db.add(candidate)
        self.db.commit()

        # Run fast agent pipeline
        result = career_supervisor.run(
            db=self.db,
            candidate_id=candidate.id,
            run_type="full",
            trigger="manual",
            fast=True
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["jobs_discovered"], 5)
        self.assertEqual(result["jobs_matched"], 5)

        # Verify database entities were populated
        agent = self.db.query(CandidateAgent).filter(CandidateAgent.candidate_id == candidate.id).first()
        self.assertIsNotNone(agent)
        self.assertEqual(agent.total_jobs_matched, 5)

        run = self.db.query(AgentRun).filter(AgentRun.candidate_id == candidate.id).first()
        self.assertIsNotNone(run)
        self.assertEqual(run.status, "completed")

        matches = self.db.query(Match).filter(Match.candidate_id == candidate.id).all()
        self.assertEqual(len(matches), 5)

        gap = self.db.query(SkillGapAnalysis).filter(SkillGapAnalysis.candidate_id == candidate.id).first()
        self.assertIsNotNone(gap)
        self.assertEqual(gap.overall_gap_score, 35.0)

        recs = self.db.query(Recommendation).filter(Recommendation.candidate_id == candidate.id).all()
        # 3 jobs + 1 career path + 1 skill recommendation
        self.assertEqual(len(recs), 5)

        insights = self.db.query(CareerInsight).filter(CareerInsight.candidate_id == candidate.id).all()
        self.assertEqual(len(insights), 2)
