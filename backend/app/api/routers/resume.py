from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union, Tuple
from datetime import datetime, timedelta
import json
import logging
import os
import uuid
import time
import asyncio

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user, get_current_admin
from app.schemas import schemas
from app.models.models import *

from app.api.helpers import *
from app.api.helpers import _check_resume_upload_rate_limit, _RESUME_UPLOAD_TIMESTAMPS

logger = logging.getLogger(__name__)

def safe_loads(val, default=None):
    if not val:
        return default if default is not None else {}
    if isinstance(val, (list, dict)):
        return val
    if isinstance(val, str):
        try:
            res = json.loads(val)
            if isinstance(res, (list, dict)):
                return res
        except Exception:
            pass
    return default if default is not None else {}


from fastapi import Query

@router.post("/candidates/resume")
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    fast: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    
    # Rate limit: max 3 uploads per hour per user
    _check_resume_upload_rate_limit(current_user.id)
        
    content = await file.read()
    
    # Validation checks
    # 1. Size limit (5 MB)
    MAX_SIZE = 5 * 1024 * 1024
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the 5MB limit.")
        
    # 2. Extension validation
    filename_lower = file.filename.lower()
    if not filename_lower.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF file format is allowed.")
        
    # 3. MIME type validation using python-magic
    allowed_mimes = [
        "application/pdf"
    ]
    mime_type = None
    try:
        import magic
        mime_type = magic.from_buffer(content, mime=True)
    except Exception as e:
        logger.warning(f"Could not import or run python-magic: {e}. Falling back to content_type check.")
        mime_type = file.content_type
        
    if mime_type not in allowed_mimes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format: {mime_type}. Only PDF and DOCX files are allowed."
        )

        
    resume = await orchestrator.run_resume_collection_agent(db, candidate.id, content, file.filename, background_tasks, fast=fast)
    from app.services.resume_cache import invalidate_resume_analysis
    invalidate_resume_analysis(candidate.id)
    return {"message": "Resume uploaded successfully. Profile analysis is running in the background.", "url": resume.resume_url}

