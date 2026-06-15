import unittest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models.models import User, Candidate
from app.core.security import get_password_hash

# Setup test DB path
DB_FILE = "test_courses_temp.db"
if os.path.exists(DB_FILE):
    try:
        os.remove(DB_FILE)
    except Exception:
        pass

engine = create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestCoursesEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        
        # Create non-ORM tables
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS courses (
                id TEXT PRIMARY KEY,
                title TEXT,
                instructor TEXT,
                rating REAL,
                reviews TEXT,
                duration TEXT,
                thumbnail TEXT,
                description TEXT,
                category TEXT,
                totalModules INTEGER,
                level TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS modules (
                id TEXT PRIMARY KEY,
                courseId TEXT,
                moduleNo INTEGER,
                title TEXT,
                unlockOrder INTEGER
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS lessons (
                id TEXT PRIMARY KEY,
                moduleId TEXT,
                title TEXT,
                youtubeUrl TEXT,
                duration TEXT
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS pdfs (
                id TEXT PRIMARY KEY,
                moduleId TEXT,
                title TEXT,
                pdfUrl TEXT
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS quizzes (
                id TEXT PRIMARY KEY,
                moduleId TEXT,
                title TEXT,
                passPercentage REAL,
                questions_json TEXT
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS written_assessments (
                id TEXT PRIMARY KEY,
                moduleId TEXT,
                title TEXT,
                passPercentage REAL,
                questions_json TEXT
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_interviews (
                id TEXT PRIMARY KEY,
                moduleId TEXT,
                title TEXT,
                passPercentage REAL,
                questions_json TEXT
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT,
                user_id INTEGER,
                progress REAL,
                status TEXT,
                enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                userId INTEGER,
                courseId TEXT,
                moduleId TEXT,
                videoCompleted INTEGER,
                pdfCompleted INTEGER,
                quizCompleted INTEGER,
                writtenCompleted INTEGER,
                interviewCompleted INTEGER,
                moduleUnlocked INTEGER,
                nextModuleUnlocked INTEGER
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT,
                user_id INTEGER,
                code TEXT,
                readiness_score REAL,
                interview_score REAL,
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                quiz_id TEXT,
                score REAL,
                passed INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS written_assessment_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                written_assessment_id TEXT,
                answers_json TEXT,
                score REAL,
                passed INTEGER,
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_interview_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ai_interview_id TEXT,
                transcript_json TEXT,
                knowledge_score REAL,
                communication_score REAL,
                confidence_score REAL,
                interview_score REAL,
                passed INTEGER,
                feedback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Insert initial test user and candidate
        user = User(
            id=1,
            email="test_student@candidate.com",
            password_hash=get_password_hash("password123"),
            full_name="Alex River",
            role="candidate"
        )
        db.add(user)
        db.commit()
        
        candidate = Candidate(id=1, user_id=1, status="Registered", current_step="Profile")
        db.add(candidate)
        db.commit()
        
        # Populate test courses & modules tables
        db.execute(text(
            "INSERT INTO courses (id, title, instructor, rating, reviews, duration, thumbnail, description, category, totalModules, level, status) VALUES "
            "('course_001', 'Python Complete Bootcamp', 'Jose Portilla', 4.9, '14.5k', '12 Hours', 'python.jpg', 'Python description', 'Programming', 1, 'Beginner', 'published')"
        ))
        db.execute(text(
            "INSERT INTO modules (id, courseId, moduleNo, title, unlockOrder) VALUES "
            "('module_course_001_1', 'course_001', 1, 'Basics', 1)"
        ))
        db.execute(text(
            "INSERT INTO lessons (id, moduleId, title, youtubeUrl, duration) VALUES "
            "('lesson_module_course_001_1', 'module_course_001_1', 'Python Intro', 'http://youtube.com', '15 min')"
        ))
        db.execute(text(
            "INSERT INTO pdfs (id, moduleId, title, pdfUrl) VALUES "
            "('pdf_module_course_001_1', 'module_course_001_1', 'Python Cheatsheet', 'http://pdf.com')"
        ))
        # Insert a real quiz question
        db.execute(text(
            "INSERT INTO quizzes (id, moduleId, title, passPercentage, questions_json) VALUES "
            "('quiz_module_course_001_1', 'module_course_001_1', 'Syntax Basics Quiz', 70, '[{\"question\": \"Q1\", \"options\": [\"A\", \"B\"], \"correct_option\": 1}]')"
        ))
        db.execute(text(
            "INSERT INTO written_assessments (id, moduleId, title, passPercentage, questions_json) VALUES "
            "('written_module_course_001_1', 'module_course_001_1', 'Data Types Concept Test', 75, '[]')"
        ))
        db.execute(text(
            "INSERT INTO ai_interviews (id, moduleId, title, passPercentage, questions_json) VALUES "
            "('interview_module_course_001_1', 'module_course_001_1', 'Technical Assessment: Python Basics', 75, '[]')"
        ))
        db.commit()
        db.close()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        if os.path.exists(DB_FILE):
            try:
                os.remove(DB_FILE)
            except Exception:
                pass

    def test_01_get_courses(self):
        res = self.client.get("/api/v1/courses")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "course_001")
        self.assertEqual(data[0]["title"], "Python Complete Bootcamp")

    def test_02_get_curriculum_unauthorized(self):
        res = self.client.get("/api/v1/courses/course_001/curriculum")
        self.assertEqual(res.status_code, 401)

    def get_token(self):
        res = self.client.post("/api/v1/auth/login", data={"username": "test_student@candidate.com", "password": "password123"})
        self.assertEqual(res.status_code, 200)
        return res.json()["access_token"]

    def test_03_courses_flow_authorized(self):
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get enrollments (initially empty)
        res = self.client.get("/api/v1/enrollments", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 0)

        # Get curriculum (should say enrolled=False)
        res = self.client.get("/api/v1/courses/course_001/curriculum", headers=headers)
        self.assertEqual(res.status_code, 200)
        cur = res.json()
        self.assertFalse(cur["enrolled"])
        self.assertEqual(cur["progress"], 0.0)
        self.assertFalse(cur["modules"][0]["unlocked"]) # unlocked = False because not enrolled

        # Enroll in course
        res = self.client.post("/api/v1/courses/course_001/enroll", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["message"], "Enrolled successfully")

        # Get enrollments (should have 1)
        res = self.client.get("/api/v1/enrollments", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]["course_id"], "course_001")

        # Get curriculum (should say enrolled=True, first module unlocked)
        res = self.client.get("/api/v1/courses/course_001/curriculum", headers=headers)
        self.assertEqual(res.status_code, 200)
        cur = res.json()
        self.assertTrue(cur["enrolled"])
        self.assertTrue(cur["modules"][0]["unlocked"])
        self.assertFalse(cur["modules"][0]["video"]["completed"])

        # Complete lesson
        res = self.client.post("/api/v1/lessons/lesson_module_course_001_1/complete", headers=headers)
        self.assertEqual(res.status_code, 200)

        # Check updated progress
        res = self.client.get("/api/v1/courses/course_001/curriculum", headers=headers)
        self.assertEqual(res.status_code, 200)
        cur = res.json()
        self.assertTrue(cur["modules"][0]["video"]["completed"])
        # Total items: 5. 1 completed. Progress: 1/5 = 20%
        self.assertEqual(cur["progress"], 20.0)

        # Complete PDF
        res = self.client.post("/api/v1/pdfs/pdf_module_course_001_1/complete", headers=headers)
        self.assertEqual(res.status_code, 200)

        # Check quiz unlocked
        res = self.client.get("/api/v1/courses/course_001/curriculum", headers=headers)
        self.assertEqual(res.status_code, 200)
        cur = res.json()
        self.assertFalse(cur["modules"][0]["quiz"]["locked"])

        # Submit quiz with correct answer
        res = self.client.post("/api/v1/quiz/quiz_module_course_001_1/submit", json={"answers": "{\"0\": 1}"}, headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["passed"])

        # Check written unlocked
        res = self.client.get("/api/v1/courses/course_001/curriculum", headers=headers)
        self.assertEqual(res.status_code, 200)
        cur = res.json()
        self.assertTrue(cur["modules"][0]["quiz"]["completed"])
        self.assertFalse(cur["modules"][0]["writtenAssessment"]["locked"])

        # Submit written
        res = self.client.post("/api/v1/written/written_module_course_001_1/submit", json={"answers": "{}"}, headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["passed"])

        # Submit interview
        res = self.client.post("/api/v1/interview/interview_module_course_001_1/submit", json={"answers": "{}"}, headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["passed"])

        # Check curriculum fully complete
        res = self.client.get("/api/v1/courses/course_001/curriculum", headers=headers)
        self.assertEqual(res.status_code, 200)
        cur = res.json()
        self.assertEqual(cur["progress"], 100.0)

        # Get certificates (should have 1)
        res = self.client.get("/api/v1/certificates", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]["course_id"], "course_001")
        self.assertEqual(res.json()[0]["course_title"], "Python Complete Bootcamp")

        # Get career readiness
        res = self.client.get("/api/v1/career-readiness", headers=headers)
        self.assertEqual(res.status_code, 200)
        cr = res.json()
        self.assertEqual(cr["courses_completed"], 1)
        self.assertEqual(cr["certificates_earned"], 1)

if __name__ == "__main__":
    unittest.main()
