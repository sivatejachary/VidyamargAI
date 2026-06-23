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
