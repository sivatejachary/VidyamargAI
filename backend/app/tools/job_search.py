from typing import Dict, Any, Type, Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.tools.base import BaseAgentTool
from app.models.job_models import Job
from app.tools.registry import tool_registry

class PostgresJobSearchArgs(BaseModel):
    query: str = Field(..., description="The job title or keywords to search for.")
    location: Optional[str] = Field(None, description="Preferred location of the job.")
    remote_only: bool = Field(False, description="Search only for remote jobs.")
    limit: int = Field(20, description="Maximum number of results to return.")

class PostgresJobSearchTool(BaseAgentTool):
    """
    Tool to perform relational/text search on PostgreSQL jobs table.
    """
    @property
    def name(self) -> str:
        return "postgres_job_search"

    @property
    def description(self) -> str:
        return "Search for jobs in the database using relational filters like title, location, remote status, etc."

    @property
    def args_schema(self) -> Type[BaseModel]:
        return PostgresJobSearchArgs

    @property
    def capabilities(self) -> List[str]:
        return ["postgres_job_search", "job_search"]

    @property
    def priority(self) -> int:
        return 40

    async def _run(self, db: Session, user_id: int, args: PostgresJobSearchArgs, **kwargs) -> Any:
        query_str = args.query.lower().strip()
        q = db.query(Job)
        
        # Filter by query (title or description keywords)
        if query_str:
            q = q.filter(
                (Job.title.ilike(f"%{query_str}%")) | 
                (Job.description.ilike(f"%{query_str}%"))
            )
            
        if args.location:
            loc = args.location.lower().strip()
            q = q.filter(Job.location.ilike(f"%{loc}%"))
            
        if args.remote_only:
            q = q.filter(Job.is_remote == True)
            
        jobs = q.limit(args.limit).all()
        
        # Serialize results
        results = []
        for job in jobs:
            results.append({
                "id": job.id,
                "title": job.title,
                "company_name": job.company_name,
                "location": job.location,
                "is_remote": job.is_remote,
                "description_summary": job.description_summary or (job.description[:200] if job.description else ""),
                "apply_url": job.apply_url,
                "job_url": job.job_url
            })
            
        return results

# Register tool
tool_registry.register(PostgresJobSearchTool())
