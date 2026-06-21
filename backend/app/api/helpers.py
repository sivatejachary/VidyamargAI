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
    User, Candidate, CandidateResume, CandidateProfile, Job, Application, ScreeningResult,
    Assessment, AssessmentAttempt, FraudLog, Interview, InterviewResult,
    CandidateRanking, Offer, Notification, AuditLog, EmailNotification, Message,
    Company, Recruiter, LinkedInHiringPost, JobSource, JobMatch, SearchHistory, SavedJob,
    JobAgentRun, JobAgentLog, TelegramSource, CourseProgress, LearningEvent,
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
from app.services.orchestrator import orchestrator, call_nvidia, call_gemini, log_agent_action
from app.services.storage import storage_service

router = APIRouter()

# Import new real-time job services
from app.services.job_connectors import (
    linkedin_jobs, naukri, foundit, internshala, wellfound, hiring_posts
)
from app.services.job_connectors.query_generator import generate_queries
from app.services.job_connectors.base import LiveJob, google_search
from app.services.match_engine import calculate_match
import app.services.job_cache as job_cache

# Global live-job store keyed by stable_id string (for save/apply lookup)
_LIVE_JOB_STORE: dict = {}

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
    # Evict old timestamps outside the window
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


def fetch_live_indian_jobs_yahoo(skills: List[str]) -> List[dict]:
    import urllib.parse
    import re

    jobs = []
    
    if not skills:
        return []
        
    skills_term = " OR ".join([f'"{s}"' for s in skills[:4]])
    query = f'{skills_term} site:linkedin.com/jobs/view OR site:naukri.com/job-listings- "India"'
    
    logger.info(f"Querying Google for Indian Jobs: {query}")
    try:
        results = google_search(query, num_results=15)
        for r in results:
            title_text = r.get("title", "")
            real_link = r.get("url", "")
            snippet = r.get("snippet", "")
            
            if not title_text or not real_link:
                continue
            
            if not ("linkedin.com" in real_link or "naukri.com" in real_link):
                continue
            
            source = "LinkedIn" if "linkedin.com" in real_link else "Naukri"
            
            # Title cleaning
            job_title = title_text
            job_title = re.sub(r'\s*\|\s*LinkedIn.*', '', job_title, flags=re.IGNORECASE)
            job_title = re.sub(r'\s*-\s*Naukri\.com.*', '', job_title, flags=re.IGNORECASE)
            job_title = re.sub(r'\s*-\s*in\.linkedin\.com.*', '', job_title, flags=re.IGNORECASE)
            job_title = re.sub(r'\bLinkedIn\b.*', '', job_title, flags=re.IGNORECASE).strip()
            
            # Company extraction
            company = "Tech Company"
            if "linkedin.com" in real_link:
                path_segment = real_link.split("/view/")[-1].split("?")[0].strip("/")
                path_segment = re.sub(r'-\d+$', '', path_segment)
                if "-at-" in path_segment:
                    company_slug = path_segment.split("-at-")[-1]
                    company = company_slug.replace("-", " ").title()
                elif "-hiring-" in path_segment:
                    company_slug = path_segment.split("-hiring-")[-1]
                    company = company_slug.replace("-", " ").title()
            elif "naukri.com" in real_link:
                path_segment = real_link.split("/job-listings/")[-1].split("?")[0].strip("/")
                path_segment = re.sub(r'-\d+$', '', path_segment)
                parts = path_segment.split("-")
                if len(parts) > 2:
                    company = " ".join(parts[-2:]).title()
            
            if company == "Tech Company" or len(company) < 3:
                if " at " in job_title:
                    parts = job_title.split(" at ", 1)
                    job_title = parts[0].strip()
                    company = parts[1].strip()
                elif " - " in job_title:
                    parts = job_title.split(" - ", 1)
                    job_title = parts[0].strip()
                    company = parts[1].strip()
                    if " - " in company:
                        c_parts = company.split(" - ", 1)
                        company = c_parts[0].strip()
            
            company = re.sub(r'\s+jobs.*', '', company, flags=re.IGNORECASE)
            company = re.sub(r'\s+hiring.*', '', company, flags=re.IGNORECASE)
            company = company.strip(' -|')
            job_title = job_title.strip(' -|')
            
            # Location deduction
            location = "India"
            text_to_search = (title_text + " " + snippet).lower()
            if "bangalore" in text_to_search or "bengaluru" in text_to_search:
                location = "Bangalore, India"
            elif "mumbai" in text_to_search:
                location = "Mumbai, India"
            elif "pune" in text_to_search:
                location = "Pune, India"
            elif "hyderabad" in text_to_search:
                location = "Hyderabad, India"
            elif "chennai" in text_to_search:
                location = "Chennai, India"
            elif "delhi" in text_to_search or "noida" in text_to_search or "gurgaon" in text_to_search:
                location = "Delhi NCR, India"
            elif "remote" in text_to_search:
                location = "Remote, India"
            
            # Match skill
            matched_skills = []
            for s in skills:
                if s.lower() in text_to_search:
                    matched_skills.append(s.title())
            if not matched_skills:
                matched_skills = ["Software Development"]
            
            jobs.append({
                "title": job_title,
                "company": company,
                "description": f"Original listing found on {source}.\n\nDescription Snippet:\n{snippet}\n\nTo view the full details and apply, please visit the official posting at: {real_link}",
                "location": location,
                "tags": matched_skills + [source, "India"],
                "url": real_link
            })
    except Exception as e:
        logger.error(f"Error scraping jobs: {e}")
        
    return jobs

