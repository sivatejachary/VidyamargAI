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

    def _generate_fallback_embedding(self, text: str) -> List[float]:
        """
        Generates a deterministic 768-dimensional vector based on the SHA-256 hash
        of the text, ensuring semantic matches remain consistent during offline test/run.
        """
        embedding = []
        # Create different hash chunks to fill 768 floats (SHA-256 yields 32 bytes/hashes)
        for i in range(24): # 24 chunks * 32 float indices = 768 floats
            salt = f"chunk_{i}_{text}"
            hasher = hashlib.sha256(salt.encode("utf-8"))
            digest = hasher.digest()
            # Convert bytes to floats normalized between -1.0 and 1.0
            for byte in digest:
                normalized = (byte / 127.5) - 1.0
                embedding.append(normalized)
        return embedding


embedding_service = EmbeddingService()
