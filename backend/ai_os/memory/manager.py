import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from .session.redis_session import RedisSessionManager
from .blackboard.blackboard import RedisBlackboard
from .database.checkpoint import CheckpointManager
from .semantic.qdrant_memory import QdrantMemoryManager
from ..schemas.memory import BlackboardMemorySchema, CandidatePreferencesSchema

logger = logging.getLogger("ai_os.memory.manager")

class MemoryManager:
    """
    Unified entrypoint coordinating all platform memory layer operations.
    """
    def __init__(
        self,
        redis_url: str,
        db_session: AsyncSession,
        qdrant_host: str,
        qdrant_api_key: Optional[str] = None
    ):
        self.session = RedisSessionManager(redis_url)
        self.blackboard = RedisBlackboard(self.session.client)
        self.checkpoint = CheckpointManager(db_session)
        self.semantic = QdrantMemoryManager(host=qdrant_host, api_key=qdrant_api_key)
        logger.info("Unified memory manager initialized.")

    async def get_session_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Reads recent chat records."""
        return await self.session.get_chat_history(session_id, limit)

    async def save_session_message(self, session_id: str, role: str, content: str):
        """Appends conversational messages."""
        await self.session.append_chat_message(session_id, role, content)

    async def get_blackboard_state(self, session_id: str) -> BlackboardMemorySchema:
        """Retrieves Blackboard context variables and facts."""
        return await self.blackboard.get_blackboard(session_id)

    async def update_blackboard_variables(self, session_id: str, updates: Dict[str, Any]):
        """Saves variable dictionaries directly to Blackboard."""
        await self.blackboard.update_variables(session_id, updates)

    async def save_agent_checkpoint(self, checkpoint_id: str, session_id: str, state_data: Dict[str, Any], wait_event: Optional[str] = None) -> bool:
        """Serializes current execution graph state to PostgreSQL database."""
        return await self.checkpoint.save_checkpoint(checkpoint_id, session_id, state_data, wait_event)

    async def load_agent_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Loads execution state checkpoint for task resumption."""
        return await self.checkpoint.load_checkpoint(checkpoint_id)

    async def remove_completed_checkpoint(self, checkpoint_id: str) -> bool:
        """Deletes checkpoint record on completion."""
        return await self.checkpoint.delete_checkpoint(checkpoint_id)

    async def index_semantic_memory(self, candidate_id: str, chunk_id: str, content: str, vector: List[float], metadata: Dict[str, Any]) -> bool:
        """Indexes vector memory chunk in Qdrant collection."""
        return await self.semantic.upsert_memory_chunk(candidate_id, chunk_id, content, vector, metadata)

    async def query_semantic_memories(self, candidate_id: str, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Searches candidate semantic memory vectors in Qdrant."""
        return await self.semantic.search_semantic_memories(candidate_id, query_vector, limit=limit)

    async def close(self):
        """Disposes Redis connection pools."""
        await self.session.close()