def fetch_live_internet_jobs(skills: List[str] = None) -> List[dict]:
    if not skills:
        skills = ["python", "react", "fastapi"]
    return fetch_live_indian_jobs_yahoo(skills)

def parse_candidate_experience_level(candidate) -> str:
    if not candidate:
        return "Mid-Level"
    skills_text = (candidate.skills or "").lower()
    summary_text = (candidate.summary or "").lower()
    exp_text = (candidate.experience or "").lower()
    
    full_text = f"{skills_text} {summary_text} {exp_text}"
    
    # Try to find years of experience using regex
    import re
    match = re.search(r'(\d+)\+?\s*(?:years|yrs)\b', full_text, re.IGNORECASE)
    years = 0
    if match:
        years = int(match.group(1))
    else:
        # Check if experience JSON contains items
        try:
            import json
            exp_list = json.loads(candidate.experience) if candidate.experience else []
            if isinstance(exp_list, list):
                years = len(exp_list) * 2 # estimate 2 years per job
        except Exception:
            pass
            
    if years >= 5 or any(k in full_text for k in ["senior", "lead", "principal", "manager", "architect"]):
        return "Senior"
    elif years >= 2 or "mid" in full_text or "associate" in full_text:
        return "Mid-Level"
    else:
        return "Entry-Level"

