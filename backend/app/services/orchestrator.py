import json
import asyncio
import logging
import os
import requests
from typing import List, Optional, Tuple, Dict, Any
from fastapi import BackgroundTasks
import random
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.ws import manager
from app.models.models import (
    User, Candidate, CandidateProfile, CandidateResume,
    Notification, AuditLog, EmailNotification
)
from app.services.storage import storage_service, get_user_folder_name

logger = logging.getLogger(__name__)

def call_gemini(prompt: str, json_mode: bool = False) -> str:
    """
    Direct HTTPS call to Gemini 3.5 Flash API.
    Returns empty string on failure — callers are responsible for any LLM fallback.
    """
    if not settings.GEMINI_API_KEY:
        return ""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        if json_mode:
            payload["generationConfig"] = {
                "responseMimeType": "application/json",
                "maxOutputTokens": 8192
            }
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        if res.status_code == 200:
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            logger.error(f"Gemini API returned status code {res.status_code}: {res.text}")
    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
    return ""

def call_nvidia(messages, json_mode: bool = False) -> str:
    """
    Direct HTTPS call to NVIDIA Chat Completions API.
    Falls back to a secondary key if the primary key fails or is missing,
    and returns empty string on failure.
    Uses dynamic model fallbacks to bypass timeouts or unsupported models.
    """
    api_key = settings.NVIDIA_API_KEY or settings.NVIDIA_API_KEY_FALLBACK
    if not api_key or str(api_key).strip().lower() in ["", "none", "null", "undefined"]:
        return ""
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
        
    # Build list of models to try, avoiding known broken ones at the start
    model_env = os.getenv("NVIDIA_MODEL", "").strip()
    broken_models = ["nvidia/llama-3.3-nemotron-super-49b-v1.5", "nvidia/llama-3.3-nemotron-70b-instruct"]
    
    models_to_try = []
    if model_env and model_env not in broken_models:
        models_to_try.append(model_env)
        
    # Add standard high-availability models
    default_models = ["meta/llama-3.3-70b-instruct", "mistralai/mistral-medium-3.5-128b"]
    for m in default_models:
        if m not in models_to_try:
            models_to_try.append(m)
            
    # Keep the user's broken model at the end as a last resort if explicitly requested
    if model_env and model_env in broken_models:
        models_to_try.append(model_env)

    def _try_call(key_to_use: str) -> str:
        import json
        for model in models_to_try:
            try:
                url = "https://integrate.api.nvidia.com/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key_to_use}"
                }
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.1,
                    "top_p": 1,
                    "max_tokens": 1024,
                    "stream": True
                }
                res = requests.post(url, headers=headers, json=payload, timeout=(10, 120), stream=True)
                if res.status_code == 200:
                    content_chunks = []
                    for line in res.iter_lines():
                        if not line:
                            continue
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                if "content" in delta:
                                    content_chunks.append(delta["content"])
                            except Exception:
                                pass
                    content = "".join(content_chunks)
                    if content:
                        return content
                else:
                    logger.error(f"NVIDIA API ({model}) returned status code {res.status_code}: {res.text}")
            except Exception as e:
                logger.error(f"Error calling NVIDIA API with model {model}: {e}")
        return ""


    # Try primary key first
    res_text = _try_call(settings.NVIDIA_API_KEY) if settings.NVIDIA_API_KEY else ""
    
    # Try fallback key if primary failed/skipped and fallback exists
    if not res_text and settings.NVIDIA_API_KEY_FALLBACK and settings.NVIDIA_API_KEY_FALLBACK != settings.NVIDIA_API_KEY:
        logger.warning("Primary NVIDIA API call failed or missing. Trying fallback NVIDIA API key...")
        res_text = _try_call(settings.NVIDIA_API_KEY_FALLBACK)
        
    return res_text

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    import io
    try:
        # Check if bytes start with %PDF header
        if not pdf_bytes.startswith(b"%PDF"):
            try:
                return pdf_bytes.decode("utf-8", errors="ignore").strip()
            except Exception:
                pass
        
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        links = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
            
            # Extract hyperlink annotations
            try:
                if page.annotations:
                    for annot in page.annotations:
                        annot_obj = annot.get_object()
                        if annot_obj and "/A" in annot_obj:
                            action = annot_obj["/A"].get_object()
                            if action and "/URI" in action:
                                uri = action["/URI"]
                                if uri and uri not in links:
                                    links.append(uri)
            except Exception as annot_err:
                logger.debug(f"Error extracting annotations from page: {annot_err}")
                
        if links:
            text += "\n\nExtracted PDF Hyperlinks:\n" + "\n".join(links)
            
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        # Final fallback try decoding just in case
        try:
            return pdf_bytes.decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""

