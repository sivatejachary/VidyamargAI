import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.models import TelegramSource
from app.services.job_connectors.base import LiveJob
from app.agents.telegram import TelegramCommunityAgent
from app.agents.consistency import JobConsistencyAgent

class TestTelegramAndConsistency(unittest.TestCase):
    def setUp(self):
        # Create SQLite in-memory test database
        self.engine = create_engine("sqlite:///:memory:")
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_telegram_source_crud_and_seeding(self):
        # Initial check (empty)
        count = self.db.query(TelegramSource).count()
        self.assertEqual(count, 0)

        # Create
        source = TelegramSource(channel_name="test_jobs_channel", active=True)
        self.db.add(source)
        self.db.commit()

        count = self.db.query(TelegramSource).count()
        self.assertEqual(count, 1)

        # Read
        db_source = self.db.query(TelegramSource).filter_by(channel_name="test_jobs_channel").first()
        self.assertIsNotNone(db_source)
        self.assertTrue(db_source.active)

        # Update
        db_source.active = False
        self.db.commit()
        db_source_updated = self.db.query(TelegramSource).filter_by(channel_name="test_jobs_channel").first()
        self.assertFalse(db_source_updated.active)

        # Delete
        self.db.delete(db_source_updated)
        self.db.commit()
        count = self.db.query(TelegramSource).count()
        self.assertEqual(count, 0)

    @patch("httpx.Client")
    def test_telegram_agent_fetch_messages_success(self, mock_client):
        # Mock successful httpx GET with bs4 elements
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <div class="tgme_widget_message_text">🚨 HIRING: Python Developer at Swiggy. Apply here: https://careers.swiggy.com/123</div>
                <div class="tgme_widget_message_text">🔥 New opening for React Intern at Google. Link: https://careers.google.com/456</div>
            </body>
        </html>
        """
        
        client_instance = MagicMock()
        client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = client_instance

        agent = TelegramCommunityAgent(self.db)
        messages = agent.fetch_channel_messages("test_channel")
        
        self.assertEqual(len(messages), 2)
        self.assertIn("Python Developer at Swiggy", messages[0])
        self.assertIn("React Intern at Google", messages[1])

    @patch("httpx.Client")
    def test_telegram_agent_fetch_messages_fallback(self, mock_client):
        # Mock 302 redirect / failure to verify fallback mock messages trigger
        mock_response = MagicMock()
        mock_response.status_code = 302
        
        client_instance = MagicMock()
        client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = client_instance

        agent = TelegramCommunityAgent(self.db)
        messages = agent.fetch_channel_messages("freshers_opening")
        
        # Should trigger fallback mock messages
        self.assertTrue(len(messages) > 0)
        self.assertTrue(any("Google" in m for m in messages))
        self.assertTrue(any("Microsoft" in m for m in messages))

    def test_telegram_agent_parsing_fallback(self):
        agent = TelegramCommunityAgent(self.db)
        msg = "🚨 HIRING: Software Engineer Intern at Google India. Location: Bangalore, India. Exp: 0-1 years. Skills: Python, SQL. Apply here: https://careers.google.com/jobs/results/12345"
        
        # Running rule-based fallback by forcing LLM call exception (or letting it fall back naturally when key is missing)
        parsed = agent.parse_job_from_message(msg)
        
        self.assertEqual(len(parsed), 1)
        job = parsed[0]
        self.assertIn("Software Engineer", job["title"])
        self.assertIn("Google", job["company"])
        self.assertIn("Bangalore", job["location"])
        self.assertIn("https://careers.google.com/jobs/results/12345", job["apply_url"])

    def test_job_consistency_scoring(self):
        agent = JobConsistencyAgent()

        # 1. Test case: Perfect match (Google)
        job = LiveJob(
            title="Software Engineer Intern",
            company="Google",
            location="Bangalore, India",
            experience="0-1 Years",
            skills=["Python", "SQL"],
            apply_url="https://careers.google.com/jobs/results/12345",
            posted_date="Today",
            source="Telegram",
            description="Software Engineer Intern at Google"
        )
        score, status = agent.verify_job_consistency(job)
        self.assertEqual(status, "Fully Verified")
        self.assertTrue(score >= 85)

        # 2. Test case: Mismatched title / Rejected
        job_mismatch = LiveJob(
            title="Java Tech Lead",  # Landing page has "Software Engineer Intern"
            company="Google",
            location="Bangalore, India",
            experience="10+ Years",
            skills=["Java"],
            apply_url="https://careers.google.com/jobs/results/12345",
            posted_date="Today",
            source="Telegram",
            description="Java Developer"
        )
        score, status = agent.verify_job_consistency(job_mismatch)
        self.assertEqual(status, "Rejected")
        self.assertTrue(score < 50)

        # 3. Test case: Generic careers page / Rejected
        job_generic = LiveJob(
            title="QA Engineer",
            company="SomeCompany",
            location="Remote",
            experience="3 Years",
            skills=["Selenium"],
            apply_url="https://careers.google.com/jobs/results/", # Generic careers homepage fallback in fetch_landing_page
            posted_date="Today",
            source="LinkedIn",
            description="QA role"
        )
        score, status = agent.verify_job_consistency(job_generic)
        self.assertEqual(status, "Rejected")
        self.assertTrue(score < 50)

    def test_job_consistency_404_rejection(self):
        agent = JobConsistencyAgent()
        # Test case: HTTP 404 Not Found / Rejected
        with patch.object(agent, 'fetch_landing_page', return_value=("", "", 404)):
            job_404 = LiveJob(
                title="Python Developer",
                company="Swiggy",
                location="Bangalore",
                experience="0-2 Years",
                skills=["Python"],
                apply_url="https://careers.swiggy.com/broken-link",
                posted_date="Today",
                source="Telegram",
                description="Python developer position"
            )
            score, status = agent.verify_job_consistency(job_404)
            self.assertEqual(status, "Rejected")
            self.assertEqual(score, 0)