def generate_live_indian_jobs(skills: List[str], experience_level: str = "Mid-Level") -> List[dict]:
    import random
    companies = ["Zomato", "Flipkart", "Swiggy", "Zoho", "Freshworks", "Paytm", "Razorpay", "Ola", "Cred", "TCS", "Infosys", "Wipro", "HCL Tech", "Tech Mahindra"]
    locations = ["Bangalore, India", "Hyderabad, India", "Pune, India", "Mumbai, India", "Chennai, India", "Delhi NCR, India", "Remote, India"]
    
    generated = []
    skills_seed = sum(ord(c) for s in skills for c in s) if skills else 42
    random.seed(skills_seed)
    for i, skill in enumerate(skills[:12]):
        skill_cap = skill.title()
        
        # Select title templates based on candidate's experience level
        if experience_level == "Senior":
            title_templates = [
                f"Senior {skill_cap} Developer",
                f"Lead {skill_cap} Engineer",
                f"Principal {skill_cap} Architect",
                f"Software Engineer - Lead {skill_cap} Platform",
                f"Senior Backend Developer ({skill_cap})",
                f"Lead AI/ML Engineer ({skill_cap})" if skill in ["machine learning", "python", "cnn", "transformers", "llm", "rag", "embeddings"] else f"Lead Full Stack Engineer ({skill_cap})"
            ]
        elif experience_level == "Entry-Level":
            title_templates = [
                f"Junior {skill_cap} Developer",
                f"{skill_cap} Intern",
                f"Graduate Engineer Trainee - {skill_cap}",
                f"Associate Software Engineer ({skill_cap})",
                f"Entry-Level Backend Developer ({skill_cap})",
                f"Junior AI/ML Engineer ({skill_cap})" if skill in ["machine learning", "python", "cnn", "transformers", "llm", "rag", "embeddings"] else f"Junior Full Stack Engineer ({skill_cap})"
            ]
        else: # Mid-Level
            title_templates = [
                f"{skill_cap} Developer",
                f"Software Engineer - {skill_cap} Platform",
                f"Backend Developer ({skill_cap})",
                f"AI/ML Engineer ({skill_cap})" if skill in ["machine learning", "python", "cnn", "transformers", "llm", "rag", "embeddings"] else f"Full Stack Engineer ({skill_cap})"
            ]
            
        title = random.choice(title_templates)
        company = companies[i % len(companies)]
        location = locations[i % len(locations)]
        
        desc = (
            f"We are looking for a highly skilled {title} to join our growing product engineering team at {company}.\n\n"
            f"Key Responsibilities:\n"
            f"- Design, build, and optimize backend/frontend components supporting our core platform.\n"
            f"- Collaborate closely with product managers and cross-functional teams to deploy features.\n"
            f"- Focus heavily on performance, scalability, and code quality using {skill_cap}.\n\n"
            f"Required Qualifications:\n"
            f"- Strong hands-on experience with {skill_cap} and related frameworks.\n"
            f"- Excellent problem solving, algorithms, and system design skills.\n"
            f"- Good communication skills and team player mindset."
        )
        
        generated.append({
            "title": title,
            "company": company,
            "description": desc,
            "location": location,
            "tags": [skill_cap, "Remote", "Software Engineering"],
            "url": f"https://{company.lower()}.com/careers"
        })
        
    return generated


ADMIN_METRICS_JOB_AGENT = {
    "hiring_posts_extracted": 0,
    "duplicate_jobs_removed": 0
}

def calculate_job_match_object(candidate_id: int, job: Job, candidate_skills_list: List[str], cand_exp_level: str, candidate_location: str, cand_education: str, cand_certifications: str) -> JobMatch:
    # 1. Skill Match
    job_skills_list = [s.strip().lower() for s in (job.required_skills or "").split(",") if s.strip()]
    if not job_skills_list:
        skill_match = 70.0
        missing_skills = []
    else:
        matched = [s for s in job_skills_list if any(s in cs or cs in s for cs in candidate_skills_list)]
        skill_match = (len(matched) / len(job_skills_list)) * 100.0 if job_skills_list else 0
        missing_skills = [s.title() for s in job_skills_list if s not in matched]
        
    # 2. Experience Match
    job_exp = job.experience_level or "Mid-Level"
    if cand_exp_level == job_exp:
        exp_match = 100.0
    elif cand_exp_level == "Senior" and job_exp == "Mid-Level":
        exp_match = 90.0
    elif cand_exp_level == "Mid-Level" and job_exp == "Entry-Level":
        exp_match = 90.0
    elif cand_exp_level == "Senior" and job_exp == "Entry-Level":
        exp_match = 80.0
    elif cand_exp_level == "Mid-Level" and job_exp == "Senior":
        exp_match = 50.0
    else:
        exp_match = 20.0
        
    # 3. Location Match
    job_loc_lower = (job.location or "").lower()
    cand_loc_lower = candidate_location.lower()
    if "remote" in job_loc_lower or "remote" in cand_loc_lower:
        location_match = 100.0
    elif cand_loc_lower in job_loc_lower or job_loc_lower in cand_loc_lower:
        location_match = 100.0
    else:
        location_match = 30.0
        
    # 4. Education Match
    edu_lower = cand_education.lower()
    desc_lower = (job.description or "").lower()
    education_match = 50.0
    if "degree" in desc_lower or "bachelor" in desc_lower or "btech" in desc_lower or "mtech" in desc_lower or "ms" in desc_lower:
        if any(term in edu_lower for term in ["b.tech", "btech", "degree", "bachelor", "m.tech", "mtech", "ms", "master"]):
            education_match = 100.0
        else:
            education_match = 30.0
            
    # 5. Project Match
    project_match = 60.0
    
    # 6. Certification Match
    cert_match = 50.0
    if cand_certifications:
        cert_match = 100.0
        
    # Weighted match score
    match_score = (
        (skill_match * 0.4) +
        (exp_match * 0.25) +
        (location_match * 0.15) +
        (project_match * 0.1) +
        (education_match * 0.05) +
        (cert_match * 0.05)
    )
    
    return JobMatch(
        candidate_id=candidate_id,
        job_id=job.id,
        skill_match=skill_match,
        experience_match=exp_match,
        education_match=education_match,
        project_match=project_match,
        certification_match=cert_match,
        location_match=location_match,
        match_score=match_score,
        skills_gap=", ".join(missing_skills)
    )

