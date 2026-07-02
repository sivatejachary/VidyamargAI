from typing import Dict, Any, Type, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.tools.base import BaseAgentTool
from app.tools.registry import tool_registry

class DeduplicationArgs(BaseModel):
    jobs: List[Dict[str, Any]] = Field(..., description="List of job dictionaries to deduplicate.")

class DeduplicationTool(BaseAgentTool):
    """
    Tool to identify and filter duplicate job listings.
    """
    @property
    def name(self) -> str:
        return "deduplicate_jobs"

    @property
    def description(self) -> str:
        return "Identify and remove duplicate job listings from a list of search results based on company name and title similarity."

    @property
    def args_schema(self) -> Type[BaseModel]:
        return DeduplicationArgs

    async def _run(self, db: Session, user_id: int, args: DeduplicationArgs, **kwargs) -> Any:
        seen_keys = set()
        deduplicated = []
        
        for job in args.jobs:
            title = job.get("title", "").lower().strip()
            company = job.get("company_name", "").lower().strip()
            
            # Simple normalization key: first 3 words of title + company name
            title_words = " ".join(title.split()[:3])
            key = f"{company}:{title_words}"
            
            if key not in seen_keys:
                seen_keys.add(key)
                deduplicated.append(job)
                
        return deduplicated

# Register tool
tool_registry.register(DeduplicationTool())
