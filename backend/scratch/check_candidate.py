import os
import sys
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from app.models.models import User, Candidate, CandidateProfile, CandidateResume
from app.models.job_models import ResumeAIAnalysis, CareerEligibilityMatrix
from app.api.routers.resume import get_resume_profile

user = db.query(User).filter(User.email.ilike("j.shivachary@gmail.com")).first()
if not user:
    print("User not found")
    sys.exit(1)

# Call the logic of get_resume_profile directly
candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
if not candidate:
    print("Candidate not found")
    sys.exit(1)

profile = db.query(CandidateProfile).filter(CandidateProfile.candidate_id == candidate.id).order_by(CandidateProfile.created_at.desc()).first()
matrix = db.query(CareerEligibilityMatrix).filter(CareerEligibilityMatrix.candidate_id == candidate.id).first()

from app.api.routers.resume import safe_loads, parse_candidate_experience_level
metadata = safe_loads(profile.parsed_metadata) if profile else {}

def load_json_field(field_val):
    if not field_val:
        return []
    if isinstance(field_val, (list, dict)):
        return field_val
    try:
        return json.loads(field_val)
    except Exception:
        return []

latest_analysis = db.query(ResumeAIAnalysis).filter(ResumeAIAnalysis.candidate_id == candidate.id).order_by(ResumeAIAnalysis.created_at.desc()).first()

analysis_status = {
    "source_type": latest_analysis.source_type if latest_analysis else "GEMINI",
    "confidence_score": latest_analysis.confidence_score if latest_analysis else "HIGH",
    "created_at": latest_analysis.created_at.isoformat() if (latest_analysis and latest_analysis.created_at) else None
}

profile_payload = {
    "personal_info": {
        "name": candidate.parsed_name or user.full_name,
        "email": candidate.parsed_email or user.email,
        "phone": candidate.phone or "",
        "location": candidate.address or "Remote",
        "summary": candidate.summary or ""
    },
    "career_classification": {
        "career_family": matrix.career_family if matrix else (profile.industry if profile else "Engineering"),
        "experience_level": metadata.get("career_level") or (parse_candidate_experience_level(candidate) if candidate else "Mid-Level"),
        "employability_score": metadata.get("employability_score", 80),
        "profile_strength": metadata.get("profile_strength", 75)
    },
    "skills": candidate.skills or "",
    "experience": load_json_field(candidate.experience),
    "education": load_json_field(candidate.education),
    "projects": load_json_field(candidate.projects),
    "certifications": candidate.certifications or "",
    "achievements": load_json_field(candidate.achievements),
    "languages": candidate.languages or "",
    "linkedin": candidate.linkedin or "",
    "github": candidate.github or "",
    "portfolio": candidate.portfolio or "",
    "resume_status": candidate.resume_status,
    "analysis_status": analysis_status
}

print(json.dumps(profile_payload, indent=2))
db.close()
