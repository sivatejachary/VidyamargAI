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
from ai_os.agent_runtime.runtime import AgentRuntime
from ai_os.agent_runtime.dispatcher import AgentDispatcher
from ai_os.execution.state_machine import ExecutionStateMachine

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount legacy api router under /api/v1 and candidate service router
app.include_router(legacy_api_router, prefix="/api/v1")
app.include_router(candidate_router)

# Initialize singletons
db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")
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
            logger.info("Database schema migration completed successfully on archive.legacy_mcp_chat_messages.")
    except Exception as e:
        logger.error(f"Failed to run database schema migrations on archive schema: {e}")
        # Fallback to standard table name
        try:
            async with db_manager.engine.begin() as conn:
                await conn.execute(
                    text("ALTER TABLE mcp_chat_messages ADD COLUMN IF NOT EXISTS interactive_card JSON;")
                )
                logger.info("Fallback schema database migration completed successfully.")
        except Exception as e_inner:
            logger.error(f"Failed fallback database migration: {e_inner}")

# WebSockets connection registry
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        logger.info(f"WebSocket client connected: '{client_id}'")

    def disconnect(self, client_id: str, websocket: WebSocket):
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        logger.info(f"WebSocket client disconnected: '{client_id}'")

    async def broadcast_to_client(self, client_id: str, event_payload: dict):
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_json(event_payload)
                except Exception as e:
                    logger.error(f"WebSocket send error to client '{client_id}': {e}")

ws_manager = ConnectionManager()

@app.websocket("/ws/{candidate_id}")
async def websocket_endpoint(websocket: WebSocket, candidate_id: str):
    """Real-time event stream channel for active candidate updates."""
    await ws_manager.connect(candidate_id, websocket)
    try:
        while True:
            # Keep connection alive, listen for ping/pong or client messages
            data = await websocket.receive_text()
            logger.info(f"Received from WebSocket client '{candidate_id}': {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(candidate_id, websocket)

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