def calculate_and_save_job_match(db: Session, candidate_id: int, job: Job, candidate_skills_list: List[str], cand_exp_level: str, candidate_location: str, cand_education: str, cand_certifications: str) -> JobMatch:
    match_record = calculate_job_match_object(
        candidate_id, job, candidate_skills_list, cand_exp_level, candidate_location, cand_education, cand_certifications
    )
    db.add(match_record)
    db.commit()
    db.refresh(match_record)
    return match_record

def extract_hiring_post_details_ai(raw_text: str) -> dict:
    # Truncate to 1200 chars — reduces tokens sent to AI, speeds up response, fewer timeouts
    raw_text = raw_text[:1200] if len(raw_text) > 1200 else raw_text
    prompt = f"""You are an expert AI recruiter. Extract structured job details from the following unstructured LinkedIn hiring post. Return ONLY valid JSON with no markdown formatting around it (no ```json).

Post Content:
{raw_text}

JSON Format:
{{
  "title": "<Job Title, default: Software Engineer>",
  "company": "<Company Name, default: Tech Company>",
  "recruiter_name": "<Recruiter Name or null>",
  "recruiter_profile_url": "<Recruiter Profile URL or null>",
  "location": "<Job Location, e.g. Bangalore, India or Remote, India>",
  "experience": "<Experience Required, e.g. Fresher, 1-3 Years, 5+ Years, or null>",
  "skills": ["<Skill 1>", "<Skill 2>"],
  "salary": "<Salary Information or null>",
  "contact_email": "<Contact Email or null>",
  "apply_link": "<Application Link or null>",
  "is_hiring": <true or false, check if this is indeed a post hiring for a job>,
  "is_spam_or_fake": <true or false, check if this is spam, advertising, or fake job description>
}}
"""
    messages = [{"role": "user", "content": prompt}]
    # Try Gemini first (more reliable from Railway infra), NVIDIA as fallback
    result = call_gemini(prompt, json_mode=True)
    
    if not result:
        result = call_nvidia(messages)
        
    if result:
        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            # First try direct parse (single clean JSON object)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                # NVIDIA sometimes returns multiple concatenated JSON objects.
                # Use raw_decode to extract only the first complete one.
                decoder = json.JSONDecoder()
                obj, _ = decoder.raw_decode(cleaned)
                return obj
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}. Raw response: {result}")
            
    return {
        "title": "Software Engineer",
        "company": "Tech Company",
        "recruiter_name": None,
        "recruiter_profile_url": None,
        "location": "India",
        "experience": "Entry-Level",
        "skills": [],
        "salary": None,
        "contact_email": None,
        "apply_link": None,
        "is_hiring": True,
        "is_spam_or_fake": False
    }

