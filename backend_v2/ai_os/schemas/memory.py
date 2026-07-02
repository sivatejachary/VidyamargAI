from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class MemoryChunkSchema(BaseModel):
    chunk_id: str = Field(..., description="Unique memory node UUID")
    candidate_id: str = Field(..., description="Target candidate profile reference")
    content: str = Field(..., description="Raw text context or summary stored")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom tags (e.g. source, category, tags)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CandidatePreferencesSchema(BaseModel):
    locations: List[str] = Field(default_factory=list, description="Target locations preferred (e.g. Bangalore)")
    roles: List[str] = Field(default_factory=list, description="Target professional titles (e.g. ML Engineer)")
    preferred_salary: Optional[float] = Field(default=None, description="Preferred package target index")
    remote_only: bool = Field(default=False)
    excluded_technologies: List[str] = Field(default_factory=list, description="Tech terms to filter out (e.g. PHP)")
    approval_required: bool = Field(default=True, description="Enforces approval card triggers before applying")

class BlackboardMemorySchema(BaseModel):
    session_id: str = Field(..., description="Correlation session key")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Active context properties")
    facts: List[str] = Field(default_factory=list, description="Verified facts derived during execution")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions currently being evaluated")
