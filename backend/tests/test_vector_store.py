import unittest
from unittest.mock import patch, MagicMock
from app.services.vector_store import QdrantVectorStore, vector_store
from app.services.embedding_service import embedding_service

class TestVectorStore(unittest.IsolatedAsyncioTestCase):
    async def test_fallback_embedding_dimensionality(self):
        """Verify the deterministic fallback embedding yields a 768-dim list of floats."""
        emb = embedding_service._generate_fallback_embedding("Python React Developer")
        self.assertEqual(len(emb), 768)
        self.assertTrue(all(isinstance(v, float) for v in emb))
        
        # Verify it is deterministic
        emb2 = embedding_service._generate_fallback_embedding("Python React Developer")
        self.assertEqual(emb, emb2)

    async def test_qdrant_disabled_by_default(self):
        """Verify vector store handles missing config gracefully and disables itself without throwing errors."""
        # Create a new client instance which should find no QDRANT_URL in default settings
        store = QdrantVectorStore()
        
        # Should be disabled since QDRANT_URL isn't set in tests
        self.assertFalse(store.enabled)
        
        # Calling methods on disabled store should return fallback values without crashing
        res_upsert = await store.upsert_job(1, "Title", "Company", "Desc", ["Python"])
        self.assertFalse(res_upsert)
        
        res_search = await store.search_jobs("Resume text")
        self.assertEqual(res_search, [])

    @patch("app.services.vector_store.QDRANT_CLIENT_AVAILABLE", True)
    @patch("app.services.vector_store.QdrantClient")
    async def test_qdrant_upsert_and_search_mocked(self, mock_qdrant_client_cls):
        """Verify upsert and search call Qdrant API methods correctly when enabled."""
        mock_client = MagicMock()
        mock_qdrant_client_cls.return_value = mock_client
        
        with patch("app.core.config.settings.QDRANT_URL", "http://localhost:6333"):
            store = QdrantVectorStore()
            self.assertTrue(store.enabled)
            
            # Mock collection exists check
            mock_client.collection_exists.return_value = True
            store.init_collections()
            self.assertEqual(mock_client.collection_exists.call_count, 8)
            
            # Test upsert
            mock_embedding = [0.1] * 768
            with patch("app.services.embedding_service.embedding_service.get_embedding", return_value=mock_embedding):
                upsert_res = await store.upsert_job(
                    job_id=101,
                    title="Python Engineer",
                    company="Google",
                    description="Write clean code",
                    skills=["Python"]
                )
                self.assertTrue(upsert_res)
                self.assertEqual(mock_client.upsert.call_count, 2)
                
            # Test search
            mock_search_result = MagicMock()
            mock_search_result.payload = {"job_id": 101}
            mock_client.search.return_value = [mock_search_result]
            
            with patch("app.services.embedding_service.embedding_service.get_embedding", return_value=mock_embedding):
                search_res = await store.search_jobs("Looking for Python Developer roles", limit=5)
                self.assertEqual(search_res, [101])
                mock_client.search.assert_called_once()
