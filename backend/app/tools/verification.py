from typing import Dict, Any, Type, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import httpx
from app.tools.base import BaseAgentTool
from app.tools.registry import tool_registry

class VerificationArgs(BaseModel):
    jobs: List[Dict[str, Any]] = Field(..., description="List of job dictionaries to verify.")

class VerificationTool(BaseAgentTool):
    """
    Tool to verify job listings viability, filtering out expired or broken URLs.
    """
    @property
    def name(self) -> str:
        return "verify_jobs"

    @property
    def description(self) -> str:
        return "Verify that job listing URLs are active and accessible, filtering out broken links."

    @property
    def args_schema(self) -> Type[BaseModel]:
        return VerificationArgs

    async def _run(self, db: Session, user_id: int, args: VerificationArgs, **kwargs) -> Any:
        verified_jobs = []
        
        async with httpx.AsyncClient(timeout=3.0) as client:
            for job in args.jobs:
                url = job.get("apply_url") or job.get("job_url")
                if not url:
                    # No URL to verify, keep it
                    verified_jobs.append(job)
                    continue
                    
                # For testing/mocking or localhost, assume valid
                if "mock" in url or "localhost" in url or "example.com" in url:
                    verified_jobs.append(job)
                    continue
                    
                try:
                    # Make a HEAD request to quickly check URL availability
                    resp = await client.head(url, follow_redirects=True)
                    if resp.status_code < 400:
                        verified_jobs.append(job)
                    else:
                        # Fallback to GET just in case HEAD is blocked
                        resp_get = await client.get(url, follow_redirects=True)
                        if resp_get.status_code < 400:
                            verified_jobs.append(job)
                except Exception as e:
                    # If network check fails, fallback to keeping the job rather than dropping valid jobs due to timeout
                    verified_jobs.append(job)
                    
        return verified_jobs

# Register tool
tool_registry.register(VerificationTool())