def fallback_parse_resume_text(text: str) -> dict:
    import re
    # Extract email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    email = email_match.group(0) if email_match else ""
    
    # Extract phone
    phone_match = re.search(r'\+?\d[\d -]{8,12}\d', text)
    phone = phone_match.group(0) if phone_match else ""
    
    # Extract name (first non-empty line)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    name = lines[0] if lines else ""
    
    # Find matching skills from common list
    common_skills = [
        "Python", "FastAPI", "React", "TypeScript", "JavaScript", "SQL", "PostgreSQL",
        "Docker", "AWS", "Node", "HTML", "CSS", "Next.js", "Java", "C++", "Git", "Kubernetes"
    ]
    matched = []
    for skill in common_skills:
        if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
            matched.append(skill)
            
    skills_str = ", ".join(matched)
    
    return {
        "name": name,
        "email": email,
        "phone": phone,
        "skills": skills_str,
        "experience": json.dumps([]),
        "education": json.dumps([]),
        "projects": json.dumps([]),
        "certifications": "",
        "github": "",
        "linkedin": "",
        "portfolio": ""
    }



class AgentOrchestrator:
    
    # 1. RESUME COLLECTION AGENT
    async def run_resume_collection_agent(self, db: Session, candidate_id: int, file_content: bytes, filename: str, background_tasks: Optional[BackgroundTasks] = None) -> CandidateResume:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            raise Exception("Candidate not found")
            
        # Initial status updates
        candidate.resume_status = "uploading"
        candidate.resume_progress = 10
        candidate.resume_step = "Uploading PDF"
        candidate.resume_processing_error = None
        db.commit()
        
        # Broadcast uploading state
        from app.core.ws import manager
        try:
            await manager.broadcast_to_user(f"candidate_{candidate_id}", {
                "type": "resume_processing",
                "candidate_id": candidate_id,
                "status": "uploading",
                "progress": 10,
                "step": "Uploading PDF"
            })
        except Exception as ws_err:
            logger.warning(f"Failed to broadcast upload status: {ws_err}")

        # Upload resume to storage
        user_folder = get_user_folder_name(candidate.user)
        resume_url = storage_service.upload_file(f"users/{user_folder}/resumes", f"{candidate_id}_{filename}", file_content)
        
        # Deactivate all other resumes for this candidate to make the new one active
        db.query(CandidateResume).filter(
            CandidateResume.candidate_id == candidate_id
        ).update({CandidateResume.is_active: False})
        
        # Record in DB
        resume = CandidateResume(
            candidate_id=candidate_id,
            resume_url=resume_url,
            is_active=True
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        
        candidate.status = "Resume Uploaded"
        candidate.current_step = "Apply"
        
        candidate.resume_status = "extracting_text"
        candidate.resume_progress = 20
        candidate.resume_step = "Extracting text from PDF"
        db.commit()
        
        # Broadcast extracting text state
        try:
            await manager.broadcast_to_user(f"candidate_{candidate_id}", {
                "type": "resume_processing",
                "candidate_id": candidate_id,
                "status": "extracting_text",
                "progress": 20,
                "step": "Extracting text from PDF"
            })
        except Exception as ws_err:
            logger.warning(f"Failed to broadcast extraction status: {ws_err}")
        
        # Extract actual text from the PDF file content
        extracted_text = extract_text_from_pdf(file_content)
        if not extracted_text:
            extracted_text = ""
            
        profile = CandidateProfile(
            candidate_id=candidate_id,
            resume_text=extracted_text,
            parsed_metadata="{}",
            resume_id=resume.id
        )
        db.add(profile)
        db.commit()
        
        # Trigger parsing agent asynchronously or synchronously
        if background_tasks:
            async def run_parsing_bg(cand_id: int):
                from app.core.database import SessionLocal
                db_session = SessionLocal()
                try:
                    await self.run_resume_parsing_agent(db_session, cand_id, None)
                except Exception as bg_err:
                    logger.error(f"Background resume parsing failed: {bg_err}")
                finally:
                    db_session.close()
            
            background_tasks.add_task(run_parsing_bg, candidate_id)
        else:
            await self.run_resume_parsing_agent(db, candidate_id, None)
        
        return resume


    # 2. RESUME PARSING AGENT
    async def run_resume_parsing_agent(self, db: Session, candidate_id: int, background_tasks: Optional[BackgroundTasks] = None):
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        profile = db.query(CandidateProfile).filter(CandidateProfile.candidate_id == candidate_id).order_by(CandidateProfile.created_at.desc()).first()
        
        if not candidate or not profile:
            return
            
        from app.core.ws import manager
        try:
            # Set status to parsing resume
            candidate.resume_status = "parsing_resume"
            candidate.resume_progress = 40
            candidate.resume_step = "Parsing resume sections with Gemini/NVIDIA"
            db.commit()
            
            try:
                await manager.broadcast_to_user(f"candidate_{candidate_id}", {
                    "type": "resume_processing",
                    "candidate_id": candidate_id,
                    "status": "parsing_resume",
                    "progress": 40,
                    "step": "Parsing resume sections with Gemini/NVIDIA"
                })
            except Exception as ws_err:
                logger.warning(f"Failed to broadcast parsing status: {ws_err}")

            # Extract metadata via Gemini or fallback
            text_to_parse = profile.resume_text
            prompt = (
                "You are an expert resume parser. Parse this resume and output a JSON object with keys: "
                "'name', 'email', 'phone', 'summary', 'skills', 'experience', 'education', 'projects', "
                "'certifications', 'achievements', 'languages', 'github', 'linkedin', 'portfolio'.\n"
                "Rules:\n"
                "1. For 'skills', return a comma-separated string of skills.\n"
                "2. For 'education', return a JSON array of objects with keys: degree, school, year.\n"
                "3. For 'experience', return a JSON array of objects with keys: role, company, years, description.\n"
                "4. For 'projects', return a JSON array of objects with keys: name, description, technologies.\n"
                "5. For 'certifications', return a comma-separated string.\n"
                "6. For 'achievements', return a JSON array of strings.\n"
                "7. For 'languages', return a comma-separated string.\n"
                "8. For 'summary', return a single string professional summary.\n"
                "9. Output strictly valid JSON only. Do not wrap in backticks or markdown tags. "
                "Ensure all double quotes inside JSON string values are properly escaped as \\\" or replaced with single quotes so that it parses successfully with json.loads.\n\n"
                f"Resume Text:\n{text_to_parse}"
            )
            
            ai_response = None
            if settings.GEMINI_API_KEY:
                ai_response = await asyncio.to_thread(call_gemini, prompt, json_mode=True)
            
            if not ai_response and settings.NVIDIA_API_KEY:
                messages = [{"role": "user", "content": prompt + "\nRemember: Return ONLY valid JSON, do not include any other text."}]
                ai_response = await asyncio.to_thread(call_nvidia, messages)
                
            data = {}
            if ai_response:
                try:
                    cleaned = ai_response.strip()
                    if cleaned.startswith("```"):
                        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    cleaned = cleaned.strip()
                    if cleaned.startswith("json"):
                        cleaned = cleaned[4:].strip()
                    
                    # Pre-clean known problematic character formats
                    cleaned = cleaned.replace('\uFFFD', '').replace('', '')
                    
                    data = json.loads(cleaned)
                except Exception as e:
                    logger.error(f"Error parsing AI JSON response: {e}")
                    try:
                        import re
                        fixed = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', cleaned)
                        data = json.loads(fixed)
                        logger.info("Successfully recovered JSON using regex normalization.")
                    except Exception as ex:
                        logger.error(f"Fallback JSON recovery failed: {ex}")
                        data = {}
                    
            if not data:
                data = fallback_parse_resume_text(text_to_parse)
                
            if candidate.user and data.get("name"):
                candidate.user.full_name = data.get("name")
                
            # Normalize fields - ensure education/experience/projects/achievements are JSON strings
            for field in ['education', 'experience', 'projects', 'achievements']:
                val = data.get(field)
                if val is not None and isinstance(val, (list, dict)):
                    data[field] = json.dumps(val)
            
            # Normalize comma-separated fields
            for field in ['skills', 'certifications', 'languages']:
                val = data.get(field)
                if val is not None and isinstance(val, list):
                    data[field] = ', '.join(str(v) for v in val)
            
            # Update candidate details
            candidate.phone = data.get("phone", candidate.phone)
            candidate.skills = data.get("skills", candidate.skills)
            candidate.education = data.get("education", candidate.education)
            candidate.experience = data.get("experience", candidate.experience)
            candidate.projects = data.get("projects", candidate.projects)
            candidate.certifications = data.get("certifications", candidate.certifications)
            candidate.summary = data.get("summary", candidate.summary)
            candidate.achievements = data.get("achievements", candidate.achievements)
            candidate.languages = data.get("languages", candidate.languages)
            candidate.github = data.get("github", candidate.github)
            candidate.linkedin = data.get("linkedin", candidate.linkedin)
            candidate.portfolio = data.get("portfolio", candidate.portfolio)
            candidate.parsed_name = data.get("name", candidate.parsed_name)
            candidate.parsed_email = data.get("email", candidate.parsed_email)
            candidate.current_step = "Apply"
            
            profile.parsed_metadata = json.dumps(data)
            db.commit()

            # Set status to building profile
            candidate.resume_status = "building_profile"
            candidate.resume_progress = 65
            candidate.resume_step = "Syncing details and calculating career metadata"
            db.commit()
            
            try:
                await manager.broadcast_to_user(f"candidate_{candidate_id}", {
                    "type": "resume_processing",
                    "candidate_id": candidate_id,
                    "status": "building_profile",
                    "progress": 65,
                    "step": "Syncing details and calculating career metadata"
                })
            except Exception as ws_err:
                logger.warning(f"Failed to broadcast profile sync status: {ws_err}")

            # Rebuild structured Candidate Profile with domain, confidence, experience, preferred roles, etc.
            try:
                await self.rebuild_candidate_profile_data(db, candidate)
            except Exception as e:
                logger.error(f"Failed to auto-rebuild profile after resume parsing: {e}")

            # Set status to generating embeddings
            candidate.resume_status = "generating_embeddings"
            candidate.resume_progress = 85
            candidate.resume_step = "Generating AI embeddings and search strategy"
            db.commit()
            
            try:
                await manager.broadcast_to_user(f"candidate_{candidate_id}", {
                    "type": "resume_processing",
                    "candidate_id": candidate_id,
                    "status": "generating_embeddings",
                    "progress": 85,
                    "step": "Generating AI embeddings and search strategy"
                })
            except Exception as ws_err:
                logger.warning(f"Failed to broadcast embeddings status: {ws_err}")

            # Trigger ResumeIntelligenceAgent synchronously in the background worker
            from app.agents.resume_intelligence_agent import ResumeIntelligenceAgent as RIA
            ria = RIA(db, candidate_id)
            await ria.execute_pipeline()

            # Mark ingestion complete
            candidate.resume_status = "completed"
            candidate.resume_progress = 100
            candidate.resume_step = "Resume analysis complete"
            candidate.resume_last_processed_at = datetime.utcnow()
            candidate.resume_processing_error = None
            db.commit()

            # Invalidate AI Mentor profile cache
            try:
                from app.services.mentor_cache import invalidate_mentor_profile
                invalidate_mentor_profile(candidate.user_id)
                logger.info(f"Invalidated AI Mentor profile cache for user {candidate.user_id}")
            except Exception as cache_err:
                logger.warning(f"Failed to invalidate AI Mentor profile cache: {cache_err}")

            # Broadcast completion
            try:
                await manager.broadcast_to_user(f"candidate_{candidate_id}", {
                    "type": "resume_processed",
                    "candidate_id": candidate_id,
                    "status": "completed",
                    "progress": 100,
                    "step": "Resume analysis complete"
                })
            except Exception as ws_err:
                logger.warning(f"Failed to broadcast completion status: {ws_err}")

        except Exception as pipeline_err:
            logger.error(f"Resume processing pipeline failed for candidate {candidate_id}: {pipeline_err}")
            db.rollback()
            try:
                # Reload candidate in a clean transaction block to save the error status
                candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
                if candidate:
                    candidate.resume_status = "failed"
                    candidate.resume_progress = 100
                    candidate.resume_step = "Failed to process resume"
                    candidate.resume_processing_error = str(pipeline_err)
                    db.commit()
                
                await manager.broadcast_to_user(f"candidate_{candidate_id}", {
                    "type": "resume_failed",
                    "candidate_id": candidate_id,
                    "status": "failed",
                    "progress": 100,
                    "step": "Failed to process resume",
                    "error": str(pipeline_err)
                })
            except Exception as save_err:
                logger.error(f"Failed to persist pipeline failure: {save_err}")

    # Helper to rebuild Candidate Profile Data
    async def rebuild_candidate_profile_data(self, db: Session, candidate: Candidate):
        """
        Rebuilds structured Candidate Profile data.
        Saves to CandidateProfile.parsed_metadata JSON.
        """
        try:
            skills_list = []
            if candidate.skills:
                skills_list = [s.strip() for s in candidate.skills.split(",") if s.strip()]
                
            certs_list = []
            if candidate.certifications:
                certs_list = [c.strip() for c in candidate.certifications.split(",") if c.strip()]
                
            exp_metrics = calculate_experience_intervals(candidate.experience)
            exp_years = exp_metrics["total_experience_years"]
            
            domain_info = classify_candidate_domain(skills_list, candidate.summary or "")
            domain = domain_info["domain"]
            confidence = domain_info["confidence"]
            subdomains = domain_info["subdomains"]
            preferred_roles = domain_info["preferred_roles"]
            career_level = domain_info["career_level"]
            
            locations = []
            if candidate.address:
                locations = [candidate.address]
                
            profile_data = {
                "skills": skills_list,
                "experience_years": exp_years,
                "experience_months": exp_metrics["total_experience_months"],
                "structured_experience": exp_metrics["structured_experience"],
                "education": candidate.education or "",
                "projects": candidate.projects or "[]",
                "certifications": certs_list,
                "summary": candidate.summary or "",
                "domain": domain,
                "confidence": confidence,
                "subdomains": subdomains,
                "preferred_roles": preferred_roles,
                "career_level": career_level,
                "locations": locations
            }
            
            profile = db.query(CandidateProfile).filter(CandidateProfile.candidate_id == candidate.id).order_by(CandidateProfile.created_at.desc()).first()
            if not profile:
                profile = CandidateProfile(candidate_id=candidate.id)
                db.add(profile)
            
            profile.experience_years = exp_years
            profile.generated_roles = json.dumps(preferred_roles)
            profile.specialization = subdomains[0] if subdomains else ""
            profile.current_role = preferred_roles[0] if preferred_roles else ""
            profile.parsed_metadata = json.dumps(profile_data)
            db.commit()
            logger.info(f"Candidate profile rebuilt successfully for candidate {candidate.id}")

            
            # Upsert to Qdrant Vector Store
            try:
                from app.services.vector_store import vector_store
                resume_text = f"Roles: {', '.join(profile_data.get('preferred_roles', []))}\nDomain: {profile_data.get('domain', '')}\nSkills: {', '.join(profile_data.get('skills', []))}\nExperience: {profile_data.get('experience_years', 0)} years\nSummary: {profile_data.get('summary', '')}"
                await vector_store.upsert_resume(candidate.id, resume_text, profile_data.get("skills", []))
                logger.info(f"Upserted resume to Qdrant vector store for candidate {candidate.id}")
            except Exception as q_err:
                logger.error(f"Error upserting resume to Qdrant: {q_err}")
        except Exception as e:
            logger.error(f"Error rebuilding candidate profile: {e}")
            db.rollback()



def calculate_experience_intervals(exp_json) -> dict:
    """
    Calculates total unique experience months and years by merging overlapping periods.
    """
    import json
    import re
    from datetime import datetime, date

    def parse_date(date_str: str) -> date:
        if not date_str:
            return None
        ds = date_str.lower().strip()
        if ds in ["present", "current", "till date", "now", "ongoing"]:
            return date.today()
            
        ds = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', ds)
        formats = [
            "%Y-%m-%d", "%Y-%m", "%m-%Y", "%m/%Y", "%Y/%m",
            "%b %Y", "%B %Y", "%d %b %Y", "%d %B %Y", "%Y"
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.date()
            except ValueError:
                pass
                
        months_map = {
            "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
            "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
            "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
            "nov": 11, "november": 11, "dec": 12, "december": 12
        }
        year_match = re.search(r'\b(19\d\d|20\d\d)\b', ds)
        if year_match:
            year = int(year_match.group(1))
            month = 1
            for m_name, m_val in months_map.items():
                if m_name in ds:
                    month = m_val
                    break
            else:
                month_match = re.search(r'\b(0?[1-9]|1[0-2])\b', ds)
                if month_match:
                    month = int(month_match.group(1))
            return date(year, month, 1)
        return None

    if not exp_json:
        return {"total_experience_months": 0, "total_experience_years": 0.0, "structured_experience": []}
        
    try:
        roles = json.loads(exp_json) if isinstance(exp_json, str) else exp_json
        if not isinstance(roles, list):
            return {"total_experience_months": 0, "total_experience_years": 0.0, "structured_experience": []}
            
        intervals = []
        structured_experience = []
        non_date_months = 0.0
        
        for role in roles:
            comp = role.get("company", "Unknown")
            role_title = role.get("role", "Employee")
            start_str = role.get("start_date") or role.get("startDate") or role.get("start")
            end_str = role.get("end_date") or role.get("endDate") or role.get("end") or "Present"
            
            currently_working = False
            if not role.get("end_date") and not role.get("endDate") and not role.get("end"):
                currently_working = True
            elif str(end_str).lower().strip() in ["present", "current", "till date", "now", "ongoing"]:
                currently_working = True
                
            if not start_str:
                duration_val = role.get("duration") or role.get("years")
                if duration_val:
                    # Normalize separators like en-dash, em-dash, "to", etc. to standard hyphen
                    normalized_duration = re.sub(r'\s*(?:to|till|until|\u2013|\u2014|\u2212|-)\s*', '-', str(duration_val), flags=re.IGNORECASE)
                    
                    if "-" in normalized_duration:
                        parts = normalized_duration.split("-")
                        start_str, end_str = parts[0], parts[1]
                        # Re-evaluate currently_working based on the new end_str
                        if str(end_str).lower().strip() in ["present", "current", "till date", "now", "ongoing"]:
                            currently_working = True
                        else:
                            currently_working = False
                    else:
                        y_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:year|yr|y)', str(duration_val), re.IGNORECASE)
                        m_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:month|mon|m)', str(duration_val), re.IGNORECASE)
                        role_months = 0.0
                        if y_match:
                            role_months += float(y_match.group(1)) * 12
                        if m_match:
                            role_months += float(m_match.group(1))
                        if not y_match and not m_match:
                            try:
                                role_months += float(duration_val) * 12
                            except ValueError:
                                pass
                        if role_months > 0:
                            non_date_months += role_months
                            structured_experience.append({
                                "company": comp,
                                "role": role_title,
                                "start_date": None,
                                "end_date": None,
                                "currently_working": currently_working,
                                "duration": str(duration_val)
                            })
                        continue
                else:
                    continue
                    
            start = parse_date(str(start_str))
            end = parse_date(str(end_str))
            
            if start and end:
                if start > end:
                    start, end = end, start
                intervals.append((start, end))
                structured_experience.append({
                    "company": comp,
                    "role": role_title,
                    "start_date": start.isoformat() if start else None,
                    "end_date": end.isoformat() if end and not currently_working else None,
                    "currently_working": currently_working
                })
                
        total_days = 0
        if intervals:
            intervals.sort(key=lambda x: x[0])
            merged = [intervals[0]]
            for current in intervals[1:]:
                prev_start, prev_end = merged[-1]
                curr_start, curr_end = current
                if curr_start <= prev_end:
                    merged[-1] = (prev_start, max(prev_end, curr_end))
                else:
                    merged.append(current)
                    
            for start, end in merged:
                total_days += (end - start).days
            
        total_months = int(round(total_days / 30.44)) + int(round(non_date_months))
        total_years = round(total_months / 12.0, 1)
        
        return {
            "total_experience_months": total_months,
            "total_experience_years": total_years,
            "structured_experience": structured_experience
        }
    except Exception as e:
        logger.error(f"Error in calculate_experience_intervals: {e}")
        return {"total_experience_months": 0, "total_experience_years": 0.0, "structured_experience": []}