def fetch_linkedin_hiring_posts(skills: List[str]) -> List[dict]:
    import urllib.parse
    import re

    posts = []
    
    if not skills:
        return []
        
    skills_term = " OR ".join([f'"{s}"' for s in skills[:3]])
    query = f'{skills_term} "hiring" OR "looking for" OR "job vacancy" site:linkedin.com/posts/ "India"'
    
    logger.info(f"Querying Google for LinkedIn Hiring Posts: {query}")
    try:
        results = google_search(query, num_results=15)
        for r in results:
            title_text = r.get("title", "")
            real_link = r.get("url", "")
            snippet = r.get("snippet", "")
            
            if not title_text or not real_link:
                continue
            
            if "linkedin.com/posts/" not in real_link:
                continue
            
            raw_text = f"{title_text}\n{snippet}"
            posts.append({
                "url": real_link,
                "raw_text": raw_text
            })
    except Exception as e:
        logger.error(f"Error fetching LinkedIn posts: {e}")
        
    return posts

def run_job_collection_agent_sync(db: Session):
    import random
    logger.info("Running hourly Job Collection Agent...")
    
    candidates = db.query(Candidate).all()
    all_skills = set()
    for c in candidates:
        if c.skills:
            for s in c.skills.split(","):
                if s.strip():
                    all_skills.add(s.strip().lower())
                    
    skills_list = list(all_skills)[:8]
    if not skills_list:
        skills_list = ["python", "react", "fastapi", "sql"]
        
    db.close() # Close session during network operations
    
    raw_jobs = fetch_live_indian_jobs_yahoo(skills_list)
    raw_posts = fetch_linkedin_hiring_posts(skills_list)
    
    # Check existing posts before AI processing to avoid checking out DB connections during network calls
    post_urls = [p["url"] for p in raw_posts]
    existing_urls = set()
    if post_urls:
        from app.core.database import SessionLocal
        db_temp = SessionLocal()
        try:
            rows = db_temp.query(LinkedInHiringPost.post_url).filter(LinkedInHiringPost.post_url.in_(post_urls)).all()
            existing_urls = {r[0] for r in rows}
        except Exception as e:
            logger.error(f"Error checking existing posts in database: {e}")
        finally:
            db_temp.close()

    new_posts = [p for p in raw_posts if p["url"] not in existing_urls]
    
    # Process AI extraction offline, completely disconnected from DB connection pool
    processed_posts = []
    for post in new_posts:
        try:
            details = extract_hiring_post_details_ai(post["raw_text"])
            if details.get("is_hiring") and not details.get("is_spam_or_fake"):
                processed_posts.append((post, details))
        except Exception as e:
            logger.error(f"Error extracting hiring post details for {post['url']}: {e}")

    hiring_posts_count = 0
    duplicates_count = 0
    
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        for post, details in processed_posts:
            # Recheck existence inside the write block in case of concurrency
            existing_post = db.query(LinkedInHiringPost).filter(LinkedInHiringPost.post_url == post["url"]).first()
            if existing_post:
                continue
                
            company_name = details.get("company", "Tech Company").strip()
            company = db.query(Company).filter(Company.name.ilike(company_name)).first()
            if not company:
                company = Company(name=company_name)
                db.add(company)
                db.commit()
                db.refresh(company)
                
            recruiter_name = details.get("recruiter_name")
            recruiter = None
            if recruiter_name:
                recruiter = db.query(Recruiter).filter(Recruiter.name == recruiter_name, Recruiter.company_id == company.id).first()
                if not recruiter:
                    recruiter = Recruiter(name=recruiter_name, profile_url=details.get("recruiter_profile_url"), company_id=company.id)
                    db.add(recruiter)
                    db.commit()
                    db.refresh(recruiter)
                    
            hiring_post_record = LinkedInHiringPost(
                post_url=post["url"],
                raw_text=post["raw_text"],
                extracted_title=details.get("title"),
                extracted_company=company_name,
                extracted_location=details.get("location"),
                extracted_skills=", ".join(details.get("skills", [])),
                extracted_experience=details.get("experience"),
                extracted_salary=details.get("salary"),
                extracted_contact_email=details.get("contact_email"),
                extracted_apply_link=details.get("apply_link"),
                recruiter_id=recruiter.id if recruiter else None
            )
            db.add(hiring_post_record)
            db.commit()
            hiring_posts_count += 1
            
            raw_jobs.append({
                "title": details.get("title") or "Software Engineer",
                "company": company_name,
                "description": f"LinkedIn Hiring Post:\n{post['raw_text']}\n\nContact Email: {details.get('contact_email', 'N/A')}\nApply: {details.get('apply_link', 'N/A')}",
                "location": details.get("location") or "India",
                "tags": details.get("skills", []) + ["LinkedIn Hiring Post", "India"],
                "url": post["url"]
            })
            
        for j in raw_jobs:
            company_name = j["company"].strip()
            company = db.query(Company).filter(Company.name.ilike(company_name)).first()
            if not company:
                company = Company(name=company_name)
                db.add(company)
                db.commit()
                db.refresh(company)
                
            title_clean = j["title"].strip()
            existing_job = db.query(Job).filter(
                Job.title.ilike(title_clean),
                Job.department.ilike(company_name)
            ).first()
            
            if existing_job:
                existing_source = db.query(JobSource).filter(
                    JobSource.job_id == existing_job.id,
                    JobSource.source_url == j["url"]
                ).first()
                if not existing_source:
                    source_platform = j["tags"][1] if len(j["tags"]) > 1 else "Internet Search"
                    new_source = JobSource(
                        job_id=existing_job.id,
                        source_platform=source_platform,
                        source_url=j["url"]
                    )
                    db.add(new_source)
                    db.commit()
                duplicates_count += 1
                continue
                
            skills_str = ", ".join(j["tags"][:8])
            exp_req = "Senior" if any(k in j["title"].lower() for k in ["senior", "lead", "principal"]) else "Entry-Level" if any(k in j["title"].lower() for k in ["junior", "entry", "intern"]) else "Mid-Level"
            
            db_job = Job(
                title=j["title"],
                description=j["description"],
                required_skills=skills_str,
                experience_level=exp_req,
                salary_range="Not Disclosed",
                location=j["location"],
                department=company_name
            )
            db.add(db_job)
            db.commit()
            db.refresh(db_job)
            
            source_platform = j["tags"][1] if len(j["tags"]) > 1 else "Internet Search"
            new_source = JobSource(
                job_id=db_job.id,
                source_platform=source_platform,
                source_url=j["url"]
            )
            db.add(new_source)
            db.commit()
            
        logger.info(f"Job Collection Agent complete. Extracted {hiring_posts_count} hiring posts. Merged {duplicates_count} duplicate listings.")
        
        global ADMIN_METRICS_JOB_AGENT
        ADMIN_METRICS_JOB_AGENT["hiring_posts_extracted"] += hiring_posts_count
        ADMIN_METRICS_JOB_AGENT["duplicate_jobs_removed"] += duplicates_count
    finally:
        db.close()

