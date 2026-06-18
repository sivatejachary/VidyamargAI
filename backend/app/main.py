import asyncio
import json
import logging
import os
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from starlette.concurrency import run_in_threadpool
from app.core.config import settings
from app.core.database import engine, Base
from app.core.monitoring import db_queries_var, cache_status_var
from app.core.ws import manager
from app.api.endpoints import router as api_router

from sqlalchemy import text

logger = logging.getLogger("app.api")


# Startup database creation and migration helper
def init_db_safely():
    import sys
    import os
    if os.getenv("TESTING") == "true" or "pytest" in sys.modules:
        print("Bypassing database initialization in testing environment.")
        return
    try:
        print("Creating all tables via SQLAlchemy metadata...")
        from app.models import mcp_models
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

            # Auto-seed default tool permissions if empty
            from app.models.mcp_models import ToolPermission
            perms_count = db_session.query(ToolPermission).count()
            if perms_count == 0:
                print("Seeding default ToolPermissions...")
                default_perms = [
                    ToolPermission(role="candidate", tool="ResumeMCPServer", grants="read,write"),
                    ToolPermission(role="candidate", tool="SkillLabMCPServer", grants="read,write"),
                    ToolPermission(role="candidate", tool="JobMCPServer", grants="read,apply"),
                    ToolPermission(role="recruiter", tool="JobMCPServer", grants="read,write"),
                    ToolPermission(role="recruiter", tool="ResumeMCPServer", grants="read"),
                    ToolPermission(role="admin", tool="*", grants="read,write,apply,admin")
                ]
                for p in default_perms:
                    db_session.add(p)
                db_session.commit()
                print("Default ToolPermissions seeded successfully.")
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
                    totalmodules INTEGER DEFAULT 0,
                    level VARCHAR DEFAULT 'Beginner',
                    status VARCHAR DEFAULT 'published',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS modules (
                    id VARCHAR PRIMARY KEY,
                    courseid VARCHAR,
                    title VARCHAR NOT NULL,
                    moduleno INTEGER DEFAULT 1,
                    unlockorder INTEGER DEFAULT 1,
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
                    topicid VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    youtubeurl VARCHAR,
                    duration VARCHAR
                )
            """))
            # pdfs table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS pdfs (
                    id VARCHAR PRIMARY KEY,
                    topicid VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    pdfurl VARCHAR NOT NULL
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
                    moduleid VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    passpercentage INTEGER,
                    questions_json TEXT NOT NULL
                )
            """))
            # ai_interviews table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS ai_interviews (
                    id VARCHAR PRIMARY KEY,
                    moduleid VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    passpercentage INTEGER,
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
                    moduleid VARCHAR NOT NULL,
                    topicno INTEGER,
                    title VARCHAR NOT NULL,
                    description TEXT,
                    estimatedduration VARCHAR,
                    orderno INTEGER
                )
            """))
            # projects table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS projects (
                    id VARCHAR PRIMARY KEY,
                    courseid VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    description TEXT,
                    difficulty VARCHAR
                )
            """))
            # final_assessments table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS final_assessments (
                    id VARCHAR PRIMARY KEY,
                    courseid VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    passpercentage INTEGER,
                    questions_json TEXT NOT NULL
                )
            """))
            # final_ai_interviews table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS final_ai_interviews (
                    id VARCHAR PRIMARY KEY,
                    courseid VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    passpercentage INTEGER,
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
            
            # ai_mentor_sessions table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS ai_mentor_sessions (
                    id VARCHAR PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title VARCHAR NOT NULL,
                    metadata_json JSONB DEFAULT '{{}}'::jsonb,
                    is_deleted BOOLEAN DEFAULT false,
                    deleted_at TIMESTAMP,
                    is_archived BOOLEAN DEFAULT false,
                    archived_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ai_mentor_session_user ON ai_mentor_sessions(user_id)"))

            # ai_mentor_messages table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS ai_mentor_messages (
                    id VARCHAR PRIMARY KEY,
                    session_id VARCHAR NOT NULL,
                    user_id INTEGER NOT NULL,
                    sender VARCHAR NOT NULL,
                    message TEXT NOT NULL,
                    metadata_json JSONB DEFAULT '{{}}'::jsonb,
                    is_archived BOOLEAN DEFAULT false,
                    archived_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ai_mentor_message_session ON ai_mentor_messages(session_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ai_mentor_message_user ON ai_mentor_messages(user_id)"))

            # ai_mentor_study_plans table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS ai_mentor_study_plans (
                    id VARCHAR PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    duration VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json JSONB DEFAULT '{{}}'::jsonb,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ai_mentor_studyplan_user ON ai_mentor_study_plans(user_id)"))

            # ai_mentor_insights table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS ai_mentor_insights (
                    id VARCHAR PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    insight_type VARCHAR NOT NULL CHECK (insight_type IN ('achievement','warning','recommendation')),
                    title VARCHAR NOT NULL,
                    description TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ai_mentor_insight_user ON ai_mentor_insights(user_id)"))

            # ai_mentor_artifacts table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS ai_mentor_artifacts (
                    id VARCHAR PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    artifact_type VARCHAR NOT NULL CHECK (artifact_type IN ('quiz','notes','challenge','questions')),
                    title VARCHAR NOT NULL,
                    content TEXT NOT NULL,
                    version INTEGER DEFAULT 1 CHECK (version > 0),
                    metadata_json JSONB DEFAULT '{{}}'::jsonb,
                    is_archived BOOLEAN DEFAULT false,
                    archived_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ai_mentor_artifact_user ON ai_mentor_artifacts(user_id)"))

            # ai_mentor_usage table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS ai_mentor_usage (
                    id VARCHAR PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    model_name VARCHAR NOT NULL,
                    prompt_chars INTEGER DEFAULT 0,
                    completion_chars INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ai_mentor_usage_user ON ai_mentor_usage(user_id)"))

            # user_career_profiles table
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS user_career_profiles (
                    id VARCHAR PRIMARY KEY,
                    user_id INTEGER NOT NULL UNIQUE,
                    career_goal VARCHAR DEFAULT 'Frontend Engineer',
                    target_role VARCHAR DEFAULT 'Frontend Developer',
                    target_level VARCHAR DEFAULT 'Mid-Level',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_career_profile_user ON user_career_profiles(user_id)"))


            # Archiving migrations for existing tables
            for tbl in ["ai_mentor_sessions", "ai_mentor_messages", "ai_mentor_artifacts"]:
                try:
                    conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN is_archived BOOLEAN DEFAULT false"))
                except Exception:
                    pass
                try:
                    conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN archived_at TIMESTAMP"))
                except Exception:
                    pass

            # Create full-text GIN search indexes on Postgres
            is_postgres = "postgresql" in str(engine.url).lower()
            if is_postgres:
                try:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ai_mentor_sessions_search ON ai_mentor_sessions USING GIN (to_tsvector('english', title)) WHERE is_archived = FALSE"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ai_mentor_messages_search ON ai_mentor_messages USING GIN (to_tsvector('english', message)) WHERE is_archived = FALSE"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ai_mentor_studyplans_search ON ai_mentor_study_plans USING GIN (to_tsvector('english', content))"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ai_mentor_artifacts_search ON ai_mentor_artifacts USING GIN (to_tsvector('english', content)) WHERE is_archived = FALSE"))
                except Exception as e:
                    print(f"GIN Index creation warning: {e}")

            print("Migration: courses/modules/enrollments/certificates and curriculum tables ensured.")
    except Exception as e:
        print(f"Migration error: {e}")




app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    default_response_class=ORJSONResponse
)

# Sentry initialization (Phase 0)
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    _sentry_dsn = os.getenv("SENTRY_DSN", "")
    if _sentry_dsn:
        sentry_sdk.init(
            dsn=_sentry_dsn,
            environment=os.getenv("ENVIRONMENT", "development"),
            release=os.getenv("GIT_SHA", "local"),
            traces_sample_rate=0.05,
            profiles_sample_rate=0.02,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        )
        logger.info("Sentry initialized")
except ImportError:
    logger.warning("sentry-sdk not installed; Sentry disabled")

# Prometheus metrics configuration moved to run after router inclusion to prevent routing resolution errors


app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.on_event("startup")
async def startup_event():
    init_db_safely()
    
    try:
        from app.core.queue import recover_queued_jobs_on_startup
        recover_queued_jobs_on_startup()
    except Exception as e:
        logger.error(f"Failed to run startup queue recovery: {e}")

    try:
        from app.services.mcp_audit import audit_logger_worker
        from app.services.alerting import start_alert_coordinator
        asyncio.create_task(audit_logger_worker())
        asyncio.create_task(start_alert_coordinator())
        logger.info("Background operational workers (Audit & Alerting) started.")
    except Exception as e:
        logger.error(f"Failed to launch background workers: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Close shared httpx client on application shutdown to release connections."""
    try:
        from app.core.http import http_client
        await http_client.aclose()
    except Exception:
        pass


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

