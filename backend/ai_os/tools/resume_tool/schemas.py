from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ParseResumeInput(BaseModel):
    candidate_id: str = Field(..., description="Target candidate profile reference ID")
    raw_text: str = Field(..., description="Raw text extracted from uploaded resume file")

class ParseResumeOutput(BaseModel):
    success: bool = Field(..., description="Indicates if parsing completed successfully")
    profile_data: Dict[str, Any] = Field(..., description="Parsed experience, skills, and education details")
    extracted_skills_count: int = Field(..., description="Number of skills extracted from resume")
