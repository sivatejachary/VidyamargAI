from typing import List, Optional
from pydantic import BaseModel, Field

class ExperienceItem(BaseModel):
    company: str = Field(..., description="Company Name")
    role: str = Field(..., description="Role Title")
    start_date: str = Field(..., description="Start Date YYYY-MM")
    end_date: str = Field(..., description="End Date YYYY-MM or Present")
    responsibilities: List[str] = Field(default_factory=list)

class EducationItem(BaseModel):
    institution: str = Field(..., description="Institution Name")
    degree: str = Field(..., description="Degree earned")
    field_of_study: str = Field(..., description="Field of study")
    graduation_year: Optional[int] = None

class ResumeProfileSchema(BaseModel):
    summary: str = Field(..., description="Professional profile summary")
    skills: List[str] = Field(default_factory=list, description="Extracted skills list")
    experience: List[ExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