# Performance headers and logging middleware
@app.middleware("http")
async def add_performance_headers(request: Request, call_next):
    db_queries_token = db_queries_var.set(0)
    cache_status_token = cache_status_var.set("BYPASS")
    
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as e:
        db_queries_var.reset(db_queries_token)
        cache_status_var.reset(cache_status_token)
        raise e
        
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    query_count = db_queries_var.get()
    cache_status = cache_status_var.get()
    
    db_queries_var.reset(db_queries_token)
    cache_status_var.reset(cache_status_token)
    
    response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"
    response.headers["X-DB-Queries"] = str(query_count)
    response.headers["X-Cache"] = cache_status
    
    path = request.url.path
    if "/curriculum" in path and elapsed_ms > 300:
        logger.warning(f"Performance Budget Exceeded: GET {path} took {elapsed_ms:.2f}ms (Budget: 300ms, DB Queries: {query_count})")
    elif "/login" in path and elapsed_ms > 500:
        logger.warning(f"Performance Budget Exceeded: POST {path} took {elapsed_ms:.2f}ms (Budget: 500ms, DB Queries: {query_count})")
    elif "/dashboard" in path and elapsed_ms > 500:
        logger.warning(f"Performance Budget Exceeded: GET {path} took {elapsed_ms:.2f}ms (Budget: 500ms, DB Queries: {query_count})")
    elif "/search" in path and elapsed_ms > 800:
        logger.warning(f"Performance Budget Exceeded: GET {path} took {elapsed_ms:.2f}ms (Budget: 800ms, DB Queries: {query_count})")
        
    return response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
        "font-src 'self' data: https:"
    )
    return response

# Attach all API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Prometheus metrics (Phase 0) - Instrument after all routes are attached to prevent router matching issues
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
except ImportError:
    logger.warning("prometheus-fastapi-instrumentator not installed; /metrics disabled")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/health/live")
async def health_live():
    return {"status": "live"}

@app.get("/health/ready")
async def health_ready():
    checks = {}
    # DB check
    try:
        await asyncio.wait_for(
            run_in_threadpool(lambda: engine.connect().execute(text("SELECT 1")).close()),
            timeout=2.0
        )
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"
    # Redis check
    try:
        import redis as _redis
        r = _redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await asyncio.wait_for(run_in_threadpool(r.ping), timeout=2.0)
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
    overall = "ready" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}

@app.get("/health/db")
async def health_db():
    try:
        await asyncio.wait_for(
            run_in_threadpool(lambda: engine.connect().execute(text("SELECT 1")).close()),
            timeout=2.0
        )
        return {"status": "ok", "service": "database"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {e}")

@app.get("/health/redis")
async def health_redis():
    try:
        import redis as _redis
        r = _redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await asyncio.wait_for(run_in_threadpool(r.ping), timeout=2.0)
        return {"status": "ok", "service": "redis"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis error: {e}")

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