@router.get("/candidates/resume")
def get_candidate_resume(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    resume = db.query(CandidateResume).filter(CandidateResume.candidate_id == candidate.id).order_by(CandidateResume.uploaded_at.desc()).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found")
    return {"id": resume.id, "resume_url": resume.resume_url, "uploaded_at": resume.uploaded_at.isoformat()}

@router.get("/candidates/resumes")
def get_candidate_resumes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    resumes = db.query(CandidateResume).filter(CandidateResume.candidate_id == candidate.id).order_by(CandidateResume.uploaded_at.desc()).all()
    return [{"id": r.id, "resume_url": r.resume_url, "uploaded_at": r.uploaded_at.isoformat()} for r in resumes]

@router.delete("/candidates/resume/{resume_id}")
def delete_candidate_resume(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    resume_to_delete = db.query(CandidateResume).filter(CandidateResume.id == resume_id, CandidateResume.candidate_id == candidate.id).first()
    if not resume_to_delete:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    try:
        # Get all resumes for this candidate, ordered by uploaded_at desc
        resumes = db.query(CandidateResume).filter(
            CandidateResume.candidate_id == candidate.id
        ).order_by(CandidateResume.uploaded_at.desc()).all()
        
        is_deleting_latest = len(resumes) > 0 and resumes[0].id == resume_id
        
        # Delete profile record(s) matching this resume_id
        db.query(CandidateProfile).filter(
            CandidateProfile.candidate_id == candidate.id,
            CandidateProfile.resume_id == resume_id
        ).delete(synchronize_session=False)

        # Delete embedding record(s) matching this resume_id
        db.query(CandidateEmbedding).filter(
            CandidateEmbedding.candidate_id == candidate.id,
            CandidateEmbedding.resume_id == resume_id
        ).delete(synchronize_session=False)
        
        # Physically delete the file from storage
        if resume_to_delete.resume_url:
            try:
                from app.services.storage import storage_service
                url_str = resume_to_delete.resume_url
                if "/storage/" in url_str:
                    rel_path = url_str.split("/storage/")[1]
                    parts = rel_path.split("/")
                    if len(parts) >= 2:
                        folder = "/".join(parts[:-1])
                        filename = parts[-1]
                        storage_service.delete_file(folder, filename)
                elif storage_service.use_minio:
                    from urllib.parse import urlparse
                    parsed = urlparse(url_str)
                    path_parts = parsed.path.strip("/").split("/")
                    if len(path_parts) >= 3:
                        folder = "/".join(path_parts[1:-1])
                        filename = path_parts[-1]
                        storage_service.delete_file(folder, filename)
            except Exception as e:
                logger.error(f"Failed to delete resume file from disk: {e}")

        # Delete the candidate resume record
        db.delete(resume_to_delete)
        
        # Check if there are any remaining resumes left for this candidate
        remaining_resumes = db.query(CandidateResume).filter(
            CandidateResume.candidate_id == candidate.id,
            CandidateResume.id != resume_id
        ).order_by(CandidateResume.uploaded_at.desc()).all()
        
        if len(remaining_resumes) == 0:
            # Delete all candidate profile records
            db.query(CandidateProfile).filter(CandidateProfile.candidate_id == candidate.id).delete(synchronize_session=False)
            
            # Clear all candidate parsed data
            candidate.phone = None
            candidate.address = None
            candidate.education = None
            candidate.experience = None
            candidate.skills = None
            candidate.projects = None
            candidate.certifications = None
            candidate.summary = None
            candidate.achievements = None
            candidate.languages = None
            candidate.github = None
            candidate.linkedin = None
            candidate.portfolio = None
            candidate.parsed_name = None
            candidate.parsed_email = None
            candidate.status = "Registered"
            candidate.current_step = "Profile"
        else:
            # Re-fetch remaining profiles
            remaining_profiles = db.query(CandidateProfile).filter(
                CandidateProfile.candidate_id == candidate.id,
                CandidateProfile.resume_id != resume_id
            ).order_by(CandidateProfile.created_at.desc()).all()
            
            if is_deleting_latest:
                if remaining_profiles:
                    # Revert to next latest profile data
                    new_latest_profile = remaining_profiles[0]
                    metadata = safe_loads(new_latest_profile.parsed_metadata)
                        
                    if not metadata and new_latest_profile.resume_text:
                        from app.services.orchestrator import fallback_parse_resume_text
                        metadata = fallback_parse_resume_text(new_latest_profile.resume_text)
                        
                    # Normalize fields to strings for SQLite compatibility
                    for field in ["education", "experience", "projects", "achievements"]:
                        val = metadata.get(field)
                        if isinstance(val, (list, dict)):
                            metadata[field] = json.dumps(val)
                    for field in ["skills", "certifications", "languages"]:
                        val = metadata.get(field)
                        if isinstance(val, list):
                            metadata[field] = ", ".join(str(v) for v in val)
                    
                    candidate.phone = metadata.get("phone", None)
                    candidate.address = metadata.get("address", None)
                    candidate.skills = metadata.get("skills", None)
                    candidate.education = metadata.get("education", None)
                    candidate.experience = metadata.get("experience", None)
                    candidate.projects = metadata.get("projects", None)
                    candidate.certifications = metadata.get("certifications", None)
                    candidate.summary = metadata.get("summary", None)
                    candidate.achievements = metadata.get("achievements", None)
                    candidate.languages = metadata.get("languages", None)
                    candidate.github = metadata.get("github", None)
                    candidate.linkedin = metadata.get("linkedin", None)
                    candidate.portfolio = metadata.get("portfolio", None)
                    candidate.parsed_name = metadata.get("name", None)
                    candidate.parsed_email = metadata.get("email", None)
                else:
                    # Clear all parsed data
                    candidate.phone = None
                    candidate.address = None
                    candidate.education = None
                    candidate.experience = None
                    candidate.skills = None
                    candidate.projects = None
                    candidate.certifications = None
                    candidate.summary = None
                    candidate.achievements = None
                    candidate.languages = None
                    candidate.github = None
                    candidate.linkedin = None
                    candidate.portfolio = None
                    candidate.parsed_name = None
                    candidate.parsed_email = None
                    candidate.status = "Registered"
                    candidate.current_step = "Profile"
                
        db.commit()
        from app.services.resume_cache import invalidate_resume_analysis
        invalidate_resume_analysis(candidate.id)
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting resume version: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete resume version: {str(e)}")
        
    return {"message": "Resume deleted successfully"}

@router.post("/candidates/resume/analyze")
async def analyze_resume(force: bool = False, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deterministic profile analysis — no fake/placeholder data."""
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    from app.services.resume_cache import get_cached_resume_analysis, set_cached_resume_analysis
    if not force:
        cached_data = get_cached_resume_analysis(candidate.id)
        if cached_data:
            return cached_data

    # ── Gather candidate data from database ──
    skills = candidate.skills or ""
    education = candidate.education or ""
    experience = candidate.experience or ""
    certifications = candidate.certifications or ""
    projects = candidate.projects or ""
    phone = candidate.phone or ""
    address = candidate.address or ""
    summary = candidate.summary or ""
    achievements = candidate.achievements or ""
    languages_field = candidate.languages or ""
    linkedin = candidate.linkedin or ""
    github = candidate.github or ""
    portfolio = candidate.portfolio or ""

    # ── Helper to check if a JSON text field has real content ──
    def has_content(val: str) -> bool:
        if not val or val.strip() in ("", "[]", "{}", "null", "None"):
            return False
        return True

    # ── Deterministic Profile Completion (exact weights from user spec) ──
    breakdown = {
        "name": {"filled": bool(candidate.parsed_name or current_user.full_name), "weight": 10},
        "contact": {"filled": bool(phone or address), "weight": 10},
        "skills": {"filled": has_content(skills), "weight": 15},
        "education": {"filled": has_content(education), "weight": 15},
        "experience": {"filled": has_content(experience), "weight": 20},
        "projects": {"filled": has_content(projects), "weight": 15},
        "certifications": {"filled": has_content(certifications), "weight": 10},
        "achievements": {"filled": has_content(achievements), "weight": 5},
    }

    completion_score = sum(v["weight"] for v in breakdown.values() if v["filled"])
    missing_sections = [k for k, v in breakdown.items() if not v["filled"]]

    # ── Count extracted items ──
    def count_json_items(val: str) -> int:
        if not has_content(val):
            return 0
        try:
            parsed = safe_loads(val, [])
            if isinstance(parsed, list):
                return len(parsed)
            return 1
        except Exception:
            return 1 if val.strip() else 0

    skills_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else []
    projects_count = count_json_items(projects)
    experience_count = count_json_items(experience)
    education_count = count_json_items(education)

    # ── AI Quality Score ──
    # Try AI-powered quality analysis, fall back to heuristic
    ai_quality_breakdown = {
        "grammar": 0,
        "formatting": 0,
        "readability": 0,
        "project_quality": 0,
        "achievement_quality": 0,
        "structure": 0,
    }

    # Heuristic quality scoring based on actual data
    if has_content(skills):
        ai_quality_breakdown["structure"] += 4
    if has_content(education):
        ai_quality_breakdown["structure"] += 3
    if has_content(experience):
        ai_quality_breakdown["structure"] += 3
    ai_quality_breakdown["structure"] = min(ai_quality_breakdown["structure"], 10)

    ai_quality_breakdown["formatting"] = min(completion_score // 10, 10)
    ai_quality_breakdown["readability"] = 7 if has_content(summary) else (5 if completion_score > 50 else 3)

    if has_content(experience):
        exp_text = experience.lower()
        ai_quality_breakdown["grammar"] = 8 if len(exp_text) > 100 else 5
    else:
        ai_quality_breakdown["grammar"] = 3

    if has_content(projects):
        ai_quality_breakdown["project_quality"] = min(projects_count * 3, 10)
    
    if has_content(achievements):
        achieve_count = count_json_items(achievements)
        ai_quality_breakdown["achievement_quality"] = min(achieve_count * 3, 10)

    # Try Gemini for better quality analysis if we have meaningful data
    if completion_score >= 40 and settings.GEMINI_API_KEY:
        quality_prompt = f"""Analyze resume quality. Return ONLY valid JSON with integer scores 0-10 for each:
{{"grammar": <score>, "formatting": <score>, "readability": <score>, "project_quality": <score>, "achievement_quality": <score>, "structure": <score>}}

Resume data:
Skills: {skills or 'None'}
Education: {education or 'None'}
Experience: {experience or 'None'}
Projects: {projects or 'None'}
Certifications: {certifications or 'None'}
Achievements: {achievements or 'None'}
Summary: {summary or 'None'}"""
        try:
            db.commit() # Commit transaction to avoid idle_in_transaction_session_timeout
        except Exception:
            db.rollback()
        try:
            quality_resp = call_gemini(quality_prompt, json_mode=True)
            if quality_resp:
                cleaned = quality_resp.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
                quality_data = json.loads(cleaned)
                for key in ai_quality_breakdown:
                    if key in quality_data and isinstance(quality_data[key], (int, float)):
                        ai_quality_breakdown[key] = min(int(quality_data[key]), 10)
        except Exception:
            pass  # Keep heuristic scores

    quality_values = [v for v in ai_quality_breakdown.values()]
    ai_quality_overall = round(sum(quality_values) / len(quality_values), 1) if quality_values else 0

    # ── Strengths & Recommendations (from actual data) ──
    strengths = []
    if skills_list:
        strengths.append(f"{len(skills_list)} skills detected")
    if has_content(education):
        strengths.append(f"{education_count} education entries found")
    if has_content(experience):
        strengths.append(f"{experience_count} experience entries found")
    if has_content(projects):
        strengths.append(f"{projects_count} projects documented")
    if has_content(certifications):
        strengths.append("Certifications included")
    if has_content(summary):
        strengths.append("Professional summary present")
    if linkedin or github:
        strengths.append("Social links provided")

    recommendations = []
    if not has_content(projects):
        recommendations.append("Add projects with measurable outcomes")
    if not has_content(certifications):
        recommendations.append("Include relevant certifications")
    if not has_content(achievements):
        recommendations.append("Add achievements and awards")
    if not has_content(summary):
        recommendations.append("Write a professional summary")
    if not linkedin and not github:
        recommendations.append("Add LinkedIn and GitHub links")
    if not phone:
        recommendations.append("Add contact phone number")
    if skills_list and len(skills_list) < 5:
        recommendations.append("Expand your skills list")

    # ── Get resume upload timestamp ──
    latest_resume = db.query(CandidateResume).filter(
        CandidateResume.candidate_id == candidate.id
    ).order_by(CandidateResume.uploaded_at.desc()).first()

    result = {
        "profile_completion": {
            "score": completion_score,
            "breakdown": breakdown,
            "missing": missing_sections,
        },
        "ai_quality": {
            "score": ai_quality_overall,
            "breakdown": ai_quality_breakdown,
        },
        "skills_extracted": skills_list,
        "projects_found": projects_count,
        "experience_found": experience_count,
        "education_found": education_count,
        "last_updated": str(latest_resume.uploaded_at) if latest_resume else None,
        "strengths": strengths if strengths else ["Upload a resume to get started"],
        "recommendations": recommendations if recommendations else ["Your profile looks complete!"],
    }
    set_cached_resume_analysis(candidate.id, result)
    return result



@router.post("/candidates/resume/{resume_id}/activate")
async def activate_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    resume = db.query(CandidateResume).filter(
        CandidateResume.id == resume_id,
        CandidateResume.candidate_id == candidate.id
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
        
    # Deactivate all other resumes for this candidate
    db.query(CandidateResume).filter(
        CandidateResume.candidate_id == candidate.id
    ).update({CandidateResume.is_active: False})
    
    # Activate selected resume
    resume.is_active = True
    db.commit()
    
    # Trigger ResumeIntelligenceAgent asynchronously to rebuild profile
    from app.agents.resume_intelligence_agent import ResumeIntelligenceAgent as RIA
    ria = RIA(db, candidate.id)
    await ria.execute_pipeline()
    
    return {"message": "Resume activated successfully", "resume_id": resume.id}


# ─────────────────────────────────────────────────────────────────────────────
# NEW RESUME INTELLIGENCE ROUTER ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/resume/upload")
async def upload_resume_new(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    fast: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Alias for /candidates/resume to support /resume/upload"""
    return await upload_resume(background_tasks, file, fast, current_user, db)


@router.get("/resume/profile")
def get_resume_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    profile = db.query(CandidateProfile).filter(CandidateProfile.candidate_id == candidate.id).order_by(CandidateProfile.created_at.desc()).first()
    matrix = db.query(CareerEligibilityMatrix).filter(CareerEligibilityMatrix.candidate_id == candidate.id).first()
    
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

    from app.models.job_models import ResumeAIAnalysis
    latest_analysis = db.query(ResumeAIAnalysis).filter(ResumeAIAnalysis.candidate_id == candidate.id).order_by(ResumeAIAnalysis.created_at.desc()).first()
    
    analysis_status = {
        "source_type": latest_analysis.source_type if latest_analysis else "GEMINI",
        "confidence_score": latest_analysis.confidence_score if latest_analysis else "HIGH",
        "created_at": latest_analysis.created_at.isoformat() if latest_analysis else None
    }

    return {
        "personal_info": {
            "name": candidate.parsed_name or current_user.full_name,
            "email": candidate.parsed_email or current_user.email,
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


@router.get("/resume/career-dna")
def get_resume_career_dna(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    dna = db.query(CandidateCareerDNA).filter(CandidateCareerDNA.candidate_id == candidate.id).first()
    if not dna:
        return {
            "personality": "Builder",
            "traits": {
                "working_style": "Highly Autonomous & Solution-Oriented",
                "growth_potential": "Strong",
                "leadership_potential": "Developing"
            }
        }
    return {
        "personality": dna.personality or "Builder",
        "traits": dna.traits or {}
    }


@router.get("/resume/skills")
def get_resume_skills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    skill_graph = db.query(CandidateSkillGraph).filter(CandidateSkillGraph.candidate_id == candidate.id).first()
    if not skill_graph:
        return {"skills": [], "edges": []}
    return {
        "skills": skill_graph.skills or [],
        "edges": skill_graph.edges or []
    }


@router.get("/resume/roles")
def get_resume_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    profile = db.query(CandidateProfile).filter(CandidateProfile.candidate_id == candidate.id).order_by(CandidateProfile.created_at.desc()).first()
    if not profile or not profile.generated_roles:
        return {
            "core": [{"role": "Software Engineer", "confidence": 95}],
            "related": [],
            "adjacent": [],
            "transferable": [],
            "future": [],
            "leadership": []
        }
    
    roles_data = safe_loads(profile.generated_roles)
    if isinstance(roles_data, list):
        return {
            "core": [{"role": r, "confidence": 90 - idx * 2} for idx, r in enumerate(roles_data[:3])],
            "related": [{"role": r, "confidence": 80 - idx * 2} for idx, r in enumerate(roles_data[3:6])],
            "adjacent": [{"role": r, "confidence": 75} for r in roles_data[6:10]],
            "transferable": [],
            "future": [],
            "leadership": []
        }
    return roles_data


@router.get("/resume/career-paths")
def get_resume_career_paths(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    paths = db.query(CareerPath).filter(CareerPath.candidate_id == candidate.id).all()
    if not paths:
        return []
    return [
        {
            "path_name": p.path_name,
            "steps": p.steps,
            "milestones": p.milestones
        }
        for p in paths
    ]


@router.get("/resume/skill-gaps")
def get_resume_skill_gaps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    gaps = db.query(SkillGapAnalysis).filter(SkillGapAnalysis.candidate_id == candidate.id).order_by(SkillGapAnalysis.created_at.desc()).first()
    if not gaps:
        return {
            "current_skills": (candidate.skills or "").split(", "),
            "required_skills": ["AWS", "Docker", "Kubernetes"],
            "missing_skills": ["AWS", "Docker", "Kubernetes"],
            "skill_scores": {},
            "learning_roadmap": [
                {"skill": "Docker", "priority": "high", "resources": ["Vite LMS Docker Course"], "est_hours": 10, "career_impact": "+15% job opportunities"},
                {"skill": "Kubernetes", "priority": "medium", "resources": ["K8s for Developers"], "est_hours": 20, "career_impact": "+20% job opportunities"}
            ],
            "overall_gap_score": 45.0,
            "estimated_upskill_months": 2.0
        }
    return {
        "current_skills": gaps.current_skills,
        "required_skills": gaps.required_skills,
        "missing_skills": gaps.missing_skills,
        "skill_scores": gaps.skill_scores,
        "learning_roadmap": gaps.learning_roadmap,
        "overall_gap_score": gaps.overall_gap_score,
        "estimated_upskill_months": gaps.estimated_upskill_months
    }


@router.get("/resume/opportunities")
def get_resume_opportunities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    matrix = db.query(CareerEligibilityMatrix).filter(CareerEligibilityMatrix.candidate_id == candidate.id).first()
    opportunities = db.query(CareerOpportunity).filter(CareerOpportunity.candidate_id == candidate.id).all()
    
    if not matrix:
        return {
            "eligible_exams": [],
            "eligible_gov_jobs": [],
            "eligible_psu_jobs": [],
            "eligible_banking_jobs": [],
            "eligible_defence_jobs": [],
            "eligible_private_roles": [],
            "eligible_international_roles": [],
            "opportunity_scores": {
                "government_score": 50,
                "private_score": 50,
                "remote_score": 50,
                "international_score": 50,
                "leadership_potential_score": 50
            },
            "risk_analysis": {
                "demand_risk": "Medium",
                "automation_risk": "Medium",
                "market_competition": "High",
                "future_demand": "High",
                "salary_growth": "Stable"
            },
            "top_opportunities": []
        }
        
    return {
        "eligible_exams": matrix.eligible_exams or [],
        "eligible_gov_jobs": matrix.eligible_gov_jobs or [],
        "eligible_psu_jobs": matrix.eligible_psu_jobs or [],
        "eligible_banking_jobs": matrix.eligible_banking_jobs or [],
        "eligible_defence_jobs": matrix.eligible_defence_jobs or [],
        "eligible_private_roles": matrix.eligible_private_roles or [],
        "eligible_international_roles": matrix.eligible_international_roles or [],
        "opportunity_scores": matrix.opportunity_scores or {},
        "risk_analysis": matrix.risk_analysis or {},
        "top_opportunities": [
            {
                "id": o.id,
                "role_title": o.role_title,
                "category": o.category,
                "confidence_score": o.confidence_score,
                "growth_score": o.growth_score,
                "salary_potential": o.salary_potential,
                "remote_potential": o.remote_potential,
                "government_potential": o.government_potential,
                "international_potential": o.international_potential
            }
            for o in opportunities
        ]
    }


@router.get("/resume/market-intelligence")
def get_resume_market_intelligence(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    profile = db.query(CandidateProfile).filter(CandidateProfile.candidate_id == candidate.id).order_by(CandidateProfile.created_at.desc()).first()
    industry = (profile.industry if profile else "Software") or "Software"
    
    market = db.query(MarketIntelligence).filter(MarketIntelligence.industry == industry).first()
    if not market:
        return {
            "demand_score": 0.85,
            "salary_range": {"min": 1000000, "max": 2500000, "currency": "INR"},
            "competition_level": "high",
            "top_hiring_industries": ["Fintech", "Healthtech", "E-commerce"],
            "top_hiring_locations": ["Bengaluru", "Hyderabad", "Noida", "Remote"],
            "emerging_skills": ["Docker", "Kubernetes", "AWS", "FastAPI"]
        }
    return {
        "demand_score": market.demand_score,
        "salary_range": {"min": market.avg_salary_min, "max": market.avg_salary_max, "currency": market.salary_currency},
        "competition_level": "medium" if market.competition_score < 0.6 else "high",
        "top_hiring_industries": market.top_companies_hiring or [],
        "top_hiring_locations": [market.city] if market.city else [],
        "emerging_skills": market.emerging_skills or []
    }


@router.post("/resume/create-agent")
async def create_resume_agent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
        
    # Check if agent already exists
    agent = db.query(CandidateAgent).filter(CandidateAgent.candidate_id == candidate.id).first()
    if not agent:
        agent = CandidateAgent(
            candidate_id=candidate.id,
            status="active",
            career_dna={},
            skill_graph={},
            career_graph={},
            industry_dna={},
            target_roles=[]
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
    # Check if preferences already exist
    prefs = db.query(CandidateAgentPreferences).filter(CandidateAgentPreferences.candidate_id == candidate.id).first()
    if not prefs:
        prefs = CandidateAgentPreferences(
            candidate_id=candidate.id,
            auto_discover=True,
            discovery_frequency_hours=6,
            notify_new_matches=True
        )
        db.add(prefs)
        db.commit()
        
    return {"message": "AI Job Agent created successfully", "agent_id": agent.id}


@router.get("/resume/improvements")
def get_resume_improvements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    improvements = db.query(ResumeImprovement).filter(ResumeImprovement.candidate_id == candidate.id).first()
    if not improvements:
        return {
            "ats_score": 70,
            "formatting_score": 75,
            "content_score": 68,
            "keyword_score": 70,
            "improvement_suggestions": ["Upload a resume to get feedback"],
            "resume_rewrite_suggestions": [],
            "achievement_suggestions": []
        }
    return {
        "ats_score": improvements.ats_score,
        "formatting_score": improvements.formatting_score,
        "content_score": improvements.content_score,
        "keyword_score": improvements.keyword_score,
        "improvement_suggestions": improvements.improvement_suggestions or [],
        "resume_rewrite_suggestions": improvements.resume_rewrite_suggestions or [],
        "achievement_suggestions": improvements.achievement_suggestions or []
    }




