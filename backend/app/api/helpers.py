from fastapi import APIRouter
router = APIRouter()
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, get_current_admin
)
from app.core.ws import manager
from app.models.models import (
    User, Candidate, CandidateResume, CandidateProfile,
    Notification, AuditLog, EmailNotification, Message,
    CourseProgress, LearningEvent,
    VideoAnalytics, CourseAnalytics, OTP,
    AIMentorSession, AIMentorMessage, AIMentorStudyPlan, AIMentorInsight, AIMentorArtifact, AIMentorUsage, UserCareerProfile, UserConsent,
    MCPChatSession, MCPChatMessage
)
from fastapi.responses import StreamingResponse
from app.services.mentor_profile import (
    get_learning_health, get_risk_analysis, get_smart_recommendations, trigger_background_insights
)
from app.services.mentor_cache import (
    get_cached_mentor_profile, set_cached_mentor_profile, invalidate_mentor_profile
)

logger = logging.getLogger(__name__)
from app.schemas import schemas
from app.services.orchestrator import orchestrator, call_nvidia, call_gemini
from app.services.storage import storage_service

router = APIRouter()

# Per-user resume upload rate limiting: {user_id: [timestamp, ...]}
# Max 3 resume uploads per hour per user
import time as _time
_RESUME_UPLOAD_TIMESTAMPS: dict = {}
_RESUME_UPLOAD_MAX = 3
_RESUME_UPLOAD_WINDOW = 3600  # 1 hour in seconds

def _check_resume_upload_rate_limit(user_id: int) -> None:
    """Raises HTTPException(429) if the user has exceeded the upload rate limit."""
    now = _time.time()
    window_start = now - _RESUME_UPLOAD_WINDOW
    timestamps = _RESUME_UPLOAD_TIMESTAMPS.get(user_id, [])
    timestamps = [ts for ts in timestamps if ts > window_start]
    if len(timestamps) >= _RESUME_UPLOAD_MAX:
        oldest = timestamps[0]
        retry_in = int(_RESUME_UPLOAD_WINDOW - (now - oldest))
        raise HTTPException(
            status_code=429,
            detail=f"Resume upload rate limit exceeded. You can upload at most {_RESUME_UPLOAD_MAX} resumes per hour. Please retry in {retry_in // 60} min {retry_in % 60} sec."
        )
    timestamps.append(now)
    _RESUME_UPLOAD_TIMESTAMPS[user_id] = timestamps


def parse_candidate_experience_level(candidate) -> str:
    if not candidate:
        return "Mid-Level"
    skills_text = (candidate.skills or "").lower()
    summary_text = (candidate.summary or "").lower()
    exp_text = (candidate.experience or "").lower()

    full_text = f"{skills_text} {summary_text} {exp_text}"

    import re
    match = re.search(r'(\d+)\+?\s*(?:years|yrs)\b', full_text, re.IGNORECASE)
    years = 0
    if match:
        years = int(match.group(1))
    else:
        try:
            exp_list = json.loads(candidate.experience) if candidate.experience else []
            if isinstance(exp_list, list):
                years = len(exp_list) * 2
        except Exception:
            pass

    if years >= 5 or any(k in full_text for k in ["senior", "lead", "principal", "manager", "architect"]):
        return "Senior"
    elif years >= 2 or "mid" in full_text or "associate" in full_text:
        return "Mid-Level"
    else:
        return "Entry-Level"


