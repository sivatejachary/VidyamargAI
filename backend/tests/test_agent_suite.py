import unittest
from unittest.mock import patch
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models.models import User, Candidate, CandidateResume, JobAgentRun, JobAgentLog
from backend.app.agents.resume_intelligence import ResumeIntelligenceAgent, CandidateProfileData
from backend.app.agents.planning import PlanningAgent
from backend.app.agents.search import SearchAgent
from backend.app.agents.verification import VerificationAgent
from backend.app.agents.matching import MatchingAgent
from backend.app.agents.ranking import RankingAgent
from backend.app.agents.skill_gap import SkillGapAgent
from backend.app.agents.recommendation import RecommendationAgent
from backend.app.agents.manager import run_agent_flow, log_step
from backend.app.services.job_connectors.base import LiveJob

class TestJobAgentSuite(unittest.IsolatedAsyncioTestCase):
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

    def test_planning_agent_queries(self):
        profile = CandidateProfileData(
            skills=["Python", "Fastapi", "React"],
            experience_years=3.0,
            education="B.Tech",
            projects="",
            certifications=[],
            summary=""
        )
        agent = PlanningAgent(profile)
        queries = agent.generate_strategy()

        self.assertTrue(len(queries) > 0)
        # Verify query contents
        has_python_dev = any("Python" in q for q in queries)
        self.assertTrue(has_python_dev)

    @patch('backend.app.agents.search.linkedin_jobs.fetch')
    @patch('backend.app.agents.search.naukri.fetch')
    def test_search_agent_integration(self, mock_naukri, mock_linkedin):
        mock_linkedin.return_value = [
            LiveJob(
                title="Python Developer",
                company="Tech Corp",
                location="Bangalore",
                experience="3 Years",
                work_mode="Remote",
                skills=["Python"],
                apply_url="https://techcorp.com/apply",
                posted_date="Today",
                source="LinkedIn",
                description="Python engineer position"
            )
        ]
        mock_naukri.return_value = []
        
        with patch('backend.app.agents.search.indeed.fetch', return_value=[]), \
             patch('backend.app.agents.search.foundit.fetch', return_value=[]), \
             patch('backend.app.agents.search.wellfound.fetch', return_value=[]), \
             patch('backend.app.agents.search.internshala.fetch', return_value=[]), \
             patch('backend.app.agents.search.instahyre.fetch', return_value=[]), \
             patch('backend.app.agents.search.cutshort.fetch', return_value=[]), \
             patch('backend.app.agents.search.hirist.fetch', return_value=[]), \
             patch('backend.app.agents.search.hiring_posts.fetch', return_value=[]):
             
            queries = ["Python Backend Developer India", "FastAPI Developer Remote"]
            agent = SearchAgent(queries, ["Python", "Fastapi"])
            jobs = agent.execute_search()
            
            self.assertTrue(len(jobs) > 0)
            self.assertEqual(jobs[0].title, "Python Developer")

    def test_search_agent_fallback_generation(self):
        with patch('backend.app.agents.search.linkedin_jobs.fetch', return_value=[]), \
             patch('backend.app.agents.search.naukri.fetch', return_value=[]), \
             patch('backend.app.agents.search.indeed.fetch', return_value=[]), \
             patch('backend.app.agents.search.foundit.fetch', return_value=[]), \
             patch('backend.app.agents.search.wellfound.fetch', return_value=[]), \
             patch('backend.app.agents.search.internshala.fetch', return_value=[]), \
             patch('backend.app.agents.search.instahyre.fetch', return_value=[]), \
             patch('backend.app.agents.search.cutshort.fetch', return_value=[]), \
             patch('backend.app.agents.search.hirist.fetch', return_value=[]), \
             patch('backend.app.agents.search.hiring_posts.fetch', return_value=[]):
             
            queries = ["Python Backend Developer India"]
            agent = SearchAgent(queries, ["Python", "FastAPI"], exp_years=2.5)
            
            # Test template generator fallback directly (without call_nvidia)
            jobs = agent.execute_search()
            self.assertEqual(len(jobs), 12)
            self.assertTrue(any("Python" in j.title or "FastAPI" in j.title for j in jobs))
            self.assertTrue(any(j.company in ["Swiggy", "Zoho", "CRED", "Razorpay", "Paytm", "Flipkart", "Zomato", "Freshworks", "Ola", "InMobi", "Tata Consultancy Services", "Infosys", "Wipro", "HCLTech", "Cognizant", "Accenture"] for j in jobs))
            
            # Verify URL uniqueness and correctness
            urls = [j.apply_url for j in jobs]
            self.assertEqual(len(urls), len(set(urls)))
            for j in jobs:
                clean_name = j.company.lower().replace(" ", "").replace(".", "").replace(",", "")
                self.assertTrue(clean_name in j.apply_url or "careers" in j.apply_url or "jobs" in j.apply_url)

    def test_verification_agent_deduplication(self):
        job1 = LiveJob(
            title="Python Developer",
            company="Tech Corp",
            location="Bangalore",
            experience="3 Years",
            work_mode="Remote",
            skills=["Python"],
            apply_url="https://techcorp.com/apply",
            posted_date="Today",
            source="LinkedIn",
            description="Python engineer position"
        )
        job2 = LiveJob(
            title="Python Developer",
            company="Tech Corp",
            location="Bangalore",
            experience="3 Years",
            work_mode="Remote",
            skills=["Python"],
            apply_url="https://techcorp.com/apply",
            posted_date="Today",
            source="LinkedIn",
            description="Python engineer position"
        )
        
        agent = VerificationAgent([job1, job2])
        verified = agent.verify_and_deduplicate()
        
        self.assertEqual(len(verified), 1)

    def test_matching_agent_scoring(self):
        profile = CandidateProfileData(
            skills=["Python", "Fastapi", "Docker"],
            experience_years=3.0,
            education="Bachelor in Computer Science",
            projects="FastAPI Chatbot",
            certifications=["AWS Certified"],
            summary=""
        )
        
        job = LiveJob(
            title="Python FastAPI Backend Developer",
            company="Awesome Inc",
            location="Bangalore",
            experience="2 Years",
            work_mode="Remote",
            skills=["Python", "Fastapi", "Docker", "Kubernetes"],
            apply_url="https://awesome.com/careers",
            posted_date="Yesterday",
            source="Foundit",
            description="Looking for Python FastAPI engineer with Docker and Kubernetes."
        )
        
        agent = MatchingAgent(profile)
        result = agent.match_job(job)

        self.assertTrue(result["match_score"] >= 50)
        self.assertIn("Kubernetes", result["missing_skills"])
        self.assertIn("Python", result["matched_skills"])
        self.assertIsNotNone(result["reasoning"])

    def test_ranking_agent_ordering(self):
        jobs = [
            {"id": "j1", "title": "Developer 1", "match_score": 60, "source": "LinkedIn", "posted_date": "Yesterday"},
            {"id": "j2", "title": "Developer 2", "match_score": 90, "source": "LinkedIn", "posted_date": "Today"},
            {"id": "j3", "title": "Developer 3", "match_score": 75, "source": "LinkedIn", "posted_date": "5 days ago"}
        ]
        
        agent = RankingAgent(jobs)
        ranked = agent.rank_jobs()
        
        # Developer 2 has highest match score and is fresher
        self.assertEqual(ranked[0]["id"], "j2")
        self.assertEqual(ranked[1]["id"], "j3")
        self.assertEqual(ranked[2]["id"], "j1")

    def test_skill_gap_analysis(self):
        top_jobs = [
            {"missing_skills": ["Docker", "Kubernetes", "AWS"]},
            {"missing_skills": ["Docker", "Kubernetes"]},
            {"missing_skills": ["Docker", "Terraform"]}
        ]
        
        agent = SkillGapAgent(top_jobs)
        gaps = agent.analyze_gaps()
        
        # Docker is missing in all 3 jobs (100% demand)
        self.assertEqual(gaps[0]["skill"], "Docker")
        self.assertEqual(gaps[0]["priority"], "High")

    def test_recommendation_generation(self):
        gaps = [
            {"skill": "Docker", "missing_in_percentage": 100, "priority": "High", "count": 3},
            {"skill": "Kubernetes", "missing_in_percentage": 66, "priority": "High", "count": 2}
        ]
        
        agent = RecommendationAgent(gaps)
        recs = agent.generate_recommendations()
        
        self.assertIn("Docker", recs["skills"])
        self.assertTrue(len(recs["certifications"]) > 0)
        self.assertTrue(len(recs["projects"]) > 0)
        self.assertTrue(len(recs["roadmap"]) > 0)
