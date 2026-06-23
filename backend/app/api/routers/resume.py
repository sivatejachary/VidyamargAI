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


@router.post("/candidates/resume")
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
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
    if not (filename_lower.endswith(".pdf") or filename_lower.endswith(".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX file extensions are allowed.")
        
    # 3. MIME type validation using python-magic
    allowed_mimes = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword"
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

        
    resume = await orchestrator.run_resume_collection_agent(db, candidate.id, content, file.filename, background_tasks)
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




