"""
Embedding Service — generates 768-dimensional semantic embeddings using the Gemini API.
Includes a deterministic mathematical fallback if the Gemini API key is missing or calls fail.
"""
import logging
import httpx
import hashlib
import json
from typing import List
from app.core.config import settings

logger = logging.getLogger("app.embedding_service")


class EmbeddingService:
    """Service to generate vector embeddings for jobs, resumes, and query matching."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"

    async def get_embedding(self, text: str) -> List[float]:
        """
        Retrieves a 768-dimensional embedding from the Gemini API.
        Falls back to a deterministic hashing mechanism on failure or key absence.
        """
        if not text:
            return [0.0] * 768

        if not self.api_key:
            logger.debug("Gemini API key missing. Generating local fallback embedding.")
            return self._generate_fallback_embedding(text)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.endpoint}?key={self.api_key}"
                payload = {
                    "model": "models/gemini-embedding-001",
                    "content": {
                        "parts": [{"text": text}]
                    },
                    "outputDimensionality": 768
                }
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    embedding_values = data.get("embedding", {}).get("values", [])
                    if len(embedding_values) == 768:
                        return embedding_values
                    else:
                        logger.warning(f"Unexpected embedding size {len(embedding_values)}. Falling back.")
                else:
                    logger.warning(f"Gemini embedding API error (status {resp.status_code}): {resp.text}")
        except Exception as exc:
            logger.warning(f"Gemini embedding API call failed: {exc}. Using local fallback.")

        return self._generate_fallback_embedding(text)

    async def get_nvidia_embedding(self, text: str) -> List[float]:
        """
        Retrieves a 768-dimensional embedding from the NVIDIA Embeddings API.
        Falls back to the Gemini embedding API, then to the local hash on failure.
        """
        if not text:
            return [0.0] * 768

        api_key = settings.NVIDIA_API_KEY or settings.NVIDIA_API_KEY_FALLBACK
        if not api_key or str(api_key).strip().lower() in ["", "none", "null", "undefined"]:
            logger.debug("NVIDIA API key missing. Trying Gemini embedding fallback.")
            return await self.get_embedding(text)

        model = "nvidia/nv-embedqa-e5-v5"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://integrate.api.nvidia.com/v1/embeddings"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                payload = {
                    "model": model,
                    "input": [text],
                    "input_type": "query"
                }
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    embedding_values = data.get("data", [{}])[0].get("embedding", [])
                    if len(embedding_values) == 768:
                        return embedding_values
                    elif len(embedding_values) > 768:
                        return embedding_values[:768]
                    elif len(embedding_values) > 0:
                        return embedding_values + [0.0] * (768 - len(embedding_values))
                    else:
                        logger.warning("Empty embedding returned from NVIDIA API. Falling back to Gemini.")
                else:
                    logger.warning(f"NVIDIA embedding API error (status {resp.status_code}): {resp.text}")
        except Exception as exc:
            logger.warning(f"NVIDIA embedding API call failed: {exc}. Falling back to Gemini.")

        return await self.get_embedding(text)

    def _generate_fallback_embedding(self, text: str) -> List[float]:
        """
        Generates a deterministic 768-dimensional vector based on the SHA-256 hash
        of the text, ensuring semantic matches remain consistent during offline test/run.
        """
        embedding = []
        for i in range(24):
            salt = f"chunk_{i}_{text}"
            hasher = hashlib.sha256(salt.encode("utf-8"))
            digest = hasher.digest()
            for byte in digest:
                normalized = (byte / 127.5) - 1.0
                embedding.append(normalized)
        return embedding


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate the cosine similarity between two vectors as a percentage score (0-100)."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    import math
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    similarity = dot_product / (norm_a * norm_b)
    similarity = max(-1.0, min(1.0, similarity))
    return round((similarity + 1.0) * 50.0, 1)


embedding_service = EmbeddingService()