STATIC_RESUME_PROMPT = """You are VidyaMarg AI Resume Intelligence Engine.

You are an expert Recruiter, Hiring Manager, Talent Intelligence Analyst, Career Strategist, Government Career Advisor, and Workforce Intelligence System.

Analyze the uploaded resume deeply and extract all possible candidate intelligence.

The platform supports all professions, industries, education backgrounds, government sectors, private sectors, certifications, and career paths.

Do not assume the candidate is a software engineer.

Analyze the complete resume and return ONLY valid JSON.

No markdown.

No explanations.

No additional text.

---

OBJECTIVE

Convert the resume into structured intelligence that can be used for:

* Resume Dashboard
* Career Intelligence
* AI Job Agent
* Job Matching
* Career Recommendations
* Skill Gap Analysis
* Learning Recommendations
* Opportunity Discovery

---

EXTRACT PERSONAL INFORMATION
Extract fields: full_name, first_name, last_name, email, phone, location, country, state, city, linkedin_url, github_url, portfolio_url, website_url.

EXTRACT EDUCATION
For each education record extract fields: degree, specialization, institution, university, board, education_level, start_year, end_year, cgpa, percentage, grade, location.

EXTRACT EXPERIENCE
For every experience record extract fields: company_name, job_title, employment_type, industry, location, start_date, end_date, is_current, duration_months, responsibilities, achievements, technologies_used, leadership_indicators.

EXTRACT SKILLS
Group skills into fields: technical_skills, business_skills, domain_skills, government_exam_skills, research_skills, teaching_skills, healthcare_skills, finance_skills, legal_skills, soft_skills, tools, frameworks, platforms, cloud_skills, database_skills, languages.

EXTRACT PROJECTS
For every project extract fields: project_name, description, domain, technologies, tools, business_problem, solution, impact, complexity, team_size, role.

EXTRACT CERTIFICATIONS
For each certification record extract fields: certification_name, provider, category, issue_date, credential_id, level.

EXTRACT ACHIEVEMENTS
For each achievement extract fields: achievement, category, organization, year, impact.

EXTRACT PUBLICATIONS
For each publication extract fields: title, publisher, year, url.

EXTRACT PATENTS
For each patent extract fields: title, year, status.

CAREER INTELLIGENCE
Determine fields: career_family (one of: Government, Private, PSU, Banking, Defence, Teaching, Healthcare, Finance, Legal, Engineering, Business, Research, Agriculture), industry, career_stage, experience_level, leadership_potential, growth_potential, employability_level.

ROLE INTELLIGENCE
Generate core_roles, related_roles, adjacent_roles, transferable_roles, future_roles, leadership_roles, government_roles, international_roles, entrepreneurship_roles. For each role include fields: role_name, reason, matched_skills, confidence.

SKILL GAP ANALYSIS
Determine fields: missing_skills, recommended_skills, recommended_certifications, recommended_projects, learning_priority.

CAREER OPPORTUNITIES
Determine fields: private_job_opportunity, government_job_opportunity, remote_job_opportunity, international_job_opportunity, leadership_opportunity, entrepreneurship_opportunity.

CAREER PATHS
Determine fields: current_stage, next_roles, future_roles, leadership_path.

AI INSIGHTS
Determine fields: best_career_match, top_strength, top_missing_skill, top_recommendation.

---

JSON Structure to return (Strictly output this JSON schema format):
{
  "personal_info": {
    "full_name": "string",
    "first_name": "string",
    "last_name": "string",
    "email": "string",
    "phone": "string",
    "location": "string",
    "country": "string",
    "state": "string",
    "city": "string",
    "linkedin_url": "string",
    "github_url": "string",
    "portfolio_url": "string",
    "website_url": "string"
  },
  "education": [
    {
      "degree": "string",
      "specialization": "string",
      "institution": "string",
      "university": "string",
      "board": "string",
      "education_level": "string",
      "start_year": "string",
      "end_year": "string",
      "cgpa": "string",
      "percentage": "string",
      "grade": "string",
      "location": "string"
    }
  ],
  "experience": [
    {
      "company_name": "string",
      "job_title": "string",
      "employment_type": "string",
      "industry": "string",
      "location": "string",
      "start_date": "string",
      "end_date": "string",
      "is_current": true,
      "duration_months": 0,
      "responsibilities": ["string"],
      "achievements": ["string"],
      "technologies_used": ["string"],
      "leadership_indicators": "string"
    }
  ],
  "skills": {
    "technical_skills": ["string"],
    "business_skills": ["string"],
    "domain_skills": ["string"],
    "government_exam_skills": ["string"],
    "research_skills": ["string"],
    "teaching_skills": ["string"],
    "healthcare_skills": ["string"],
    "finance_skills": ["string"],
    "legal_skills": ["string"],
    "soft_skills": ["string"],
    "tools": ["string"],
    "frameworks": ["string"],
    "platforms": ["string"],
    "cloud_skills": ["string"],
    "database_skills": ["string"],
    "languages": ["string"]
  },
  "projects": [
    {
      "project_name": "string",
      "description": "string",
      "domain": "string",
      "technologies": ["string"],
      "tools": ["string"],
      "business_problem": "string",
      "solution": "string",
      "impact": "string",
      "complexity": "string",
      "team_size": 0,
      "role": "string"
    }
  ],
  "certifications": [
    {
      "certification_name": "string",
      "provider": "string",
      "category": "string",
      "issue_date": "string",
      "credential_id": "string",
      "level": "string"
    }
  ],
  "achievements": [
    {
      "achievement": "string",
      "category": "string",
      "organization": "string",
      "year": "string",
      "impact": "string"
    }
  ],
  "publications": [
    {
      "title": "string",
      "publisher": "string",
      "year": "string",
      "url": "string"
    }
  ],
  "patents": [
    {
      "title": "string",
      "year": "string",
      "status": "string"
    }
  ],
  "career_intelligence": {
    "career_family": "string (strictly select one of: Government, Private, PSU, Banking, Defence, Teaching, Healthcare, Finance, Legal, Engineering, Business, Research, Agriculture)",
    "industry": "string",
    "career_stage": "string",
    "experience_level": "string",
    "leadership_potential": "string",
    "growth_potential": "string",
    "employability_level": 80
  },
  "role_intelligence": {
    "core_roles": [
      {"role_name": "string", "reason": "string", "matched_skills": ["string"], "confidence": 80}
    ],
    "related_roles": [
      {"role_name": "string", "reason": "string", "matched_skills": ["string"], "confidence": 80}
    ],
    "adjacent_roles": [
      {"role_name": "string", "reason": "string", "matched_skills": ["string"], "confidence": 80}
    ],
    "transferable_roles": [
      {"role_name": "string", "reason": "string", "matched_skills": ["string"], "confidence": 80}
    ],
    "future_roles": [
      {"role_name": "string", "reason": "string", "matched_skills": ["string"], "confidence": 80}
    ],
    "leadership_roles": [
      {"role_name": "string", "reason": "string", "matched_skills": ["string"], "confidence": 80}
    ],
    "government_roles": [
      {"role_name": "string", "reason": "string", "matched_skills": ["string"], "confidence": 80}
    ],
    "international_roles": [
      {"role_name": "string", "reason": "string", "matched_skills": ["string"], "confidence": 80}
    ],
    "entrepreneurship_roles": [
      {"role_name": "string", "reason": "string", "matched_skills": ["string"], "confidence": 80}
    ]
  },
  "skill_gap_analysis": {
    "missing_skills": ["string"],
    "recommended_skills": ["string"],
    "recommended_certifications": ["string"],
    "recommended_projects": ["string"],
    "learning_priority": "string"
  },
  "career_opportunities": {
    "private_job_opportunity": 80,
    "government_job_opportunity": 50,
    "remote_job_opportunity": 80,
    "international_job_opportunity": 70,
    "leadership_opportunity": 75,
    "entrepreneurship_opportunity": 60
  },
  "career_paths": {
    "current_stage": "string",
    "next_roles": ["string"],
    "future_roles": ["string"],
    "leadership_path": ["string"]
  },
  "ai_insights": {
    "best_career_match": "string",
    "top_strength": "string",
    "top_missing_skill": "string",
    "top_recommendation": "string"
  }
}
"""

