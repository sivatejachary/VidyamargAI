import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.core.ws import manager
from app.api.endpoints import router as api_router

from sqlalchemy import text

# Auto create database tables on start
Base.metadata.create_all(bind=engine)

# Auto-seed external jobs and telegram sources on startup
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

# Run safe SQLite migration check on startup
try:
    with engine.begin() as conn:
        res = conn.execute(text("PRAGMA table_info(candidates)")).fetchall()
        columns = [row[1] for row in res]
        for col_name, col_type in [
            ("hackathon_team", "VARCHAR"),
            ("assigned_mentor", "VARCHAR"),
            ("hackathon_problem", "VARCHAR"),
            ("hackathon_members", "TEXT"),
            ("summary", "TEXT"),
            ("achievements", "TEXT"),
            ("languages", "TEXT"),
        ]:
            if col_name not in columns:
                conn.execute(text(f"ALTER TABLE candidates ADD COLUMN {col_name} {col_type}"))
                print(f"Migration: Added column {col_name} to candidates table.")
                
        # Migrate jobs table
        res_jobs = conn.execute(text("PRAGMA table_info(jobs)")).fetchall()
        job_columns = [row[1] for row in res_jobs]
        for col_name, col_type in [
            ("company_id", "INTEGER"),
            ("recruiter_id", "INTEGER")
        ]:
            if col_name not in job_columns:
                conn.execute(text(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}"))
                print(f"Migration: Added column {col_name} to jobs table.")

        # Create courses/learning tables if missing
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR NOT NULL,
                instructor VARCHAR DEFAULT 'VidyaMarg Team',
                rating REAL DEFAULT 4.5,
                reviews INTEGER DEFAULT 0,
                duration VARCHAR DEFAULT '4 weeks',
                thumbnail VARCHAR,
                description TEXT,
                category VARCHAR DEFAULT 'Technology',
                totalModules INTEGER DEFAULT 0,
                level VARCHAR DEFAULT 'Beginner',
                status VARCHAR DEFAULT 'published',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                courseId INTEGER,
                title VARCHAR NOT NULL,
                moduleNo INTEGER DEFAULT 1,
                unlockOrder INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER,
                user_id INTEGER,
                progress REAL DEFAULT 0.0,
                status VARCHAR DEFAULT 'active',
                enrolled_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER,
                user_id INTEGER,
                code VARCHAR,
                readiness_score REAL DEFAULT 0.0,
                interview_score REAL DEFAULT 0.0,
                earned_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        print("Migration: courses/modules/enrollments/certificates tables ensured.")
except Exception as e:
    print(f"Migration error: {e}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

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
