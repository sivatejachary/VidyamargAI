"""
Qdrant Vector Store Service — manages semantic embeddings for jobs, resumes, skills, courses, and companies.
Includes robust fallbacks to bypass Qdrant if the server is unconfigured, offline, or library is missing.
"""
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.services.embedding_service import embedding_service

logger = logging.getLogger("app.vector_store")

# Attempt importing qdrant_client. Fall back gracefully.
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, VectorParams, PointStruct
    QDRANT_CLIENT_AVAILABLE = True
except ImportError:
    QDRANT_CLIENT_AVAILABLE = False
    logger.warning("qdrant-client package is not installed. Qdrant functionality will be disabled/bypassed.")

class QdrantVectorStore:
    def __init__(self):
        self.enabled = False
        self.client = None
        if not QDRANT_CLIENT_AVAILABLE:
            return
        
        url = getattr(settings, "QDRANT_URL", "").strip()
        api_key = getattr(settings, "QDRANT_API_KEY", "").strip()
        
        if not url:
            logger.info("QDRANT_URL is not set. Qdrant vector store is disabled.")
            return
            
        try:
            # If API key is provided, use it (Qdrant Cloud/secured self-hosted)
            # otherwise just connect with URL (local self-hosted Qdrant)
            if api_key:
                self.client = QdrantClient(url=url, api_key=api_key, timeout=5.0)
            else:
                self.client = QdrantClient(url=url, timeout=5.0)
            self.enabled = True
            logger.info(f"Qdrant client initialized successfully for URL: {url}")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            self.enabled = False

    def init_collections(self):
        """Initializes collections for: jobs, resumes, skills, courses, companies, candidate_embeddings, job_embeddings, company_embeddings."""
        if not self.enabled or not self.client:
            return
            
        collections = [
            "jobs", "resumes", "skills", "courses", "companies",
            "candidate_embeddings", "job_embeddings", "company_embeddings"
        ]
        for col in collections:
            try:
                # Check if collection exists
                exists = self.client.collection_exists(col)
                if not exists:
                    logger.info(f"Creating Qdrant collection: {col}")
                    self.client.create_collection(
                        collection_name=col,
                        vectors_config=VectorParams(size=768, distance=Distance.COSINE)
                    )
            except Exception as e:
                logger.error(f"Error checking/creating Qdrant collection '{col}': {e}")

    async def upsert_job(self, job_id: int, title: str, company: str, description: str, skills: List[str]) -> bool:
        """Embeds and indexes a job in the 'job_embeddings' and 'jobs' collections using NVIDIA Embeddings."""
        if not self.enabled or not self.client:
            return False
            
        try:
            text = f"Title: {title}\nCompany: {company}\nDescription: {description or ''}\nSkills: {', '.join(skills or [])}"
            vector = await embedding_service.get_nvidia_embedding(text)
            
            import asyncio
            loop = asyncio.get_running_loop()
            
            def _upsert():
                # Upsert to job_embeddings
                self.client.upsert(
                    collection_name="job_embeddings",
                    points=[
                        PointStruct(
                            id=job_id,
                            vector=vector,
                            payload={
                                "job_id": job_id,
                                "title": title,
                                "company": company,
                                "skills": skills
                            }
                        )
                    ]
                )
                # Legacy compatibility
                self.client.upsert(
                    collection_name="jobs",
                    points=[
                        PointStruct(
                            id=job_id,
                            vector=vector,
                            payload={
                                "job_id": job_id,
                                "title": title,
                                "company": company,
                                "skills": skills
                            }
                        )
                    ]
                )
            
            await loop.run_in_executor(None, _upsert)
            return True
        except Exception as e:
            logger.error(f"Failed to upsert job {job_id} to Qdrant: {e}")
            return False

    async def search_jobs(self, resume_text: str, limit: int = 50) -> List[int]:
        """Searches 'job_embeddings' collection using resume embedding and returns matching job IDs."""
        if not self.enabled or not self.client:
            return []
            
        try:
            vector = await embedding_service.get_nvidia_embedding(resume_text)
            return await self.search_jobs_by_vector(vector, limit)
        except Exception as e:
            logger.error(f"Failed to search jobs in Qdrant: {e}")
            return []

    async def search_jobs_by_vector(self, vector: List[float], limit: int = 50) -> List[int]:
        """Searches 'job_embeddings' collection directly using a pre-computed candidate embedding vector."""
        if not self.enabled or not self.client:
            return []
            
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            
            def _search():
                return self.client.search(
                    collection_name="job_embeddings",
                    query_vector=vector,
                    limit=limit
                )
                
            results = await loop.run_in_executor(None, _search)
            job_ids = [r.payload["job_id"] for r in results if r.payload and "job_id" in r.payload]
            return job_ids
        except Exception as e:
            logger.error(f"Failed to search jobs by vector in Qdrant: {e}")
            return []

    async def upsert_resume(self, candidate_id: int, resume_text: str, skills: List[str]) -> bool:
        """Embeds and indexes a candidate's resume/profile in the 'candidate_embeddings' collection using NVIDIA Embeddings."""
        if not self.enabled or not self.client:
            return False
            
        try:
            text = f"Skills: {', '.join(skills or [])}\nProfile: {resume_text}"
            vector = await embedding_service.get_nvidia_embedding(text)
            return await self.upsert_candidate_vector(candidate_id, vector, skills)
        except Exception as e:
            logger.error(f"Failed to upsert resume for candidate {candidate_id} to Qdrant: {e}")
            return False

    async def upsert_candidate_vector(self, candidate_id: int, vector: List[float], skills: List[str]) -> bool:
        """Directly indexes a precomputed candidate embedding vector in Qdrant."""
        if not self.enabled or not self.client:
            return False
            
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            
            def _upsert():
                self.client.upsert(
                    collection_name="candidate_embeddings",
                    points=[
                        PointStruct(
                            id=candidate_id,
                            vector=vector,
                            payload={
                                "candidate_id": candidate_id,
                                "skills": skills
                            }
                        )
                    ]
                )
                # Legacy resumes collection compatibility
                self.client.upsert(
                    collection_name="resumes",
                    points=[
                        PointStruct(
                            id=candidate_id,
                            vector=vector,
                            payload={
                                "candidate_id": candidate_id,
                                "skills": skills
                            }
                        )
                    ]
                )
            
            await loop.run_in_executor(None, _upsert)
            return True
        except Exception as e:
            logger.error(f"Failed to upsert candidate vector for candidate {candidate_id}: {e}")
            return False

    async def upsert_course(self, course_id: int, title: str, description: str, skills: List[str]) -> bool:
        """Embeds and indexes a course in the 'courses' collection."""
        if not self.enabled or not self.client:
            return False
            
        try:
            text = f"Course: {title}\nDescription: {description or ''}\nSkills taught: {', '.join(skills or [])}"
            vector = await embedding_service.get_embedding(text)
            
            import asyncio
            loop = asyncio.get_running_loop()
            
            def _upsert():
                self.client.upsert(
                    collection_name="courses",
                    points=[
                        PointStruct(
                            id=course_id,
                            vector=vector,
                            payload={
                                "course_id": course_id,
                                "title": title,
                                "skills": skills
                            }
                        )
                    ]
                )
            
            await loop.run_in_executor(None, _upsert)
            return True
        except Exception as e:
            logger.error(f"Failed to upsert course {course_id} to Qdrant: {e}")
            return False

    async def upsert_company(self, company_id: int, name: str, description: str) -> bool:
        """Embeds and indexes a company in the 'companies' collection."""
        if not self.enabled or not self.client:
            return False
            
        try:
            text = f"Company: {name}\nDescription: {description or ''}"
            vector = await embedding_service.get_embedding(text)
            
            import asyncio
            loop = asyncio.get_running_loop()
            
            def _upsert():
                self.client.upsert(
                    collection_name="companies",
                    points=[
                        PointStruct(
                            id=company_id,
                            vector=vector,
                            payload={
                                "company_id": company_id,
                                "name": name
                            }
                        )
                    ]
                )
            
            await loop.run_in_executor(None, _upsert)
            return True
        except Exception as e:
            logger.error(f"Failed to upsert company {company_id} to Qdrant: {e}")
            return False

    async def upsert_skill(self, skill_id: int, name: str, category: str) -> bool:
        """Embeds and indexes a skill in the 'skills' collection."""
        if not self.enabled or not self.client:
            return False
            
        try:
            text = f"Skill: {name}\nCategory: {category or ''}"
            vector = await embedding_service.get_embedding(text)
            
            import asyncio
            loop = asyncio.get_running_loop()
            
            def _upsert():
                self.client.upsert(
                    collection_name="skills",
                    points=[
                        PointStruct(
                            id=skill_id,
                            vector=vector,
                            payload={
                                "skill_id": skill_id,
                                "name": name,
                                "category": category
                            }
                        )
                    ]
                )
            
            await loop.run_in_executor(None, _upsert)
            return True
        except Exception as e:
            logger.error(f"Failed to upsert skill {skill_id} to Qdrant: {e}")
            return False

    async def search_jobs_with_scores(self, resume_text: str, limit: int = 50) -> Dict[int, float]:
        """Searches 'job_embeddings' collection using resume embedding and returns a dictionary of job_id -> cosine_similarity score."""
        if not self.enabled or not self.client:
            return {}
            
        try:
            vector = await embedding_service.get_nvidia_embedding(resume_text)
            import asyncio
            loop = asyncio.get_running_loop()
            
            def _search():
                return self.client.search(
                    collection_name="job_embeddings",
                    query_vector=vector,
                    limit=limit
                )
                
            results = await loop.run_in_executor(None, _search)
            scores = {}
            for r in results:
                if r.payload and "job_id" in r.payload:
                    jid = r.payload["job_id"]
                    score_pct = max(0.0, min(100.0, float(r.score) * 100.0))
                    scores[jid] = round(score_pct, 2)
            return scores
        except Exception as e:
            logger.error(f"Failed to search jobs with scores in Qdrant: {e}")
            return {}

    async def get_candidate_vector(self, candidate_id: int) -> Optional[List[float]]:
        """Retrieves a candidate's pre-computed embedding vector from Qdrant."""
        if not self.enabled or not self.client:
            return None
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            
            def _retrieve():
                return self.client.retrieve(
                    collection_name="candidate_embeddings",
                    ids=[candidate_id],
                    with_vectors=True
                )
                
            results = await loop.run_in_executor(None, _retrieve)
            if results and results[0].vector:
                return results[0].vector
        except Exception as e:
            logger.error(f"Failed to retrieve vector for candidate {candidate_id}: {e}")
        return None

# Singleton instance
vector_store = QdrantVectorStore()
