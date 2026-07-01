from typing import Dict, Any, Type, Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.tools.base import BaseAgentTool
from app.models.job_models import Job
from app.services.vector_store import vector_store
from app.services.embedding_service import embedding_service, cosine_similarity
from app.tools.registry import tool_registry

class SemanticSearchArgs(BaseModel):
    query: str = Field(..., description="The semantic search query (e.g. resume text or skill set).")
    limit: int = Field(20, description="Maximum number of results to return.")

class SemanticSearchTool(BaseAgentTool):
    """
    Tool to perform semantic vector search on jobs.
    """
    @property
    def name(self) -> str:
        return "semantic_job_search"

    @property
    def description(self) -> str:
        return "Search for jobs semantically based on a query or candidate resume profile."

    @property
    def args_schema(self) -> Type[BaseModel]:
        return SemanticSearchArgs

    @property
    def capabilities(self) -> List[str]:
        return ["semantic_job_search", "job_search"]

    @property
    def priority(self) -> int:
        return 60

    async def _run(self, db: Session, user_id: int, args: SemanticSearchArgs, **kwargs) -> Any:
        # 1. Try vector store search
        job_ids = []
        if vector_store.enabled:
            try:
                job_ids = await vector_store.search_jobs(args.query, limit=args.limit)
            except Exception as e:
                # Log and fallback
                pass
                
        # 2. If vector store was not enabled or returned no results, fallback to relational search
        if not job_ids:
            # Fallback: get candidate embedding and calculate similarities locally with jobs in database
            query_vector = await embedding_service.get_nvidia_embedding(args.query)
            
            # Fetch a pool of active jobs
            jobs_pool = db.query(Job).filter(Job.is_active == True).limit(100).all()
            
            # Calculate mock/local similarities
            scored_jobs = []
            for job in jobs_pool:
                # Get local job embedding vector
                job_text = f"Title: {job.title}\nCompany: {job.company_name}\nDescription: {job.description or ''}"
                job_vector = await embedding_service.get_nvidia_embedding(job_text)
                sim = cosine_similarity(query_vector, job_vector)
                scored_jobs.append((job, sim))
                
            # Sort by similarity descending
            scored_jobs.sort(key=lambda x: x[1], reverse=True)
            results = []
            for job, sim in scored_jobs[:args.limit]:
                results.append({
                    "id": job.id,
                    "title": job.title,
                    "company_name": job.company_name,
                    "location": job.location,
                    "is_remote": job.is_remote,
                    "description_summary": job.description_summary or (job.description[:200] if job.description else ""),
                    "apply_url": job.apply_url,
                    "job_url": job.job_url,
                    "similarity_score": sim
                })
            return results
            
        # If job_ids were found in Qdrant, retrieve the corresponding Job records
        jobs = db.query(Job).filter(Job.id.in_(job_ids)).all()
        
        # Sort jobs to match Qdrant order
        job_map = {job.id: job for job in jobs}
        results = []
        for j_id in job_ids:
            if j_id in job_map:
                job = job_map[j_id]
                results.append({
                    "id": job.id,
                    "title": job.title,
                    "company_name": job.company_name,
                    "location": job.location,
                    "is_remote": job.is_remote,
                    "description_summary": job.description_summary or (job.description[:200] if job.description else ""),
                    "apply_url": job.apply_url,
                    "job_url": job.job_url,
                    "similarity_score": 85.0  # Default mock score if from Qdrant
                })
        return results

# Register tool
tool_registry.register(SemanticSearchTool())
