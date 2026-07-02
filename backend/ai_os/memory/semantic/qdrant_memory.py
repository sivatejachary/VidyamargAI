import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

logger = logging.getLogger("ai_os.memory.semantic.qdrant_memory")

class QdrantMemoryManager:
    """
    Client manager for storing and querying vector memories in Qdrant collections.
    """
    def __init__(self, host: str, api_key: Optional[str] = None, port: int = 6333, collection_name: str = "conversational_memory"):
        self.collection_name = collection_name
        self.client = QdrantClient(host=host, port=port, api_key=api_key)
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Initializes target collection if missing."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: '{self.collection_name}' with 768 dimensions and Cosine distance metric.")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
                )
        except Exception as e:
            logger.critical(f"Failed to connect to Qdrant or initialize collection: {e}")

    async def upsert_memory_chunk(
        self,
        candidate_id: str,
        chunk_id: str,
        content: str,
        vector: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Indexes a candidate's memory chunk vector in Qdrant.
        """
        logger.info(f"Upserting semantic memory chunk '{chunk_id}' for candidate '{candidate_id}'")
        
        # Standardize payload fields
        payload = {
            "candidate_id": candidate_id,
            "content": content,
            "metadata": metadata
        }
        
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=chunk_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            logger.info(f"Vector memory chunk '{chunk_id}' successfully upserted.")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert vector memory: {e}")
            return False

    async def search_semantic_memories(
        self,
        candidate_id: str,
        query_vector: List[float],
        limit: int = 5,
        threshold: float = 0.70
    ) -> List[Dict[str, Any]]:
        """
        Queries memories matching the search vector, filtered by candidate ownership.
        """
        logger.info(f"Searching semantic memories for candidate '{candidate_id}' (Limit: {limit})")
        
        # Enforce strict ABAC filter: return only vectors matching this candidate_id
        candidate_filter = Filter(
            must=[
                FieldCondition(
                    key="candidate_id",
                    match=MatchValue(value=candidate_id)
                )
            ]
        )
        
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=candidate_filter,
                limit=limit,
                score_threshold=threshold
            )
            
            return [
                {
                    "chunk_id": str(r.id),
                    "score": r.score,
                    "content": r.payload.get("content", ""),
                    "metadata": r.payload.get("metadata", {})
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Qdrant search query failed: {e}")
            return []
