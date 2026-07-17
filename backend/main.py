import os
import logging
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text

# Core packages & services imports
from packages.core_lib.database import DatabaseManager
from packages.core_lib.telemetry import configure_telemetry
from packages.model_client.client import AppAIClient

# AI OS Subsystems imports
from ai_os.kernel import AIOSKernel
from ai_os.memory.manager import MemoryManager

# Microservice routers
from services.candidate_service.app.router import router as candidate_router
from app.api.endpoints import router as legacy_api_router

# Configure logging
configure_telemetry(service_name="vidyamarg-api")
logger = logging.getLogger("vidyamarg.api")

app = FastAPI(
    title="VidyaMarg AI Career OS API",
    description="Asynchronous core operating system and decoupled business service endpoints.",
    version="2.0.0"
)

# CORS middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "https://vidyamarg-ai.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount legacy api router under /api/v1 and candidate service router
app.include_router(legacy_api_router, prefix="/api/v1")
app.include_router(candidate_router)

raw_db_url = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:qPKoMqtzapoyltHQVdheOKyldfbnYrPH@thomas.proxy.rlwy.net:20637/Vidyamargai"
)
if raw_db_url.startswith("postgresql://"):
    db_url = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    db_url = raw_db_url
db_manager = DatabaseManager(database_url=db_url)
ai_client = AppAIClient(api_key=os.getenv("GROQ_API_KEY", "mock_key"))

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
qdrant_host = os.getenv("QDRANT_HOST", "localhost")
qdrant_api_key = os.getenv("QDRANT_API_KEY", None)

memory_manager = MemoryManager(
    redis_url=redis_url,
    db_session=db_manager.session_factory(),
    qdrant_host=qdrant_host,
    qdrant_api_key=qdrant_api_key
)
kernel = AIOSKernel(memory_manager=memory_manager, ai_client=ai_client)

@app.on_event("startup")
async def run_db_migrations():
    """Applies runtime schema corrections to sync remote tables."""
    logger.info("Running startup database schema migrations...")
    try:
        async with db_manager.engine.begin() as conn:
            # Run migration on archive.legacy_mcp_chat_messages table
            await conn.execute(
                text("ALTER TABLE archive.legacy_mcp_chat_messages ADD COLUMN IF NOT EXISTS interactive_card JSON;")
            )
            # Add lifecycle_status and deleted_at to jobs
            await conn.execute(
                text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(50) DEFAULT 'discovered';")
            )
            await conn.execute(
                text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;")
            )
            # Seed job sources
            await conn.execute(
                text("""
                INSERT INTO job_sources (name, display_name, source_type, is_active, priority)
                VALUES 
                    ('linkedin', 'LinkedIn', 'api', true, 2),
                    ('linkedin_posts', 'LinkedIn Posts', 'api', true, 3),
                    ('telegram', 'Telegram', 'api', true, 4),
                    ('naukri', 'Naukri', 'api', true, 5),
                    ('serper_jobs', 'Serper Jobs', 'api', true, 1)
                ON CONFLICT (name) DO UPDATE SET is_active = true;
                """)
            )
            # Deactivate unwanted sources
            await conn.execute(
                text("UPDATE job_sources SET is_active = false WHERE name IN ('remoteok', 'indeed_rss');")
            )
            logger.info("Database schema migration and job source seeding completed successfully.")
    except Exception as e:
        logger.error(f"Failed to run database schema migrations on archive schema: {e}")
        # Fallback to standard table name
        try:
            async with db_manager.engine.begin() as conn:
                await conn.execute(
                    text("ALTER TABLE mcp_chat_messages ADD COLUMN IF NOT EXISTS interactive_card JSON;")
                )
                await conn.execute(
                    text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(50) DEFAULT 'discovered';")
                )
                await conn.execute(
                    text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;")
                )
                 # Seed job sources in fallback
                await conn.execute(
                    text("""
                    INSERT INTO job_sources (name, display_name, source_type, is_active, priority)
                    VALUES 
                        ('linkedin', 'LinkedIn', 'api', true, 2),
                        ('linkedin_posts', 'LinkedIn Posts', 'api', true, 3),
                        ('telegram', 'Telegram', 'api', true, 4),
                        ('naukri', 'Naukri', 'api', true, 5),
                        ('serper_jobs', 'Serper Jobs', 'api', true, 1)
                    ON CONFLICT (name) DO UPDATE SET is_active = true;
                    """)
                )
                # Deactivate unwanted sources in fallback
                await conn.execute(
                    text("UPDATE job_sources SET is_active = false WHERE name IN ('remoteok', 'indeed_rss');")
                )
                logger.info("Fallback schema database migration and job source seeding completed successfully.")
        except Exception as e_inner:
            logger.error(f"Failed fallback database migration: {e_inner}")

