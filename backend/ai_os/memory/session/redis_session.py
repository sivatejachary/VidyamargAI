import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import redis.asyncio as aioredis

logger = logging.getLogger("ai_os.memory.session.redis_session")

class RedisSessionManager:
    """
    Manages transient session states, active contexts, and chat history.
    """
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client = aioredis.from_url(redis_url, decode_responses=True)
        logger.info("Initializing async Redis session manager connection.")

    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Retrieves session context variables cached in Redis hash."""
        key = f"session:context:{session_id}"
        context_data = await self.client.hgetall(key)
        # Parse nested json strings inside hashes
        parsed_context = {}
        for k, v in context_data.items():
            try:
                parsed_context[k] = json.loads(v)
            except Exception:
                parsed_context[k] = v
        return parsed_context

    async def set_session_context(self, session_id: str, context: Dict[str, Any], expire_seconds: int = 86400):
        """Saves session context variables as Redis hash with an expiration timeout."""
        key = f"session:context:{session_id}"
        serialized_context = {k: json.dumps(v) for k, v in context.items()}
        if serialized_context:
            async with self.client.pipeline(transaction=True) as pipe:
                await pipe.hset(key, mapping=serialized_context)
                await pipe.expire(key, expire_seconds)
                await pipe.execute()
                
    async def append_chat_message(self, session_id: str, role: str, content: str, expire_seconds: int = 86400):
        """Appends a new conversation message to the session list."""
        key = f"session:chat:{session_id}"
        message_payload = json.dumps({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() if 'datetime' in globals() else ""
        })
        async with self.client.pipeline(transaction=True) as pipe:
            await pipe.rpush(key, message_payload)
            await pipe.expire(key, expire_seconds)
            await pipe.execute()

    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent chat conversation history list."""
        key = f"session:chat:{session_id}"
        messages = await self.client.lrange(key, -limit, -1)
        return [json.loads(msg) for msg in messages]

    async def clear_session(self, session_id: str):
        """Deletes session context and chat lists keys."""
        async with self.client.pipeline(transaction=True) as pipe:
            await pipe.delete(f"session:context:{session_id}")
            await pipe.delete(f"session:chat:{session_id}")
            await pipe.execute()
        logger.info(f"Session data deleted for: {session_id}")

    async def close(self):
        """Closes the Redis pool client."""
        await self.client.close()