def map_static_intel_to_legacy_schema(intel: dict) -> dict:
    if not isinstance(intel, dict):
        return {}
        
    personal_raw = intel.get("personal_info") or {}
    edu_raw = intel.get("education") or []
    exp_raw = intel.get("experience") or []
    skills_raw = intel.get("skills") or {}
    projects_raw = intel.get("projects") or []
    certs_raw = intel.get("certifications") or []
    classification_raw = intel.get("career_intelligence") or {}
    roles_raw = intel.get("role_intelligence") or {}
    gaps_raw = intel.get("skill_gap_analysis") or {}
    opps_raw = intel.get("career_opportunities") or {}
    paths_raw = intel.get("career_paths") or {}
    insights_raw = intel.get("ai_insights") or {}
    
    # 1. Map personal_info
    personal = {
        "name": personal_raw.get("full_name") or personal_raw.get("name") or "",
        "email": personal_raw.get("email") or "",
        "phone": personal_raw.get("phone") or "",
        "location": personal_raw.get("location") or personal_raw.get("city") or "Remote",
        "summary": insights_raw.get("top_strength") or "",
        "linkedin": personal_raw.get("linkedin_url") or personal_raw.get("linkedin") or "",
        "portfolio": personal_raw.get("portfolio_url") or personal_raw.get("portfolio") or "",
        "github": personal_raw.get("github_url") or personal_raw.get("github") or "",
        "website": personal_raw.get("website_url") or personal_raw.get("website") or ""
    }
    
    # 2. Map education
    education = []
    if isinstance(edu_raw, list):
        for edu in edu_raw:
            if not isinstance(edu, dict): continue
            education.append({
                "degree": edu.get("degree") or "",
                "branch": edu.get("specialization") or "",
                "specialization": edu.get("specialization") or "",
                "institution": edu.get("institution") or "",
                "university": edu.get("university") or edu.get("board") or "",
                "graduation_year": str(edu.get("end_year") or edu.get("start_year") or ""),
                "cgpa": str(edu.get("cgpa") or ""),
                "percentage": str(edu.get("percentage") or ""),
                "academic_performance": edu.get("grade") or "",
                "education_level": edu.get("education_level") or ""
            })
        
    # 3. Map experience
    experience = []
    if isinstance(exp_raw, list):
        for exp in exp_raw:
            if not isinstance(exp, dict): continue
            experience.append({
                "company": exp.get("company_name") or "",
                "role": exp.get("job_title") or "",
                "duration": f"{exp.get('start_date', '')} - {exp.get('end_date', '')}".strip(" -"),
                "industry": exp.get("industry") or "",
                "responsibilities": exp.get("responsibilities") or [],
                "achievements": exp.get("achievements") or [],
                "leadership": exp.get("leadership_indicators") or "",
                "promotions": "",
                "career_progression": "",
                "total_experience": "",
                "relevant_experience": ""
            })
        
    # 4. Map skills list (for legacy "skills" table & graphs)
    skills = []
    skill_names = set()
    if isinstance(skills_raw, dict):
        for cat, list_skills in skills_raw.items():
            if isinstance(list_skills, list):
                for s in list_skills:
                    if s:
                        skill_names.add(str(s).strip())
                    
    # Also fallback to general skills if any
    if isinstance(intel.get("skills"), list):
        for s in intel.get("skills"):
            if isinstance(s, dict) and s.get("name"):
                skill_names.add(str(s.get("name")).strip())
            elif isinstance(s, str):
                skill_names.add(s.strip())
        
    for name in skill_names:
        skills.append({
            "name": name,
            "score": 85,
            "confidence": 90,
            "market_demand": 80,
            "experience_years": 1.0
        })
        
    # Technical skills, business skills, domain skills grouped under skill_intelligence
    skill_intelligence = {
        "technical_skills": skills_raw.get("technical_skills") or [],
        "business_skills": skills_raw.get("business_skills") or [],
        "domain_skills": skills_raw.get("domain_skills") or [],
        "government_exam_skills": skills_raw.get("government_exam_skills") or [],
        "teaching_skills": skills_raw.get("teaching_skills") or [],
        "healthcare_skills": skills_raw.get("healthcare_skills") or [],
        "financial_skills": skills_raw.get("finance_skills") or [],
        "legal_skills": skills_raw.get("legal_skills") or [],
        "research_skills": skills_raw.get("research_skills") or [],
        "soft_skills": skills_raw.get("soft_skills") or [],
        "languages": skills_raw.get("languages") or [],
        "tools": skills_raw.get("tools") or [],
        "frameworks": skills_raw.get("frameworks") or [],
        "platforms": skills_raw.get("platforms") or [],
        "databases": skills_raw.get("database_skills") or [],
        "cloud_technologies": skills_raw.get("cloud_skills") or [],
        "ai_technologies": []
    }
    
    # 5. Map projects
    projects = []
    if isinstance(projects_raw, list):
        for p in projects_raw:
            if not isinstance(p, dict): continue
            projects.append({
                "project_name": p.get("project_name") or "",
                "description": p.get("description") or "",
                "technologies": p.get("technologies") or p.get("tools") or [],
                "complexity": p.get("complexity") or "Medium",
                "industry_domain": p.get("domain") or "",
                "business_impact": p.get("impact") or p.get("solution") or "",
                "leadership_indicators": p.get("role") or "",
                "innovation_indicators": ""
            })
        
    # 6. Map certifications
    certifications = []
    if isinstance(certs_raw, list):
        for c in certs_raw:
            if not isinstance(c, dict): continue
            certifications.append({
                "certification": c.get("certification_name") or "",
                "provider": c.get("provider") or "",
                "category": c.get("category") or "",
                "level": c.get("level") or "",
                "industry_relevance": ""
            })
        
    # 7. Map career_classification
    career_classification = {
        "career_family": classification_raw.get("career_family") or "Private",
        "experience_level": classification_raw.get("experience_level") or "Mid-Level",
        "employability_score": classification_raw.get("employability_level") or 80,
        "profile_strength": 75,
        "classifications": []
    }
    
    # 8. Map roles
    roles = {}
    for cat in ["core", "related", "adjacent", "transferable", "future", "leadership", "government", "international", "entrepreneurship"]:
        roles_list = roles_raw.get(f"{cat}_roles") or []
        roles[cat] = []
        if isinstance(roles_list, list):
            for r in roles_list:
                if not isinstance(r, dict): continue
                roles[cat].append({
                    "role": r.get("role_name") or "",
                    "confidence": r.get("confidence") or 85,
                    "reason": r.get("reason") or ""
                })
            
    # 9. Map opportunities
    opportunities = {
        "eligible_exams": [],
        "eligible_gov_jobs": [],
        "eligible_psu_jobs": [],
        "eligible_banking_jobs": [],
        "eligible_defence_jobs": [],
        "eligible_private_roles": [],
        "eligible_international_roles": [],
        "opportunity_scores": {
            "government_score": opps_raw.get("government_job_opportunity") or 50,
            "private_score": opps_raw.get("private_job_opportunity") or 80,
            "remote_score": opps_raw.get("remote_job_opportunity") or 70,
            "international_score": opps_raw.get("international_job_opportunity") or 60
        }
    }
    
    # 10. Map career_paths
    career_paths = {
        "paths": [
            {
                "path_name": insights_raw.get("best_career_match") or "Core Career Path",
                "steps": paths_raw.get("next_roles") or [],
                "milestones": paths_raw.get("future_roles") or []
            }
        ]
    }
    
    # 11. Map improvements
    improvements = {
        "ats_score": 75,
        "formatting_score": 75,
        "content_score": 75,
        "keyword_score": 75,
        "improvement_suggestions": gaps_raw.get("missing_skills") or [],
        "resume_rewrite_suggestions": gaps_raw.get("recommended_certifications") or [],
        "achievement_suggestions": gaps_raw.get("recommended_projects") or []
    }
    
    return {
        "personal_info": personal,
        "education": education,
        "experience": experience,
        "skill_intelligence": skill_intelligence,
        "skills": skills,
        "skill_graph_edges": [],
        "projects": projects,
        "certifications": certifications,
        "career_classification": career_classification,
        "roles": roles,
        "opportunities": opportunities,
        "career_paths": career_paths,
        "improvements": improvements,
        "risk_analysis": {},
        "raw_static_intel": intel
    }

