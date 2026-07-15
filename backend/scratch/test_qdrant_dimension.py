import sys
import os
import math
# Resolve absolute path to the parent directory (backend) of the scratch folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.mcp.servers import get_fallback_embedding
from app.services.vector_store import QdrantVectorStore

def test_fallback_dimension():
    print("Testing get_fallback_embedding dimension...")
    emb = get_fallback_embedding("React Developer Python FastAPI")
    print(f"Embedding length: {len(emb)}")
    assert len(emb) == 768, f"Expected 768 dimensions, got {len(emb)}"
    
    # Calculate magnitude
    magnitude = math.sqrt(sum(x * x for x in emb))
    print(f"Vector magnitude: {magnitude:.6f}")
    assert abs(magnitude - 1.0) < 1e-4, f"Vector is not L2-normalized (magnitude: {magnitude})"
    print("[OK] Fallback vector dimension and normalization are correct.")

def test_qdrant_assertion():
    print("Testing Qdrant dimension assertion check...")
    vstore = QdrantVectorStore()
    if vstore.enabled and vstore.client:
        try:
            vstore.init_collections()
            print("[OK] Qdrant collections initialized and verified successfully.")
        except Exception as e:
            print(f"[FAIL] Qdrant initialization threw an error: {e}")
            raise e
    else:
        print("[SKIP] Qdrant is offline or disabled.")

if __name__ == "__main__":
    test_fallback_dimension()
    test_qdrant_assertion()
