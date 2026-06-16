import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.core.ws import manager
from app.api.endpoints import router as api_router

from sqlalchemy import text

# Startup database creation and migration helper
def init_db_safely():
    try:
        print("Creating all tables via SQLAlchemy metadata...")
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully.")
    except Exception as e:
        print(f"Error during Base.metadata.create_all: {e}")
        # If Base creation fails, skip subsequent database queries to avoid crashing
        return

    # Auto-seed external jobs and telegram sources
    try:
        from app.core.database import SessionLocal
        from app.models.models import Job, TelegramSource
        from app.api.endpoints import extract_and_seed_external_jobs
        db_session = SessionLocal()
        try:
            active_jobs_count = db_session.query(Job).filter(Job.status == "active").count()
            if active_jobs_count < 5:
                print("Database has few jobs. Initializing external job extraction from Remotive API...")
                added = extract_and_seed_external_jobs(db_session, limit=20)
                print(f"External job extraction seeded {added} jobs successfully.")
            
            # Auto-seed telegram source
            tg_sources_count = db_session.query(TelegramSource).count()
            if tg_sources_count == 0:
                default_channels = [
                    "freshers_opening",
                    "RisersSquad",
                    "DebugDominators",
                    "walkindrive",
                    "freshers_openings",
                    "CorporateIdeas",
                    "jobsvillaa",
                    "jobupdateschannel",
                    "hiringdaily",
                    "engineerjobsindia",
                    "internseeker",
                    "fresher_offcampus_drives",
                    "jobsinternshipshub",
                    "job4fresherss",
                    "freshershunt",
                    "jobseekeras"
                ]
                print(f"Seeding {len(default_channels)} default Telegram channels...")
                for ch in default_channels:
                    db_session.add(TelegramSource(channel_name=ch, active=True))
                db_session.commit()
                print("Default Telegram channels seeded successfully.")
        except Exception as e:
            print(f"Auto-seed warning: {e}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Auto-seed warning initialization failed: {e}")

    def _get_columns(conn, table_name: str):
        """Return list of column names for a table in PostgreSQL."""
        rows = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :t"
        ), {"t": table_name}).fetchall()
        return [r[0] for r in rows]

    serial = "SERIAL PRIMARY KEY"
    try:
        with engine.begin() as conn:
            conn.execute(text(f"""
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
                    "totalModules" INTEGER DEFAULT 0,
                    level VARCHAR DEFAULT 'Beginner',
                    status VARCHAR DEFAULT 'published',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS modules (
                    id VARCHAR PRIMARY KEY,
                    "courseId" VARCHAR,
                    title VARCHAR NOT NULL,
                    "moduleNo" INTEGER DEFAULT 1,
                    "unlockOrder" INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS enrollments (
                    id {serial},
                    course_id VARCHAR,
                    user_id INTEGER,
                    progress REAL DEFAULT 0.0,
                    status VARCHAR DEFAULT 'active',
                    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS certificates (
                    id {serial},
                    course_id VARCHAR,
                    user_id INTEGER,
                    code VARCHAR,
                    readiness_score REAL DEFAULT 0.0,
                    interview_score REAL DEFAULT 0.0,
                    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # categories table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS categories (
                    id {serial},
                    name VARCHAR NOT NULL UNIQUE,
                    description TEXT
                )
            """))
            # lessons table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS lessons (
                    id VARCHAR PRIMARY KEY,
                    "moduleId" VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    "youtubeUrl" VARCHAR,
                    duration VARCHAR
                )
            """))
            # pdfs table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS pdfs (
                    id VARCHAR PRIMARY KEY,
                    "moduleId" VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    "pdfUrl" VARCHAR NOT NULL
                )
            """))
            # quizzes table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS quizzes (
                    id VARCHAR PRIMARY KEY,
                    "moduleId" VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    "passPercentage" INTEGER,
                    questions_json TEXT NOT NULL
                )
            """))
            # written_assessments table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS written_assessments (
                    id VARCHAR PRIMARY KEY,
                    "moduleId" VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    "passPercentage" INTEGER,
                    questions_json TEXT NOT NULL
                )
            """))
            # ai_interviews table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS ai_interviews (
                    id VARCHAR PRIMARY KEY,
                    "moduleId" VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    "passPercentage" INTEGER,
                    questions_json TEXT NOT NULL
                )
            """))
            # user_progress table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS user_progress (
                    id {serial},
                    "userId" INTEGER NOT NULL,
                    "courseId" VARCHAR NOT NULL,
                    "moduleId" VARCHAR NOT NULL,
                    "videoCompleted" BOOLEAN,
                    "pdfCompleted" BOOLEAN,
                    "quizCompleted" BOOLEAN,
                    "writtenCompleted" BOOLEAN,
                    "interviewCompleted" BOOLEAN,
                    "moduleUnlocked" BOOLEAN,
                    "nextModuleUnlocked" BOOLEAN
                )
            """))
            # topics table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS topics (
                    id VARCHAR PRIMARY KEY,
                    "moduleId" VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    description TEXT,
                    duration VARCHAR,
                    "learningOutcome" TEXT
                )
            """))
            # projects table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS projects (
                    id VARCHAR PRIMARY KEY,
                    "courseId" VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    objective TEXT,
                    requirements TEXT,
                    "acceptanceCriteria" TEXT,
                    "evaluationRubric" TEXT
                )
            """))
            # final_assessments table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS final_assessments (
                    id VARCHAR PRIMARY KEY,
                    "courseId" VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    "passPercentage" INTEGER,
                    questions_json TEXT NOT NULL
                )
            """))
            # final_ai_interviews table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS final_ai_interviews (
                    id VARCHAR PRIMARY KEY,
                    "courseId" VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    "passPercentage" INTEGER,
                    questions_json TEXT NOT NULL
                )
            """))
            # readiness_scores table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS readiness_scores (
                    id VARCHAR PRIMARY KEY,
                    "courseId" VARCHAR NOT NULL,
                    "quizWeight" REAL DEFAULT 25.0,
                    "writtenWeight" REAL DEFAULT 20.0,
                    "interviewWeight" REAL DEFAULT 25.0,
                    "projectWeight" REAL DEFAULT 30.0
                )
            """))
            # quiz_attempts table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS quiz_attempts (
                    id {serial},
                    user_id INTEGER NOT NULL,
                    quiz_id VARCHAR NOT NULL,
                    score REAL NOT NULL,
                    passed BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            # written_assessment_attempts table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS written_assessment_attempts (
                    id {serial},
                    user_id INTEGER NOT NULL,
                    written_assessment_id VARCHAR NOT NULL,
                    answers_json TEXT NOT NULL,
                    score REAL,
                    passed BOOLEAN,
                    feedback TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            # ai_interview_attempts table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS ai_interview_attempts (
                    id {serial},
                    user_id INTEGER NOT NULL,
                    ai_interview_id VARCHAR NOT NULL,
                    transcript_json TEXT NOT NULL,
                    knowledge_score REAL,
                    communication_score REAL,
                    confidence_score REAL,
                    interview_score REAL,
                    passed BOOLEAN,
                    feedback TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            print("Migration: courses/modules/enrollments/certificates and curriculum tables ensured.")
    except Exception as e:
        print(f"Migration error: {e}")




app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.on_event("startup")
def startup_event():
    init_db_safely()


origins = [
    "https://vidyamarg-ai.vercel.app",
    "https://vidyamarg-ai-git-main-shiva-s-projects27.vercel.app",
    "https://vidyamarg-ouhsg53xj-shiva-s-projects27.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.1.7:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://192.168.1.7:3001",
]

# CORS middleware for Next.js portals
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach all API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/db-test")
def db_test():
    import traceback
    try:
        from sqlalchemy import text
        # Try to execute a simple query
        with engine.connect() as conn:
            res = conn.execute(text("SELECT 1")).scalar()
        return {
            "status": "connected",
            "result": res,
            "database_url_masked": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": str(type(e)),
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "database_url_masked": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL
        }

@app.get("/")
def read_root():
    return {"message": "Welcome to HireAI Recruitment Engine"}

# WebSocket endpoint
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            # We just wait for incoming packets or keep connection alive
            data = await websocket.receive_text()
            # If candidate is answering in assessment, or proctoring, broadcast to admins
            try:
                msg = json.loads(data)
                if msg.get("type") == "proctor_event":
                    await manager.broadcast_to_admins({
                        "type": "proctor_alert",
                        "data": {
                            "client_id": client_id,
                            "event": msg.get("event"),
                            "details": msg.get("details")
                        }
                    })
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
