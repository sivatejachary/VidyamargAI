import json
import logging
from typing import Dict, Any, List, Optional
import redis.asyncio as aioredis
from ...schemas.memory import BlackboardMemorySchema

logger = logging.getLogger("ai_os.memory.blackboard.blackboard")

class RedisBlackboard:
    """
    Thread-safe, cross-node shared Blackboard coordinator stored in Redis.
    """
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    def _get_key(self, session_id: str) -> str:
        return f"blackboard:{session_id}"

    async def get_blackboard(self, session_id: str) -> BlackboardMemorySchema:
        """Retrieves and compiles the active Blackboard memory schema from Redis."""
        key = self._get_key(session_id)
        data = await self.redis.hgetall(key)
        
        variables = json.loads(data.get("variables", "{}"))
        facts = json.loads(data.get("facts", "[]"))
        assumptions = json.loads(data.get("assumptions", "[]"))
        
        return BlackboardMemorySchema(
            session_id=session_id,
            variables=variables,
            facts=facts,
            assumptions=assumptions
        )

    async def update_variables(self, session_id: str, updates: Dict[str, Any]):
        """Updates variable dictionaries stored in the Blackboard."""
        key = self._get_key(session_id)
        current = await self.get_blackboard(session_id)
        current.variables.update(updates)
        
        async with self.redis.pipeline(transaction=True) as pipe:
            await pipe.hset(key, "variables", json.dumps(current.variables))
            await pipe.expire(key, 86400) # Expiration budget: 24h
            await pipe.execute()
        logger.info(f"Blackboard variables updated for session: {session_id}")

    async def add_fact(self, session_id: str, fact: str):
        """Appends a new verified fact to the Blackboard."""
        key = self._get_key(session_id)
        current = await self.get_blackboard(session_id)
        if fact not in current.facts:
            current.facts.append(fact)
            await self.redis.hset(key, "facts", json.dumps(current.facts))
            logger.info(f"Added verified fact to Blackboard: '{fact}'")

    async def add_assumption(self, session_id: str, assumption: str):
        """Appends a new hypothesis assumption to the Blackboard."""
        key = self._get_key(session_id)
        current = await self.get_blackboard(session_id)
        if assumption not in current.assumptions:
            current.assumptions.append(assumption)
            await self.redis.hset(key, "assumptions", json.dumps(current.assumptions))
            logger.info(f"Added assumption to Blackboard: '{assumption}'")

    async def clear_blackboard(self, session_id: str):
        """Deletes the Blackboard data key."""
        await self.redis.delete(self._get_key(session_id))
        logger.info(f"Blackboard cleared for session: {session_id}")
