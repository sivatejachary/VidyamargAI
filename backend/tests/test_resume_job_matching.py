import unittest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.models import User, Candidate, CandidateProfile
from app.models.pool_models import JobPool, JobPoolMatch
from app.workers.discovery_worker import match_pool_jobs_for_candidate

class TestResumeJobMatching(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Create in-memory SQLite database
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        self.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.TestingSessionLocal()

        # Seed Candidate and User
        self.user = User(
            email="candidate_match_test@example.com",
            password_hash="hashed_password",
            full_name="Alex River",
            role="candidate"
        )
        self.db.add(self.user)
        self.db.commit()

        self.candidate = Candidate(
            user_id=self.user.id,
            status="Resume Uploaded",
            current_step="Jobs",
            skills="Python, FastAPI, React, SQL",
            education="Bachelor of Technology in Computer Science",
            certifications="AWS Certified Developer",
            summary="Experienced developer with focus on Python and FastAPI."
        )
        self.db.add(self.candidate)
        self.db.commit()

        # Seed Candidate Profile representing parsed resume details
        self.profile = CandidateProfile(
            candidate_id=self.candidate.id,
            current_role="Backend Developer",
            generated_roles=json.dumps(["Backend Developer", "Software Engineer", "Python Developer"]),
            skills_graph=json.dumps({
                "primary_skills": ["Python", "FastAPI", "SQL"],
                "secondary_skills": ["React", "JavaScript"]
            }),
            parsed_metadata=json.dumps({
                "skills": ["Python", "FastAPI", "React", "SQL"]
            }),
            experience_years=3.0,
            specialization="Backend Engineering",
            industry="Software Development"
        )
        self.db.add(self.profile)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    async def test_job_pool_matching_based_on_resume(self):
        # 1. Seed matching and non-matching jobs in the pool
        matching_job = JobPool(
            stable_id="matching_job_101",
            title="Senior Python Backend Developer",
            company="Tech Corp",
            location="Remote",
            experience="3 years",
            skills="Python, FastAPI, PostgreSQL",
            apply_url="https://techcorp.com/jobs/101",
            posted_date=None,
            source="Greenhouse",
            description="Looking for an engineer to build backends with Python and FastAPI.",
            work_mode="Remote"
        )

        non_matching_job = JobPool(
            stable_id="civil_engineer_202",
            title="Civil Design Engineer",
            company="Build Infrastructure LLC",
            location="San Francisco, CA",
            experience="5 years",
            skills="AutoCAD, Structural Engineering",
            apply_url="https://buildinfra.com/jobs/202",
            posted_date=None,
            source="Lever",
            description="Seeking a civil engineer experienced with site design and AutoCAD.",
            work_mode="On-site"
        )

        self.db.add(matching_job)
        self.db.add(non_matching_job)
        self.db.commit()

        # 2. Execute candidate match processing
        await match_pool_jobs_for_candidate(
            candidate=self.candidate,
            db=self.db,
            candidate_skills=["Python", "FastAPI", "React", "SQL"]
        )

        # 3. Fetch matched records
        matches = self.db.query(JobPoolMatch).filter(
            JobPoolMatch.candidate_id == self.candidate.id
        ).all()

        # We should have matches for both jobs in the pool
        self.assertEqual(len(matches), 2)

        # Verify details of matching job score
        matching_score_record = next(m for m in matches if m.job_pool_id == matching_job.id)
        self.assertTrue(matching_score_record.should_apply)
        self.assertGreaterEqual(matching_score_record.match_score, 70.0)

        # Verify details of non-matching job score
        non_matching_score_record = next(m for m in matches if m.job_pool_id == non_matching_job.id)
        self.assertFalse(non_matching_score_record.should_apply)
        self.assertLess(non_matching_score_record.match_score, 60.0)