@app.get("/api/v1/db-test")
def test_db_connections():
    import psycopg2
    import os
    results = {}
    urls_to_test = {
        "ENV_DATABASE_URL": os.getenv("DATABASE_URL"),
        "INTERNAL_POSTGRES_PORT_5432": "postgresql://postgres:qPKoMqtzapoyltHQVdheOKyldfbnYrPH@postgres:5432/railway",
        "INTERNAL_POSTGRES_PORT_5432_POSTGRES": "postgresql://postgres:qPKoMqtzapoyltHQVdheOKyldfbnYrPH@postgres:5432/postgres",
        "INTERNAL_POSTGRES_INTERNAL_5432": "postgresql://postgres:qPKoMqtzapoyltHQVdheOKyldfbnYrPH@postgres.railway.internal:5432/railway",
        "INTERNAL_POSTGRES_INTERNAL_5432_POSTGRES": "postgresql://postgres:qPKoMqtzapoyltHQVdheOKyldfbnYrPH@postgres.railway.internal:5432/postgres",
        "FALLBACK_THOMAS_PROXY": "postgresql://postgres:qPKoMqtzapoyltHQVdheOKyldfbnYrPH@thomas.proxy.rlwy.net:20637/Vidyamargai",
    }
    
    for name, url in urls_to_test.items():
        if not url:
            results[name] = "Not Configured / Empty"
            continue
        try:
            # Parse postgresql connection parameters
            clean_url = url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")
            auth, rest = clean_url.split("@")
            user, password = auth.split(":")
            host_port, dbname = rest.split("/")
            if ":" in host_port:
                host, port = host_port.split(":")
            else:
                host, port = host_port, 5432
            
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=dbname,
                user=user,
                password=password,
                connect_timeout=3
            )
            cur = conn.cursor()
            cur.execute("SELECT 1;")
            val = cur.fetchone()[0]
            cur.close()
            conn.close()
            results[name] = f"SUCCESS! Query returns: {val}"
        except Exception as e:
            results[name] = f"FAILED: {str(e)}"
            
    return {
        "environment_variables": {k: os.getenv(k) for k in ["DATABASE_URL", "PORT", "ENV", "ENVIRONMENT"]},
        "results": results
    }

@app.on_event("startup")
async def start_event_bus_and_workers():
    logger.info("Initializing Redis EventBus connection...")
    try:

        from app.core.event_bus import event_bus
        await event_bus.connect(redis_url)

        # Start split scheduler
        from app.core.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        logger.error(f"Failed to initialize EventBus, workers, or scheduler: {e}")

@app.on_event("shutdown")
async def shutdown_event_bus_and_workers():
    logger.info("Shutting down background scheduler...")
    try:
        from app.core.scheduler import shutdown_scheduler
        shutdown_scheduler()
    except Exception as e:
        logger.error(f"Failed to shutdown scheduler: {e}")

# WebSocket endpoint — uses the GLOBAL singleton manager from app.core.ws
# so that background agents and workers can broadcast to connected clients.
# The local ws_manager below is intentionally REMOVED to fix the split-registry bug.
@app.websocket("/ws/{candidate_id}")
async def websocket_endpoint(websocket: WebSocket, candidate_id: str):
    """Real-time event stream channel for active candidate updates."""
    from app.core.ws import manager as global_ws_manager
    await global_ws_manager.connect(candidate_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received from WebSocket client '{candidate_id}': {data}")
    except WebSocketDisconnect:
        global_ws_manager.disconnect(candidate_id, websocket)

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Active session key")
    candidate_id: str = Field(..., description="Candidate reference key")
    query: str = Field(..., description="Natural language workspace command query")

@app.post("/tush-ai/chat", status_code=status.HTTP_200_OK)
async def chat_tush_ai(payload: ChatRequest):
    """
    Central natural language control console endpoint.
    Bootstraps the AI OS Kernel to plan, schedule, and execute workflows.
    """
    logger.info(f"Main App: Forwarding chat query to AI OS Kernel for user '{payload.candidate_id}'")
    
    # In production, pull user preferences from DB/Redis session cache
    mock_preferences = {
        "api_key": os.getenv("GROQ_API_KEY", "mock_key"),
        "role": "candidate"
    }

    try:
        # Execute loop
        result = await kernel.execute_goal(
            session_id=payload.session_id,
            candidate_id=payload.candidate_id,
            user_query=payload.query,
            preferences=mock_preferences
        )
        return result
    except Exception as e:
        logger.error(f"Kernel execution error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI OS Kernel failed to execute goal: {str(e)}"
        )