def classify_candidate_domain(skills: List[str], summary: str) -> dict:
    """Classifies candidate profile into domain, confidence, subdomains, and preferred roles using NVIDIA LLM."""
    import json
    
    prompt = f"""
You are an expert recruitment AI. Analyze the candidate's skills and professional summary, and classify their profile.
Return ONLY a strictly valid JSON object with the following keys. Do NOT wrap in markdown blocks, backticks, or write any explanatory text.

Keys:
- domain: string (The primary professional domain. Examples: "Software Engineering", "Civil Engineering", "Mechanical Engineering", "Chartered Accountant", "Finance", "HR", "Marketing", "Healthcare", "Legal", "Operations", or any other specific industry/domain).
- subdomains: list of strings (3-4 core sub-specializations based on skills/summary)
- preferred_roles: list of strings (3-4 specific job titles / roles they are qualified for)
- confidence: integer (0-100 score of how confident you are in this classification)
- career_level: string (e.g. "Entry-level", "Mid-level", "Senior", "Lead/Management")

Profile Details:
Skills: {", ".join(skills) if skills else "None"}
Summary: {summary if summary else "None"}
"""
    try:
        messages = [{"role": "user", "content": prompt}]
        res = call_nvidia(messages)
        res_clean = res.strip()
        if res_clean.startswith("```"):
            lines = res_clean.split("\n")
            res_clean = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        if res_clean.startswith("json"):
            res_clean = res_clean[4:].strip()
            
        data = json.loads(res_clean)
        return {
            "domain": data.get("domain", "Software Engineering"),
            "confidence": int(data.get("confidence", 85)),
            "subdomains": data.get("subdomains", ["Full Stack Development"]),
            "preferred_roles": data.get("preferred_roles", ["Software Engineer"]),
            "career_level": data.get("career_level", "Mid-level")
        }
    except Exception as e:
        logger.warning(f"AI candidate domain classification failed: {e}. Falling back to default.")
        return {
            "domain": "Software Engineering",
            "confidence": 80,
            "subdomains": ["Full Stack Development"],
            "preferred_roles": ["Software Engineer"],
            "career_level": "Mid-level"
        }

orchestrator = AgentOrchestrator()
