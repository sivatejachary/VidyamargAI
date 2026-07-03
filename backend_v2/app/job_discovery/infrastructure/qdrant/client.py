"""
VidyaMarg AI — Qdrant Vector Store Client
==========================================
Wraps all Qdrant operations for job embedding indexing and semantic search.
Implements the following resilience guarantees:
  - Connection health check on startup
  - Automatic collection creation with optimal settings
  - Scalar Quantization (int8) for 75% memory reduction
  - Batch upsert with configurable batch size
  - PostgreSQL fallback signaling when Qdrant is offline

IMPORTANT: The Embedding Worker writes to Qdrant.
           The Matching Worker reads from Qdrant ONLY — never generates embeddings.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse

from app.job_discovery import config as cfg
from app.job_discovery.domain.exceptions import QdrantError, QdrantUnavailableError

logger = logging.getLogger("jd.qdrant")

# ---------------------------------------------------------------------------
# Qdrant Collection Configuration
# ---------------------------------------------------------------------------

COLLECTION_CONFIG = {
    "vectors_config": qmodels.VectorParams(
        size=cfg.QDRANT_VECTOR_SIZE,
        distance=qmodels.Distance.COSINE,
        on_disk=True,              # Use disk-backed storage for large collections
    ),
    "quantization_config": qmodels.ScalarQuantization(
        scalar=qmodels.ScalarQuantizationConfig(
            type=qmodels.ScalarType.INT8,
            quantile=0.99,
            always_ram=True,       # Keep quantized index in RAM for fast lookup
        )
    ),
    "optimizers_config": qmodels.OptimizersConfigDiff(
        indexing_threshold=10_000,   # Build HNSW index after 10k vectors
        memmap_threshold=50_000,
    ),
    "hnsw_config": qmodels.HnswConfigDiff(
        m=16,
        ef_construct=200,
        full_scan_threshold=10_000,
    ),
}


class QdrantVectorStore:
    """
    Production Qdrant client wrapper with:
    - Automatic collection initialization
    - Bulk upsert with batching
    - Filtered semantic search
    - Graceful offline degradation
    """

    def __init__(self) -> None:
        self._client: Optional[AsyncQdrantClient] = None
        self._available = False

    async def connect(self) -> None:
        """Initialize Qdrant connection and ensure collection exists."""
        try:
            self._client = AsyncQdrantClient(
                url=cfg.QDRANT_URL,
                api_key=cfg.QDRANT_API_KEY,
                timeout=30,
                prefer_grpc=True,  # gRPC for lower latency in production
            )
            await self._client.get_collections()
            await self._ensure_collection()
            self._available = True
            logger.info(f"Qdrant connected. Collection: {cfg.QDRANT_COLLECTION_NAME}")
        except Exception as exc:
            logger.error(f"Qdrant unavailable: {exc}")
            self._available = False

    async def _ensure_collection(self) -> None:
        """Creates the jobs collection if it doesn't exist."""
        assert self._client is not None
        collections = await self._client.get_collections()
        existing = [c.name for c in collections.collections]
        if cfg.QDRANT_COLLECTION_NAME not in existing:
            await self._client.create_collection(
                collection_name=cfg.QDRANT_COLLECTION_NAME,
                **COLLECTION_CONFIG,
            )
            # Create payload indexes for filtered search
            await self._client.create_payload_index(
                collection_name=cfg.QDRANT_COLLECTION_NAME,
                field_name="country",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
            await self._client.create_payload_index(
                collection_name=cfg.QDRANT_COLLECTION_NAME,
                field_name="is_remote",
                field_schema=qmodels.PayloadSchemaType.BOOL,
            )
            await self._client.create_payload_index(
                collection_name=cfg.QDRANT_COLLECTION_NAME,
                field_name="seniority",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
            await self._client.create_payload_index(
                collection_name=cfg.QDRANT_COLLECTION_NAME,
                field_name="role_category",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
            logger.info(f"Created Qdrant collection: {cfg.QDRANT_COLLECTION_NAME}")

    async def upsert_embeddings(
        self,
        points: List[Dict[str, Any]],
    ) -> bool:
        """
        Bulk upserts embedding points to Qdrant.

        Each point must have:
            id: str (UUID or int)
            vector: List[float]
            payload: Dict[str, Any]  (metadata for filtered search)

        Returns True on success, False on failure.
        """
        if not self._available or not self._client:
            raise QdrantUnavailableError("Qdrant is offline. Job flagged for re-indexing.")

        qdrant_points = [
            qmodels.PointStruct(
                id=p["id"],
                vector=p["vector"],
                payload=p.get("payload", {}),
            )
            for p in points
        ]

        # Batch upserts to avoid oversized gRPC payloads
        batch_size = cfg.EMBEDDING_BATCH_SIZE
        for i in range(0, len(qdrant_points), batch_size):
            batch = qdrant_points[i : i + batch_size]
            try:
                await self._client.upsert(
                    collection_name=cfg.QDRANT_COLLECTION_NAME,
                    points=batch,
                    wait=True,  # Synchronous confirmation
                )
                logger.debug(f"Upserted batch of {len(batch)} vectors to Qdrant")
            except Exception as exc:
                logger.error(f"Qdrant upsert failed: {exc}")
                raise QdrantError(f"Qdrant upsert failed: {exc}") from exc

        return True

    async def similarity_search(
        self,
        query_vector: List[float],
        limit: int = 20,
        score_threshold: float = 0.60,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Semantic similarity search against the jobs collection.
        Returns list of (point_id, score, payload) tuples.

        Applies metadata pre-filters before vector search to minimize search space.
        NOTE: NEVER generates embeddings here — only queries existing vectors.
        """
        if not self._available or not self._client:
            raise QdrantUnavailableError("Qdrant offline — falling back to PostgreSQL keyword search.")

        must_conditions: List[qmodels.Condition] = []
        if filters:
            if filters.get("country"):
                must_conditions.append(
                    qmodels.FieldCondition(
                        key="country",
                        match=qmodels.MatchValue(value=filters["country"]),
                    )
                )
            if filters.get("is_remote") is True:
                must_conditions.append(
                    qmodels.FieldCondition(
                        key="is_remote",
                        match=qmodels.MatchValue(value=True),
                    )
                )
            if filters.get("seniority"):
                must_conditions.append(
                    qmodels.FieldCondition(
                        key="seniority",
                        match=qmodels.MatchValue(value=filters["seniority"]),
                    )
                )
            if filters.get("role_category"):
                must_conditions.append(
                    qmodels.FieldCondition(
                        key="role_category",
                        match=qmodels.MatchValue(value=filters["role_category"]),
                    )
                )

        query_filter = qmodels.Filter(must=must_conditions) if must_conditions else None

        try:
            results = await self._client.search(
                collection_name=cfg.QDRANT_COLLECTION_NAME,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
                with_payload=True,
                with_vectors=False,
            )
            return [(str(r.id), r.score, r.payload or {}) for r in results]
        except Exception as exc:
            logger.error(f"Qdrant search failed: {exc}")
            raise QdrantError(f"Qdrant search failed: {exc}") from exc

    async def delete_points(self, point_ids: List[str]) -> None:
        """Removes vector points from the collection (used by cleanup worker)."""
        if not self._available or not self._client:
            return
        try:
            await self._client.delete(
                collection_name=cfg.QDRANT_COLLECTION_NAME,
                points_selector=qmodels.PointIdsList(points=point_ids),
            )
        except Exception as exc:
            logger.error(f"Qdrant delete failed: {exc}")

    async def get_collection_info(self) -> Optional[Dict[str, Any]]:
        """Returns collection stats for monitoring."""
        if not self._available or not self._client:
            return None
        try:
            info = await self._client.get_collection(cfg.QDRANT_COLLECTION_NAME)
            return {
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "status": info.status.value,
            }
        except Exception:
            return None

    async def is_healthy(self) -> bool:
        """Quick health probe for monitoring worker."""
        if not self._available or not self._client:
            return False
        try:
            await self._client.get_collections()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.close()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_qdrant_instance: Optional[QdrantVectorStore] = None


def get_qdrant_store() -> QdrantVectorStore:
    global _qdrant_instance
    if _qdrant_instance is None:
        _qdrant_instance = QdrantVectorStore()
    return _qdrant_instance