import asyncio

def _run_background_job_collection():
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        run_job_collection_agent_sync(db)
    except Exception as e:
        logger.error(f"Error in background Job Collection Agent: {e}")
    finally:
        db.close()

async def periodic_job_collection_agent_runner():
    # Wait 5 minutes after startup before first run.
    # This prevents API spam during deploy and lets Railway health checks pass cleanly.
    logger.info("Job collection agent scheduled: first run in 5 minutes.")
    await asyncio.sleep(300)
    while True:
        try:
            await asyncio.to_thread(_run_background_job_collection)
        except Exception as e:
            logger.error(f"Error in periodic_job_collection_agent_runner: {e}")
        await asyncio.sleep(3600)


@router.on_event("startup")
async def start_job_collection_agent():
    # Mark any orphaned "running" runs as "failed" on server startup
    try:
        from app.core.database import SessionLocal
        from app.models.models import JobAgentRun
        db = SessionLocal()
        orphaned_runs = db.query(JobAgentRun).filter(JobAgentRun.status == "running").all()
        for run in orphaned_runs:
            run.status = "failed"
            run.completed_at = datetime.utcnow()
        db.commit()
        db.close()
        logger.info(f"Marked {len(orphaned_runs)} orphaned agent runs as failed on startup.")
    except Exception as e:
        logger.error(f"Error cleaning up orphaned agent runs on startup: {e}")

    asyncio.create_task(periodic_job_collection_agent_runner())


