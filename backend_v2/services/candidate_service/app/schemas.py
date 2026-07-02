from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, EmailStr

class CandidateCreate(BaseModel):
    id: str
    name: str
    email: EmailStr

class CandidateResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True

class ProfileResponse(BaseModel):
    id: str
    candidate_id: str
    summary: Optional[str] = None
    skills_graph: Dict[str, Any]
    experience_graph: List[Dict[str, Any]]
    education_graph: List[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True
