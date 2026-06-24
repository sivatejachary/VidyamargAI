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

def call_gemini(prompt: str, json_mode: bool = False, pdf_bytes: Optional[bytes] = None, model: str = "gemini-2.0-flash") -> str:
    """
    Direct HTTPS call to Gemini API with dynamic model support.
    Can accept pdf_bytes to send PDF file directly to Gemini's multimodal window.
    """
    if not settings.GEMINI_API_KEY:
        return ""
    try:
        import base64
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        
        parts = []
        if pdf_bytes:
            encoded_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
            parts.append({
                "inlineData": {
                    "mimeType": "application/pdf",
                    "data": encoded_pdf
                }
            })
        parts.append({"text": prompt})
        
        payload = {
            "contents": [{"parts": parts}]
        }
        if json_mode:
            payload["generationConfig"] = {
                "responseMimeType": "application/json",
                "maxOutputTokens": 8192
            }
        res = requests.post(url, headers=headers, json=payload, timeout=40)
        if res.status_code == 200:
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            logger.error(f"Gemini API ({model}) returned status code {res.status_code}: {res.text}")
    except Exception as e:
        logger.error(f"Error calling Gemini ({model}): {e}")
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
                    "max_tokens": 4096,
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

def fallback_pymupdf_pipeline(pdf_bytes: bytes) -> dict:
    import re
    import json
    
    # 1. Text Extraction
    text = ""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text()
    except Exception as e:
        logger.warning(f"PyMuPDF text extraction failed: {e}. Falling back to pypdf.")
        try:
            import pypdf
            import io
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                text += page.extract_text() or ""
        except Exception as e2:
            logger.error(f"pypdf extraction failed: {e2}")
            
    # Clean text
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # 2. Section Detection
    sections = {
        "personal": [],
        "education": [],
        "experience": [],
        "skills": [],
        "projects": [],
        "certifications": [],
        "achievements": [],
        "other": []
    }
    
    current_sec = "personal"
    
    sec_keywords = {
        "education": ["education", "academic", "study", "university", "college", "school"],
        "experience": ["experience", "work history", "employment", "professional background", "career history"],
        "skills": ["skills", "technical skills", "technologies", "expertise", "competencies"],
        "projects": ["projects", "personal projects", "academic projects", "key projects"],
        "certifications": ["certifications", "licenses", "credentials"],
        "achievements": ["achievements", "awards", "honors"]
    }
    
    for line in lines:
        lower_line = line.lower()
        matched_sec = None
        if len(line) < 30:
            for sec, keywords in sec_keywords.items():
                if any(re.search(r'\b' + re.escape(kw) + r'\b', lower_line) for kw in keywords):
                    matched_sec = sec
                    break
        
        if matched_sec:
            current_sec = matched_sec
        else:
            sections[current_sec].append(line)
            
    # 3. Regex Extraction
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    email = email_match.group(0) if email_match else ""
    
    phone_match = re.search(r'\+?\d[\d -().]{8,15}\d', text)
    phone = phone_match.group(0) if phone_match else ""
    
    name = "Candidate"
    for line in lines[:5]:
        if email in line or phone in line:
            continue
        clean_line = re.sub(r'^(name|full\s*name)[:\s\-]+', '', line, flags=re.IGNORECASE).strip()
        clean_line = re.sub(r'[^a-zA-Z\s]', '', clean_line).strip()
        if len(clean_line) > 2 and len(clean_line) < 40 and len(clean_line.split()) >= 2:
            name = clean_line
            break
    if name == "Candidate" and lines:
        clean_line = re.sub(r'^(name|full\s*name)[:\s\-]+', '', lines[0], flags=re.IGNORECASE).strip()
        name = re.sub(r'[^a-zA-Z\s]', '', clean_line).strip() or "Candidate"
        
    location = "Remote"
    location_match = re.search(r'\b(Bengaluru|Bangalore|Hyderabad|Pune|Mumbai|Delhi|Noida|Gurugram|Chennai|San Francisco|New York|London|Remote)\b', text, re.IGNORECASE)
    if location_match:
        location = location_match.group(0)
        
    linkedin = ""
    github = ""
    portfolio = ""
    
    li_match = re.search(r'(https?://)?(www\.)?linkedin\.com/in/[\w\.-]+', text, re.IGNORECASE)
    if li_match:
        linkedin = li_match.group(0)
        
    gh_match = re.search(r'(https?://)?(www\.)?github\.com/[\w\.-]+', text, re.IGNORECASE)
    if gh_match:
        github = gh_match.group(0)
        
    portfolio_match = re.search(r'(https?://)?(www\.)?([\w\.-]+)\.github\.io', text, re.IGNORECASE)
    if portfolio_match:
        portfolio = portfolio_match.group(0)

    # 4. Education Extraction
    education_list = []
    edu_text = "\n".join(sections["education"])
    edu_entries = re.split(r'\b(19\d{2}|20\d{2})\b', edu_text)
    if len(edu_entries) > 1:
        for i in range(0, len(edu_entries) - 1, 2):
            chunk = edu_entries[i].strip()
            year = edu_entries[i+1].strip()
            
            deg = "Degree"
            deg_match = re.search(r'\b(B\.?Tech|M\.?Tech|B\.?E|M\.?E|B\.?Sc|M\.?Sc|B\.?Com|M\.?Com|B\.?B\.?A|M\.?B\.?A|M\.?C\.?A|Ph\.?D|Intermediate|10th|ITI|Diploma)\b', chunk, re.IGNORECASE)
            if deg_match:
                deg = deg_match.group(0)
                
            school = "University"
            school_match = re.search(r'\b([A-Z][a-zA-Z\s]+(University|College|Institute|School|IIT|NIT|BITS|Board))\b', chunk)
            if school_match:
                school = school_match.group(1).strip()
            else:
                chunk_lines = [l for l in chunk.split('\n') if l.strip()]
                if chunk_lines:
                    school = chunk_lines[-1]
                    
            education_list.append({
                "degree": deg,
                "school": school,
                "year": year
            })
    if not education_list:
        education_list = [{"degree": "Bachelor's Degree", "school": "University", "year": "2023"}]

    # 5. Experience Extraction
    experience_list = []
    exp_text = "\n".join(sections["experience"])
    exp_chunks = re.split(r'\b(19\d{2}|20\d{2})\b', exp_text)
    if len(exp_chunks) > 1:
        for i in range(0, len(exp_chunks) - 1, 2):
            chunk = exp_chunks[i].strip()
            year = exp_chunks[i+1].strip()
            
            role = "Software Developer"
            role_match = re.search(r'\b([A-Za-z\s]+(Developer|Engineer|Manager|Analyst|Consultant|Specialist|Officer|Teacher|Architect|Aspirant|Accountant))\b', chunk)
            if role_match:
                role = role_match.group(1).strip()
                
            company = "Company"
            company_match = re.search(r'\b([A-Z][a-zA-Z0-9\s]+(Ltd|Inc|Corp|Co|Pvt|Group|Solutions|Services))\b', chunk)
            if company_match:
                company = company_match.group(1).strip()
            else:
                chunk_lines = [l for l in chunk.split('\n') if l.strip()]
                if chunk_lines:
                    company = chunk_lines[-1]
                    
            experience_list.append({
                "role": role,
                "company": company,
                "years": year,
                "description": chunk[:200]
            })
    if not experience_list:
        experience_list = [{"role": "Professional", "company": "Private Sector", "years": "2 years", "description": "Experienced candidate."}]

    # 6. Skills Extraction
    skills_text = "\n".join(sections["skills"]) + "\n" + text
    common_skills = [
        "Python", "FastAPI", "React", "TypeScript", "JavaScript", "SQL", "PostgreSQL",
        "Docker", "AWS", "Node", "HTML", "CSS", "Next.js", "Java", "C++", "Git", "Kubernetes",
        "Spring", "Django", "Machine Learning", "AI", "Deep Learning", "TensorFlow", "PyTorch",
        "Accounting", "GST", "UPSC Preparation", "Civil Services", "Teaching", "Analytics",
        "Finance", "Management", "Communication", "Leadership", "Excel", "Data Analysis"
    ]
    detected_skills = []
    for skill in common_skills:
        if re.search(r'\b' + re.escape(skill) + r'\b', skills_text, re.IGNORECASE):
            detected_skills.append(skill)
            
    if not detected_skills:
        detected_skills = ["Communication", "Problem Solving", "Collaboration"]
        
    skills_structured = []
    for s in detected_skills:
        skills_structured.append({
            "name": s,
            "score": 80,
            "confidence": 85,
            "market_demand": 75,
            "experience_years": 2.0
        })

    edges = []
    if len(detected_skills) >= 2:
        for i in range(len(detected_skills) - 1):
            edges.append({"from": detected_skills[i], "to": detected_skills[i+1]})

    # 7. Projects Extraction
    projects_list = []
    proj_text = "\n".join(sections["projects"])
    proj_lines = [l for l in sections["projects"] if len(l) > 10]
    for idx, l in enumerate(proj_lines[:3]):
        projects_list.append({
            "name": l[:30],
            "description": l,
            "technologies": ", ".join(detected_skills[:3])
        })
    if not projects_list:
        projects_list = [{"name": "Professional Project", "description": "Applied technical skills to deliver value.", "technologies": ", ".join(detected_skills[:3])}]

    # 8. Certifications Extraction
    certifications_list = []
    cert_text = "\n".join(sections["certifications"])
    cert_matches = re.findall(r'\b([A-Za-z\s]+(Certified|Certification|PMP|AWS|Google|Microsoft))\b', cert_text, re.IGNORECASE)
    for m in cert_matches[:3]:
        certifications_list.append(m[0].strip())
    certifications_str = ", ".join(certifications_list) if certifications_list else "None"

    # 9. Fallback Role Engine (Rule-Based Role Generation)
    skills_lower = [s.lower() for s in detected_skills]
    experience_lower = exp_text.lower()
    projects_lower = proj_text.lower()
    combined_lower_text = (skills_text + "\n" + exp_text + "\n" + proj_text).lower()
    
    core_roles = []
    if "python" in skills_lower and ("ml" in skills_lower or "machine learning" in skills_lower or "ai" in skills_lower):
        core_roles.append({"role": "ML Engineer", "confidence": 85})
    if "java" in skills_lower and "spring" in skills_lower:
        core_roles.append({"role": "Backend Developer", "confidence": 85})
    if "accounting" in skills_lower or "gst" in skills_lower:
        core_roles.append({"role": "Accountant", "confidence": 85})
    if "upsc" in combined_lower_text or "civil services" in combined_lower_text:
        core_roles.append({"role": "Civil Services Aspirant", "confidence": 85})
    if "teaching" in combined_lower_text or "teacher" in combined_lower_text or "education" in experience_lower:
        core_roles.append({"role": "Teacher", "confidence": 85})
        
    is_tech = any(s in ["python", "javascript", "java", "c++", "typescript", "react", "node", "aws", "docker", "sql"] for s in skills_lower)
    
    if not core_roles:
        if is_tech:
            core_roles.append({"role": "Software Engineer", "confidence": 80})
            core_roles.append({"role": "Full Stack Developer", "confidence": 75})
        else:
            core_roles.append({"role": "Business Analyst", "confidence": 80})
            core_roles.append({"role": "Operations Manager", "confidence": 70})
            
    roles = {
        "core": core_roles,
        "related": [{"role": "Systems Analyst" if is_tech else "Project Manager", "confidence": 75}],
        "adjacent": [{"role": "Technical Consultant" if is_tech else "Support Specialist", "confidence": 70}],
        "transferable": [{"role": "Product Specialist", "confidence": 65}],
        "future": [{"role": "Technical Lead" if is_tech else "Operations Director", "confidence": 60}],
        "leadership": [{"role": "Engineering Manager" if is_tech else "Team Lead", "confidence": 55}]
    }

    summary = ""
    if sections["personal"]:
        for l in sections["personal"]:
            if len(l) > 40 and not email in l and not phone in l:
                summary = l
                break
    if not summary:
        summary = f"Results-driven professional with experience in {', '.join(detected_skills[:4])}."

    career_family = "Engineering" if is_tech else "Business"
    if any(s in ["biology", "nursing", "medicine", "mbbs", "bds"] for s in skills_lower):
        career_family = "Healthcare"
    elif any(s in ["law", "llb", "legal"] for s in skills_lower):
        career_family = "Legal"
    elif any(s in ["finance", "accounting", "ca", "cfa", "banking", "gst"] for s in skills_lower):
        career_family = "Finance"
    elif "teaching" in combined_lower_text or "teacher" in combined_lower_text:
        career_family = "Teaching"

    primary_role = core_roles[0]["role"]
    career_paths = [
        {
            "path_name": f"{primary_role} Growth Path",
            "steps": [primary_role, f"Senior {primary_role}", f"Lead {primary_role}"],
            "milestones": ["Deliver key deliverables", "Acquire advanced domain skills"]
        }
    ]

    personality = "Builder" if is_tech else "Operator"
    if "teaching" in combined_lower_text or "teacher" in combined_lower_text:
        personality = "Researcher"

    eligible_exams = [
        {
            "exam_name": "UPSC Civil Services",
            "status": "Eligible",
            "age_eligibility": "Eligible (Fits age criteria)",
            "education_eligibility": "Eligible (Graduate degree match)",
            "attempts_analysis": "6 attempts remaining",
            "promotion_path": "SDM -> District Magistrate"
        },
        {
            "exam_name": "SSC CGL",
            "status": "Eligible",
            "age_eligibility": "Eligible",
            "education_eligibility": "Eligible",
            "attempts_analysis": "Multiple attempts allowed",
            "promotion_path": "Assistant Section Officer -> Section Officer"
        }
    ]
    
    gov_jobs = ["National Informatics Centre Scientist" if is_tech else "Administrative Officer"]
    psu_jobs = ["NTPC Graduate Engineer" if is_tech else "Management Trainee"]
    banking_jobs = ["SBI PO", "IBPS Specialist Officer"]
    defence_jobs = ["CDS Entry"]
    private_roles = [r["role"] for r in roles["core"]]
    intl_roles = [f"Remote {primary_role}"]
    
    opportunity_scores = {
        "government_score": 60,
        "private_score": 85,
        "remote_score": 80 if is_tech else 45,
        "international_score": 70 if is_tech else 40,
        "leadership_potential_score": 50
    }
    
    risk_analysis = {
        "demand_risk": "Low",
        "automation_risk": "Low" if is_tech else "Medium",
        "market_competition": "High",
        "future_demand": "High",
        "salary_growth": "Stable"
    }

    improvements = {
        "ats_score": 70,
        "formatting_score": 75,
        "content_score": 68,
        "keyword_score": 70,
        "improvement_suggestions": [
            "Use measurable metrics for achievements.",
            "Include more keywords from target job roles."
        ],
        "resume_rewrite_suggestions": [
            "Rewrite job descriptions using active verbs."
        ],
        "achievement_suggestions": [
            "Quantify results where possible."
        ]
    }

    parsed_json = {
        "personal_info": {
            "name": name,
            "email": email,
            "phone": phone,
            "location": location,
            "summary": summary
        },
        "career_classification": {
            "career_family": career_family,
            "experience_level": "Mid-Level",
            "employability_score": 80,
            "profile_strength": 75
        },
        "skills": skills_structured,
        "skill_graph_edges": edges,
        "career_dna": {
            "personality": personality,
            "traits": {
                "working_style": "Autonomous & Detail-Oriented",
                "growth_potential": "Strong",
                "leadership_potential": "Developing"
            }
        },
        "roles": roles,
        "career_paths": career_paths,
        "opportunities": {
            "eligible_exams": eligible_exams,
            "eligible_gov_jobs": gov_jobs,
            "eligible_psu_jobs": psu_jobs,
            "eligible_banking_jobs": banking_jobs,
            "eligible_defence_jobs": defence_jobs,
            "eligible_private_roles": private_roles,
            "eligible_international_roles": intl_roles,
            "opportunity_scores": opportunity_scores
        },
        "career_risk_analysis": risk_analysis,
        "resume_improvements": improvements
    }

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "skills": ", ".join(detected_skills),
        "experience": experience_list,
        "education": education_list,
        "projects": projects_list,
        "certifications": certifications_str,
        "github": github,
        "linkedin": linkedin,
        "portfolio": portfolio,
        "summary": summary,
        "achievements": [],
        "languages": "",
        "parsed_json": parsed_json
    }


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
    async def run_resume_collection_agent(self, db: Session, candidate_id: int, file_content: bytes, filename: str, background_tasks: Optional[BackgroundTasks] = None, fast: bool = False) -> CandidateResume:
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
        
        # Extract text locally to ensure we always have resume_text fallback for NVIDIA Llama and agent pipeline
        extracted_text = extract_text_from_pdf(file_content)
            
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
                    await self.run_resume_parsing_agent(db_session, cand_id, None, fast=fast)
                except Exception as bg_err:
                    logger.error(f"Background resume parsing failed: {bg_err}")
                finally:
                    db_session.close()
            
            background_tasks.add_task(run_parsing_bg, candidate_id)
        else:
            await self.run_resume_parsing_agent(db, candidate_id, None, fast=fast)
        
        return resume


    # 2. RESUME PARSING AGENT
    async def run_resume_parsing_agent(self, db: Session, candidate_id: int, background_tasks: Optional[BackgroundTasks] = None, fast: bool = False):
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

            # Load PDF bytes directly from storage instead of extracting text locally
            resume = db.query(CandidateResume).filter(
                CandidateResume.candidate_id == candidate_id,
                CandidateResume.is_active == True
            ).first()
            if not resume:
                resume = db.query(CandidateResume).filter(
                    CandidateResume.candidate_id == candidate_id
                ).order_by(CandidateResume.uploaded_at.desc()).first()

            pdf_bytes = None
            if resume and resume.resume_url:
                try:
                    from urllib.parse import urlparse
                    url_str = resume.resume_url
                    folder, filename = "", ""
                    if "/storage/" in url_str:
                        rel_path = url_str.split("/storage/")[1]
                        parts = rel_path.split("/")
                        if len(parts) >= 2:
                            folder = "/".join(parts[:-1])
                            filename = parts[-1]
                    else:
                        parsed = urlparse(url_str)
                        path_parts = parsed.path.strip("/").split("/")
                        if len(path_parts) >= 3:
                            folder = "/".join(path_parts[1:-1])
                            filename = path_parts[-1]
                            
                    if folder and filename:
                        pdf_bytes = storage_service.get_file_content(folder, filename)
                        logger.info(f"Loaded {len(pdf_bytes)} PDF bytes from storage for direct Gemini parsing.")
                        if pdf_bytes and (not profile.resume_text or profile.resume_text.strip() == ""):
                            profile.resume_text = extract_text_from_pdf(pdf_bytes)
                            db.commit()
                except Exception as e:
                    logger.error(f"Failed to read PDF bytes from storage: {e}")

            from app.api.helpers import STATIC_RESUME_PROMPT, map_static_intel_to_legacy_schema
            prompt = STATIC_RESUME_PROMPT
            
            ai_response = None
            data = {}
            if fast:
                logger.info("Fast mode enabled. Bypassing LLM calls.")
                data = fallback_pymupdf_pipeline(pdf_bytes) if pdf_bytes else fallback_parse_resume_text("")
            else:
                if settings.GEMINI_API_KEY:
                    try:
                        logger.info("Calling Gemini 3.5 Flash (gemini-2.0-flash)...")
                        ai_response = await asyncio.to_thread(call_gemini, prompt, True, pdf_bytes, "gemini-2.0-flash")
                    except Exception as flash_err:
                        logger.error(f"Gemini 3.5 Flash failed: {flash_err}")
                
                if not ai_response and settings.GEMINI_API_KEY:
                    try:
                        logger.info("Falling back to Gemini 3.5 Pro (gemini-1.5-pro)...")
                        ai_response = await asyncio.to_thread(call_gemini, prompt, True, pdf_bytes, "gemini-1.5-pro")
                    except Exception as pro_err:
                        logger.error(f"Gemini 3.5 Pro failed: {pro_err}")
                
                if not ai_response and settings.NVIDIA_API_KEY:
                    text_to_parse = profile.resume_text or ""
                    fallback_prompt = prompt + f"\n\nResume Text:\n{text_to_parse}"
                    messages = [{"role": "user", "content": fallback_prompt + "\nRemember: Return ONLY valid JSON, do not include any other text."}]
                    ai_response = await asyncio.to_thread(call_nvidia, messages)
            
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
                    
                    raw_data = json.loads(cleaned)
                    data = map_static_intel_to_legacy_schema(raw_data)
                except Exception as e:
                    logger.error(f"Error parsing AI JSON response: {e}")
                    try:
                        import re
                        fixed = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', cleaned)
                        raw_data = json.loads(fixed)
                        data = map_static_intel_to_legacy_schema(raw_data)
                        logger.info("Successfully recovered JSON using regex normalization.")
                    except Exception as ex:
                        logger.error(f"Fallback JSON recovery failed: {ex}")
                        data = {}
                    
            if not data:
                logger.warning("AI parsing failed. Triggering local PyMuPDF fallback pipeline.")
                data = fallback_pymupdf_pipeline(pdf_bytes) if pdf_bytes else fallback_parse_resume_text("")
                
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
            ria = RIA(db, candidate_id, fast=fast)
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
                db.flush()
            
            existing_data = {}
            if profile.parsed_metadata:
                try:
                    loaded = json.loads(profile.parsed_metadata)
                    if isinstance(loaded, dict):
                        existing_data = loaded
                except Exception:
                    pass
            
            # Merge recalculated profile fields
            existing_data.update(profile_data)
            
            profile.experience_years = exp_years
            profile.generated_roles = json.dumps(preferred_roles)
            profile.specialization = subdomains[0] if subdomains else ""
            profile.current_role = preferred_roles[0] if preferred_roles else ""
            profile.parsed_metadata = json.dumps(existing_data)
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
