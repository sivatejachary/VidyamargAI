"""
Resume Intelligence Agent — Parses resumes, extracts candidate intelligence,
generates career DNA, skill graphs, role confidence, opportunity score dials,
exam eligibility, risks and improvements, and stores them in PostgreSQL/Qdrant.
Uses LangGraph to compile the Resume Intelligence Pipeline.
"""
import logging
import hashlib
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, TypedDict, Optional
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import (
    Candidate, CandidateResume, CandidateProfile, CandidateEmbedding
)
from app.models.job_models import (
    ResumeVersion, ResumeEmbedding as ResumeEmbeddingVersion, CandidateSkillGraph,
    CandidateCareerGraph, CandidateCareerDNA, CareerPath, CareerOpportunity,
    ResumeImprovement, CareerEligibilityMatrix
)
from app.services.orchestrator import call_nvidia, call_gemini
from app.core.config import settings
from app.services.embedding_service import embedding_service
from app.services.vector_store import vector_store
from app.api.helpers import STATIC_RESUME_PROMPT, map_static_intel_to_legacy_schema
from langgraph.graph import StateGraph, END

logger = logging.getLogger("app.agents.resume_intelligence_agent")


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


class ResumeState(TypedDict):
    candidate_id: int
    resume_id: int
    resume_text: str
    resume_hash: str
    skip_processing: bool
    fast: bool
    
    # Extracted / generated career intelligence fields
    career_intelligence: dict
    embedding: List[float]


class ResumeIntelligenceAgent:
    def __init__(self, db: Session, candidate_id: int, fast: bool = False):
        self.db = db
        self.candidate_id = candidate_id
        self.fast = fast

    def _clean_and_parse_json(self, text: str) -> Any:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(cleaned)
            return obj

    def load_resume(self, state: ResumeState) -> Dict[str, Any]:
        candidate_id = state["candidate_id"]
        logger.info(f"[Resume Intelligence] Loading resume for candidate {candidate_id}")
        
        # Fetch the active resume
        resume = self.db.query(CandidateResume).filter(
            CandidateResume.candidate_id == candidate_id,
            CandidateResume.is_active == True
        ).first()
        
        # Fallback to the latest resume if no active resume is selected
        if not resume:
            resume = self.db.query(CandidateResume).filter(
                CandidateResume.candidate_id == candidate_id
            ).order_by(CandidateResume.uploaded_at.desc()).first()
            
        if not resume:
            logger.warning(f"No resume record found for candidate {candidate_id}")
            return {"skip_processing": True}

        # Retrieve resume text from CandidateProfile
        profile_obj = self.db.query(CandidateProfile).filter(
            CandidateProfile.candidate_id == candidate_id,
            CandidateProfile.resume_id == resume.id
        ).first()

        # Fallback to latest CandidateProfile text if not found
        if not profile_obj:
            profile_obj = CandidateProfile(candidate_id=candidate_id, resume_id=resume.id)
            self.db.add(profile_obj)
            self.db.commit()

        if not profile_obj.resume_text or profile_obj.resume_text.strip() == "":
            try:
                from urllib.parse import urlparse
                from app.services.storage import storage_service
                from app.services.orchestrator import extract_text_from_pdf
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
                    if pdf_bytes:
                        profile_obj.resume_text = extract_text_from_pdf(pdf_bytes)
                        self.db.commit()
            except Exception as e:
                logger.error(f"Failed to auto-extract resume text in load_resume: {e}")

        if not profile_obj.resume_text or profile_obj.resume_text.strip() == "":
            logger.warning(f"No resume text available for candidate {candidate_id}")
            return {"resume_id": resume.id, "skip_processing": True}

        return {
            "resume_id": resume.id,
            "resume_text": profile_obj.resume_text,
            "skip_processing": False
        }

    def generate_resume_hash(self, state: ResumeState) -> Dict[str, Any]:
        if state.get("skip_processing"):
            return {}
            
        text = state["resume_text"]
        resume_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        
        # Check if the hash matches and role version is v2 (for detailed intelligence)
        profile_obj = self.db.query(CandidateProfile).filter(
            CandidateProfile.candidate_id == state["candidate_id"],
            CandidateProfile.resume_id == state["resume_id"]
        ).first()
        
        # Fetch detailed eligibility matrix to check if it exists
        eligibility = self.db.query(CareerEligibilityMatrix).filter(
            CareerEligibilityMatrix.candidate_id == state["candidate_id"]
        ).first()
        
        if profile_obj and profile_obj.resume_hash == resume_hash and profile_obj.role_version == "v2" and eligibility:
            logger.info("[Resume Intelligence] Hash and version match. Loading pre-existing career intelligence.")
            
            # Fetch structured improvements
            improvements = self.db.query(ResumeImprovement).filter(
                ResumeImprovement.candidate_id == state["candidate_id"]
            ).first()
            
            # Fetch skill graph
            skill_graph = self.db.query(CandidateSkillGraph).filter(
                CandidateSkillGraph.candidate_id == state["candidate_id"]
            ).first()

            # Reconstruct the career_intelligence dictionary
            career_intel = {
                "personal_info": safe_loads(profile_obj.parsed_metadata).get("personal_info", {}),
                "career_classification": {
                    "career_family": eligibility.career_family,
                    "experience_level": safe_loads(profile_obj.parsed_metadata).get("career_level", "Mid-Level"),
                    "employability_score": safe_loads(profile_obj.parsed_metadata).get("employability_score", 80),
                    "profile_strength": safe_loads(profile_obj.parsed_metadata).get("profile_strength", 75)
                },
                "skills": skill_graph.skills if skill_graph else [],
                "skill_graph_edges": skill_graph.edges if skill_graph else [],
                "career_dna": {
                    "personality": eligibility.opportunity_scores.get("personality", "Builder") if eligibility.opportunity_scores else "Builder",
                    "traits": eligibility.risk_analysis.get("traits", {}) if eligibility.risk_analysis else {}
                },
                "roles": safe_loads(profile_obj.generated_roles),
                "opportunities": {
                    "eligible_exams": eligibility.eligible_exams,
                    "eligible_gov_jobs": eligibility.eligible_gov_jobs,
                    "eligible_psu_jobs": eligibility.eligible_psu_jobs,
                    "eligible_banking_jobs": eligibility.eligible_banking_jobs,
                    "eligible_defence_jobs": eligibility.eligible_defence_jobs,
                    "eligible_private_roles": eligibility.eligible_private_roles,
                    "eligible_international_roles": eligibility.eligible_international_roles,
                    "opportunity_scores": eligibility.opportunity_scores
                },
                "career_risk_analysis": eligibility.risk_analysis,
                "resume_improvements": {
                    "ats_score": improvements.ats_score if improvements else 75,
                    "formatting_score": improvements.formatting_score if improvements else 75,
                    "content_score": improvements.content_score if improvements else 75,
                    "keyword_score": improvements.keyword_score if improvements else 75,
                    "improvement_suggestions": improvements.improvement_suggestions if improvements else [],
                    "resume_rewrite_suggestions": improvements.resume_rewrite_suggestions if improvements else [],
                    "achievement_suggestions": improvements.achievement_suggestions if improvements else []
                }
            }
            
            return {
                "resume_hash": resume_hash,
                "skip_processing": True,
                "career_intelligence": career_intel
            }
            
        return {"resume_hash": resume_hash, "skip_processing": False}

    async def extract_career_intelligence(self, state: ResumeState) -> Dict[str, Any]:
        if state.get("skip_processing"):
            return {}
            
        candidate_id = state["candidate_id"]
        logger.info(f"[Resume Intelligence] Extracting career intelligence for candidate {candidate_id}")
        
        # Load candidate details for fallbacks
        candidate = self.db.query(Candidate).filter(Candidate.id == candidate_id).first()
        skills_list = [s.strip() for s in candidate.skills.split(",") if s.strip()] if candidate and candidate.skills else []
        exp_years = 1.0
        try:
            profile_obj = self.db.query(CandidateProfile).filter(CandidateProfile.candidate_id == candidate_id).order_by(CandidateProfile.created_at.desc()).first()
            if profile_obj and profile_obj.experience_years:
                exp_years = float(profile_obj.experience_years)
        except Exception:
            pass

        # Load PDF bytes directly from storage using CandidateResume if we need to fall back
        pdf_bytes = None
        try:
            resume = self.db.query(CandidateResume).filter(
                CandidateResume.candidate_id == candidate_id,
                CandidateResume.is_active == True
            ).first()
            if not resume:
                resume = self.db.query(CandidateResume).filter(
                    CandidateResume.candidate_id == candidate_id
                ).order_by(CandidateResume.uploaded_at.desc()).first()
            
            if resume and resume.resume_url:
                from urllib.parse import urlparse
                from app.services.storage import storage_service
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
                    logger.info(f"[Resume Intelligence] Loaded {len(pdf_bytes)} PDF bytes from storage for fallback/Pro parsing.")
        except Exception as e:
            logger.error(f"[Resume Intelligence] Failed to load PDF bytes from storage: {e}")

        # Fast Mode / Dry-run checks
        if state.get("fast") or self.fast:
            logger.info("[Resume Intelligence] Fast mode enabled. Running rules-based parser fallback.")
            if pdf_bytes:
                from app.services.orchestrator import fallback_pymupdf_pipeline
                fallback_res = fallback_pymupdf_pipeline(pdf_bytes)
                career_intel = fallback_res.get("parsed_json", {})
            else:
                career_intel = get_fallback_resume_intelligence(candidate, skills_list, exp_years)
            
            # Save history in DB
            try:
                from app.models.job_models import ResumeAIAnalysis
                analysis_rec = ResumeAIAnalysis(
                    candidate_id=candidate_id,
                    source_type="FALLBACK",
                    raw_response=json.dumps(career_intel),
                    parsed_json=career_intel,
                    confidence_score="MEDIUM"
                )
                self.db.add(analysis_rec)
                self.db.commit()
            except Exception as db_err:
                self.db.rollback()
                logger.error(f"[Resume Intelligence] Failed to store fallback analysis: {db_err}")
                
            return {"career_intelligence": career_intel}

        prompt = STATIC_RESUME_PROMPT + f"\n\nResume Text:\n{state['resume_text']}"

        ai_response = None
        career_intel = {}
        source_type = "GEMINI"
        confidence_score = "HIGH"

        # 1. Primary Model: Gemini Flash
        if settings.GEMINI_API_KEY:
            try:
                logger.info("[Resume Intelligence] Invoking Gemini Flash (gemini-2.0-flash) for parsing...")
                ai_response = await asyncio.to_thread(call_gemini, prompt, True, pdf_bytes, "gemini-2.0-flash")
            except Exception as gemini_err:
                logger.error(f"[Resume Intelligence] Gemini Flash call failed: {gemini_err}")

        # 2. Fallback Model: Gemini Pro
        if not ai_response and settings.GEMINI_API_KEY:
            try:
                logger.info("[Resume Intelligence] Falling back to Gemini Pro (gemini-1.5-pro) for parsing...")
                ai_response = await asyncio.to_thread(call_gemini, prompt, True, pdf_bytes, "gemini-1.5-pro")
            except Exception as pro_err:
                logger.error(f"[Resume Intelligence] Gemini Pro fallback failed: {pro_err}")

        # 3. Nvidia fallback as intermediate backup before local PyMuPDF
        if not ai_response and settings.NVIDIA_API_KEY:
            try:
                logger.info("[Resume Intelligence] Falling back to NVIDIA Llama for parsing...")
                messages = [{"role": "user", "content": prompt + "\nRemember: Return ONLY valid JSON, do not include any other text."}]
                ai_response = await asyncio.to_thread(call_nvidia, messages)
            except Exception as nvidia_err:
                logger.error(f"[Resume Intelligence] NVIDIA Llama fallback failed: {nvidia_err}")

        # Parse AI response if successful
        if ai_response:
            try:
                raw_intel = self._clean_and_parse_json(ai_response)
                career_intel = map_static_intel_to_legacy_schema(raw_intel)
            except Exception as parse_err:
                logger.error(f"[Resume Intelligence] Failed to parse JSON output: {parse_err}. Raw output was: {ai_response[:200]}")

        # 4. Rule-based / PyMuPDF fallback
        if not career_intel:
            logger.warning("[Resume Intelligence] LLM parsing failed or keys are empty. Running programmatic fallback.")
            source_type = "FALLBACK"
            confidence_score = "MEDIUM"
            if pdf_bytes:
                from app.services.orchestrator import fallback_pymupdf_pipeline
                fallback_res = fallback_pymupdf_pipeline(pdf_bytes)
                career_intel = fallback_res.get("parsed_json", {})
            else:
                career_intel = get_fallback_resume_intelligence(candidate, skills_list, exp_years)

        # 5. Persist history log to database (never overwriting)
        try:
            from app.models.job_models import ResumeAIAnalysis
            analysis_rec = ResumeAIAnalysis(
                candidate_id=candidate_id,
                source_type=source_type,
                raw_response=ai_response if ai_response else json.dumps(career_intel),
                parsed_json=career_intel,
                confidence_score=confidence_score
            )
            self.db.add(analysis_rec)
            self.db.commit()
            logger.info(f"[Resume Intelligence] Successfully stored resume AI analysis (Source: {source_type})")
        except Exception as db_err:
            self.db.rollback()
            logger.error(f"[Resume Intelligence] Failed to store resume AI analysis in DB: {db_err}")

        return {"career_intelligence": career_intel}

    async def generate_embedding(self, state: ResumeState) -> Dict[str, Any]:
        if state.get("skip_processing"):
            db_emb = self.db.query(CandidateEmbedding).filter(
                CandidateEmbedding.candidate_id == state["candidate_id"],
                CandidateEmbedding.resume_id == state["resume_id"]
            ).first()
            if db_emb:
                return {"embedding": safe_loads(db_emb.embedding_vector, [])}
            return {"embedding": [0.0] * 768}
            
        intel = state["career_intelligence"]
        personal = intel.get("personal_info", {})
        classification = intel.get("career_classification", {})
        skills = [s.get("name", "") for s in intel.get("skills", [])]
        
        resume_summary_text = (
            f"Name: {personal.get('name', '')}\n"
            f"Family: {classification.get('career_family', '')}\n"
            f"Level: {classification.get('experience_level', '')}\n"
            f"Skills: {', '.join(skills)}\n"
            f"Summary: {personal.get('summary', '')}"
        )
        
        logger.info(f"[Resume Intelligence] Generating profile embedding for candidate {state['candidate_id']}")
        try:
            vector = await embedding_service.get_nvidia_embedding(resume_summary_text)
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}. Using zero-vector fallback.")
            vector = [0.0] * 768
        return {"embedding": vector}

    async def store_candidate_intelligence(self, state: ResumeState) -> Dict[str, Any]:
        if state.get("skip_processing"):
            return {}
            
        candidate_id = state["candidate_id"]
        resume_id = state["resume_id"]
        intel = state["career_intelligence"]
        embedding = state["embedding"]
        resume_hash = state["resume_hash"]
        
        logger.info(f"[Resume Intelligence] Persisting full career intelligence for candidate {candidate_id}")
        
        # Gather info
        personal = intel.get("personal_info", {})
        classification = intel.get("career_classification", {})
        skills_raw = intel.get("skills", [])
        edges_raw = intel.get("skill_graph_edges", [])
        dna_raw = intel.get("career_dna", {})
        roles_raw = intel.get("roles", {})
        paths_raw = intel.get("career_paths", [])
        opportunities_raw = intel.get("opportunities", {})
        risk_raw = intel.get("career_risk_analysis", {})
        improvements_raw = intel.get("resume_improvements", {})
        
        skills_comma = ", ".join([s.get("name", "") for s in skills_raw if s.get("name")])
        
        # 1. Update Candidate fields
        candidate = self.db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            candidate.skills = skills_comma or candidate.skills
            candidate.summary = personal.get("summary") or candidate.summary or ""
            candidate.phone = personal.get("phone") or candidate.phone
            candidate.parsed_name = personal.get("name") or candidate.parsed_name
            candidate.parsed_email = personal.get("email") or candidate.parsed_email
            
            # Enrich candidate social links and details
            if personal.get("linkedin"):
                candidate.linkedin = personal.get("linkedin")
            if personal.get("github"):
                candidate.github = personal.get("github")
            if personal.get("portfolio"):
                candidate.portfolio = personal.get("portfolio")
            if personal.get("location"):
                candidate.address = personal.get("location")
                
            if intel.get("education"):
                candidate.education = json.dumps(intel.get("education"))
            if intel.get("experience"):
                candidate.experience = json.dumps(intel.get("experience"))
            if intel.get("projects"):
                candidate.projects = json.dumps(intel.get("projects"))
                
            if intel.get("certifications"):
                cert_val = intel.get("certifications")
                if isinstance(cert_val, list):
                    candidate.certifications = ", ".join([c.get("certification", "") if isinstance(c, dict) else str(c) for c in cert_val])
                else:
                    candidate.certifications = str(cert_val)
                    
            if candidate.parsed_name and candidate.user:
                candidate.user.full_name = candidate.parsed_name
            self.db.commit()
            
        # 2. Update CandidateProfile (Version v2)
        profile_obj = self.db.query(CandidateProfile).filter(
            CandidateProfile.candidate_id == candidate_id,
            CandidateProfile.resume_id == resume_id
        ).first()
        
        if not profile_obj:
            profile_obj = CandidateProfile(candidate_id=candidate_id, resume_id=resume_id)
            self.db.add(profile_obj)
            
        profile_obj.resume_hash = resume_hash
        profile_obj.role_version = "v2"  # Upgrade version to v2
        profile_obj.industry = classification.get("career_family")
        profile_obj.specialization = personal.get("location")
        
        # Calculate experience years
        exp_years = 0.0
        if skills_raw:
            exp_years = max([s.get("experience_years", 0.0) for s in skills_raw])
        profile_obj.experience_years = float(exp_years or 1.0)
        
        # Current role
        core_roles = roles_raw.get("core", [])
        profile_obj.current_role = core_roles[0].get("role") if core_roles else "Professional"
        
        profile_obj.generated_roles = json.dumps(roles_raw)
        profile_obj.search_strategy = json.dumps({
            "primary_roles": [r.get("role") for r in core_roles],
            "locations": [personal.get("location", "Remote")],
            "keywords": [s.get("name") for s in skills_raw][:5]
        })
        profile_obj.skills_graph = json.dumps(skills_raw)
        
        profile_data = {
            "skills": [s.get("name") for s in skills_raw],
            "experience_years": profile_obj.experience_years,
            "education": personal.get("summary", ""),
            "summary": personal.get("summary", ""),
            "domain": classification.get("career_family"),
            "career_level": classification.get("experience_level"),
            "employability_score": classification.get("employability_score", 80),
            "profile_strength": classification.get("profile_strength", 75),
            "personal_info": personal
        }
        existing_data = {}
        if profile_obj.parsed_metadata:
            try:
                loaded = json.loads(profile_obj.parsed_metadata)
                if isinstance(loaded, dict):
                    existing_data = loaded
            except Exception:
                pass
        existing_data.update(profile_data)
        # Store raw static intelligence if present in mapped intel
        if "raw_static_intel" in intel:
            existing_data["raw_static_intel"] = intel["raw_static_intel"]
        elif "personal_info" in intel:
            existing_data["raw_static_intel"] = intel
            
        profile_obj.parsed_metadata = json.dumps(existing_data)
        self.db.commit()
        
        # 3. Create or Update ResumeVersion record
        resume_rec = self.db.query(CandidateResume).filter(CandidateResume.id == resume_id).first()
        resume_url = resume_rec.resume_url if resume_rec else "local://resume"
        
        version_name = f"Resume_V_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        resume_version = ResumeVersion(
            candidate_id=candidate_id,
            resume_url=resume_url,
            extracted_text=state["resume_text"],
            parsed_json=intel,
            version_name=version_name,
            is_active=True
        )
        # Deactivate all other resume versions
        self.db.query(ResumeVersion).filter(ResumeVersion.candidate_id == candidate_id).update({ResumeVersion.is_active: False})
        self.db.add(resume_version)
        self.db.commit()
        
        # 4. Create or Update ResumeEmbeddingVersion
        res_emb = ResumeEmbeddingVersion(
            candidate_id=candidate_id,
            resume_id=resume_id,
            resume_version_id=resume_version.id,
            embedding_model="nvidia/nv-embedqa-e5-v5",
            embedding_vector=json.dumps(embedding)
        )
        self.db.add(res_emb)
        self.db.commit()
        
        # 5. Create or Update CandidateEmbedding (legacy table compatibility)
        emb_obj = self.db.query(CandidateEmbedding).filter(
            CandidateEmbedding.candidate_id == candidate_id,
            CandidateEmbedding.resume_id == resume_id
        ).first()
        
        if not emb_obj:
            emb_obj = CandidateEmbedding(candidate_id=candidate_id, resume_id=resume_id)
            self.db.add(emb_obj)
            
        emb_obj.embedding_model = "nvidia/nv-embedqa-e5-v5"
        emb_obj.embedding_vector = json.dumps(embedding)
        self.db.commit()
        
        # 6. Save CandidateSkillGraph
        self.db.query(CandidateSkillGraph).filter(CandidateSkillGraph.candidate_id == candidate_id).delete()
        skill_graph_obj = CandidateSkillGraph(
            candidate_id=candidate_id,
            skills=skills_raw,
            edges=edges_raw
        )
        self.db.add(skill_graph_obj)
        self.db.commit()
        
        # 7. Save CandidateCareerGraph
        self.db.query(CandidateCareerGraph).filter(CandidateCareerGraph.candidate_id == candidate_id).delete()
        career_graph_obj = CandidateCareerGraph(
            candidate_id=candidate_id,
            career_paths=paths_raw
        )
        self.db.add(career_graph_obj)
        self.db.commit()
        
        # 8. Save CandidateCareerDNA
        self.db.query(CandidateCareerDNA).filter(CandidateCareerDNA.candidate_id == candidate_id).delete()
        career_dna_obj = CandidateCareerDNA(
            candidate_id=candidate_id,
            personality=dna_raw.get("personality"),
            traits=dna_raw.get("traits", {})
        )
        self.db.add(career_dna_obj)
        self.db.commit()
        
        # 9. Save CareerPath entities
        self.db.query(CareerPath).filter(CareerPath.candidate_id == candidate_id).delete()
        for idx, path in enumerate(paths_raw):
            cpath = CareerPath(
                candidate_id=candidate_id,
                path_name=path.get("path_name", f"Career Track {idx+1}"),
                steps=path.get("steps", []),
                milestones=path.get("milestones", [])
            )
            self.db.add(cpath)
        self.db.commit()
            
        # 10. Save CareerOpportunities
        self.db.query(CareerOpportunity).filter(CareerOpportunity.candidate_id == candidate_id).delete()
        # Flat list of generated core/related/adjacent roles to populate opportunities
        confidence_scores = opportunities_raw.get("opportunity_scores", {})
        for cat, list_roles in roles_raw.items():
            for r in list_roles[:5]:  # Take top 5 from each category to store opportunities
                copp = CareerOpportunity(
                    candidate_id=candidate_id,
                    role_title=r.get("role"),
                    category=cat,
                    confidence_score=float(r.get("confidence", 80)),
                    growth_score=float(confidence_scores.get("private_score", 85) if "private" in cat or cat == "core" else confidence_scores.get("government_score", 70)),
                    salary_potential={"min": 1000000.0, "max": 2500000.0, "currency": "INR"},
                    remote_potential=float(confidence_scores.get("remote_score", 80)),
                    government_potential=float(confidence_scores.get("government_score", 70)),
                    international_potential=float(confidence_scores.get("international_score", 75)),
                    requirements_match={"matched": [s.get("name") for s in skills_raw[:3]], "missing": []}
                )
                self.db.add(copp)
        self.db.commit()
                
        # 11. Save ResumeImprovement suggestions
        self.db.query(ResumeImprovement).filter(ResumeImprovement.candidate_id == candidate_id).delete()
        imp_obj = ResumeImprovement(
            candidate_id=candidate_id,
            ats_score=improvements_raw.get("ats_score", 75),
            formatting_score=improvements_raw.get("formatting_score", 75),
            content_score=improvements_raw.get("content_score", 75),
            keyword_score=improvements_raw.get("keyword_score", 75),
            improvement_suggestions=improvements_raw.get("improvement_suggestions", []),
            resume_rewrite_suggestions=improvements_raw.get("resume_rewrite_suggestions", []),
            achievement_suggestions=improvements_raw.get("achievement_suggestions", [])
        )
        self.db.add(imp_obj)
        self.db.commit()
        
        # 12. Save CareerEligibilityMatrix
        self.db.query(CareerEligibilityMatrix).filter(CareerEligibilityMatrix.candidate_id == candidate_id).delete()
        elig_obj = CareerEligibilityMatrix(
            candidate_id=candidate_id,
            career_family=classification.get("career_family"),
            eligible_exams=opportunities_raw.get("eligible_exams", []),
            eligible_gov_jobs=opportunities_raw.get("eligible_gov_jobs", []),
            eligible_psu_jobs=opportunities_raw.get("eligible_psu_jobs", []),
            eligible_banking_jobs=opportunities_raw.get("eligible_banking_jobs", []),
            eligible_defence_jobs=opportunities_raw.get("eligible_defence_jobs", []),
            eligible_private_roles=opportunities_raw.get("eligible_private_roles", []),
            eligible_international_roles=opportunities_raw.get("eligible_international_roles", []),
            opportunity_scores=opportunities_raw.get("opportunity_scores", {}),
            risk_analysis=risk_raw
        )
        self.db.add(elig_obj)
        self.db.commit()
        
        # Index in Qdrant candidate_embeddings collection
        try:
            await vector_store.upsert_candidate_vector(
                candidate_id=candidate_id,
                vector=embedding,
                skills=[s.get("name") for s in skills_raw]
            )
        except Exception as e:
            logger.error(f"Failed to upsert candidate vector: {e}")
            
        return {}

    def _build_graph(self):
        workflow = StateGraph(ResumeState)
        
        workflow.add_node("load_resume", self.load_resume)
        workflow.add_node("generate_resume_hash", self.generate_resume_hash)
        workflow.add_node("extract_career_intelligence", self.extract_career_intelligence)
        workflow.add_node("generate_embedding", self.generate_embedding)
        workflow.add_node("store_candidate_intelligence", self.store_candidate_intelligence)
        
        workflow.set_entry_point("load_resume")
        
        workflow.add_edge("load_resume", "generate_resume_hash")
        workflow.add_edge("generate_resume_hash", "extract_career_intelligence")
        workflow.add_edge("extract_career_intelligence", "generate_embedding")
        workflow.add_edge("generate_embedding", "store_candidate_intelligence")
        workflow.add_edge("store_candidate_intelligence", END)
        
        return workflow.compile()

    async def execute_pipeline(self) -> dict:
        initial_state = ResumeState(
            candidate_id=self.candidate_id,
            resume_id=0,
            resume_text="",
            resume_hash="",
            skip_processing=False,
            fast=self.fast,
            career_intelligence={},
            embedding=[]
        )
        app = self._build_graph()
        final_state = await app.ainvoke(initial_state)
        return final_state


def get_fallback_resume_intelligence(candidate, skills_list, experience_years) -> dict:
    # Heuristic career family classification
    skills_lower = [s.lower() for s in skills_list]
    is_tech = any(s in ["python", "javascript", "java", "c++", "typescript", "react", "node", "aws", "docker", "machine learning", "ai", "deep learning", "sql"] for s in skills_lower)
    
    career_family = "Engineering" if is_tech else "Business"
    if any(s in ["biology", "nursing", "medicine", "mbbs", "bds"] for s in skills_lower):
        career_family = "Healthcare"
    elif any(s in ["law", "llb", "legal"] for s in skills_lower):
        career_family = "Legal"
    elif any(s in ["finance", "accounting", "ca", "cfa", "banking"] for s in skills_lower):
        career_family = "Finance"
        
    personality = "Builder" if is_tech else "Operator"
    if experience_years >= 5:
        personality = "Manager"
        career_level = "Senior"
    elif experience_years >= 2:
        career_level = "Mid-Level"
    else:
        career_level = "Entry-Level"
        
    # Generate structured skills list
    structured_skills = []
    for s in skills_list[:12]:
        score = 80 if len(s) % 2 == 0 else 75
        structured_skills.append({
            "name": s,
            "score": score,
            "confidence": 85,
            "market_demand": 80,
            "experience_years": max(1.0, round(experience_years * 0.6, 1))
        })
    if not structured_skills:
        structured_skills = [
            {"name": "Communication", "score": 80, "confidence": 90, "market_demand": 75, "experience_years": max(1.0, experience_years)},
            {"name": "Problem Solving", "score": 85, "confidence": 90, "market_demand": 80, "experience_years": max(1.0, experience_years)}
        ]
        
    # Generate skill graph edges
    edges = []
    if len(structured_skills) >= 2:
        for i in range(len(structured_skills) - 1):
            edges.append({"from": structured_skills[i]["name"], "to": structured_skills[i+1]["name"]})
            
    # Roles with confidence scores
    candidate_role = None
    if candidate:
        if hasattr(candidate, "current_role") and candidate.current_role:
            candidate_role = candidate.current_role
        elif hasattr(candidate, "profiles") and candidate.profiles:
            candidate_role = candidate.profiles[0].current_role
            
    primary_role = candidate_role or ("Software Engineer" if is_tech else "Business Analyst")
    roles = {
        "core": [{"role": primary_role, "confidence": 95}, {"role": f"Senior {primary_role}" if experience_years >= 3 else f"Associate {primary_role}", "confidence": 88}],
        "related": [{"role": "Systems Engineer" if is_tech else "Project Associate", "confidence": 82}],
        "adjacent": [{"role": "Technical Consultant" if is_tech else "Operations Analyst", "confidence": 78}],
        "transferable": [{"role": "Product Specialist", "confidence": 72}],
        "future": [{"role": "Technical Architect" if is_tech else "Operations Manager", "confidence": 68}],
        "leadership": [{"role": "Engineering Lead" if is_tech else "Team Manager", "confidence": 60}]
    }
    
    # Career Paths
    career_paths = [
        {
            "path_name": f"{primary_role} Growth Path",
            "steps": [primary_role, f"Senior {primary_role}", f"Lead {primary_role}", f"Principal {primary_role}"],
            "milestones": ["Complete core domain projects", "Mentor junior team members", "Define system architecture"]
        }
    ]
    
    # Opportunities
    eligible_exams = [
        {
            "exam_name": "UPSC Civil Services",
            "status": "Eligible",
            "age_eligibility": "Eligible (Age Limit: 32, candidate fits)",
            "education_eligibility": "Eligible (Graduate degree match)",
            "attempts_analysis": "6 attempts remaining",
            "promotion_path": "SDM -> District Magistrate -> Secretary"
        },
        {
            "exam_name": "SSC CGL",
            "status": "Eligible",
            "age_eligibility": "Eligible (Under 30)",
            "education_eligibility": "Eligible (Graduate)",
            "attempts_analysis": "Unlimited attempts until age limit",
            "promotion_path": "Assistant Section Officer -> Section Officer"
        }
    ]
    
    # Opportunities Matrix
    gov_jobs = [f"Scientist B in National Informatics Centre" if is_tech else "Administrative Officer in Government Dept"]
    psu_jobs = [f"Graduate Engineer Trainee at NTPC/IOCL" if is_tech else "Management Trainee at SAIL"]
    banking_jobs = ["SBI PO", "IBPS Specialist Officer"]
    defence_jobs = ["CDS Technical Entry" if is_tech else "Short Service Commission Officer"]
    private_roles = [r["role"] for r in roles["core"] + roles["related"]]
    intl_roles = [f"Remote {primary_role} (US/EU Markets)"]
    
    opportunity_scores = {
        "government_score": 65,
        "private_score": 90,
        "remote_score": 85 if is_tech else 50,
        "international_score": 75 if is_tech else 45,
        "leadership_potential_score": 70 if experience_years >= 3 else 50
    }
    
    risk_analysis = {
        "demand_risk": "Low" if is_tech else "Medium",
        "automation_risk": "Low" if is_tech else "Medium",
        "market_competition": "High",
        "future_demand": "High",
        "salary_growth": "High (10-15% YoY)"
    }
    
    improvements = {
        "ats_score": 72,
        "formatting_score": 78,
        "content_score": 68,
        "keyword_score": 70,
        "improvement_suggestions": [
            "Add quantitative achievements (e.g. 'improved performance by 20%')",
            "List more industry-standard keyword skills",
            "Refine the professional summary to highlight leadership indicators"
        ],
        "resume_rewrite_suggestions": [
            "Rewrite project description to focus on impact and technical tools used.",
            "Use active verbs like 'Architected', 'Spearheaded', 'Optimized' instead of 'Responsible for'."
        ],
        "achievement_suggestions": [
            "Mention any awards, certifications, or major milestones hit during tenure."
        ]
    }
    
    return {
        "personal_info": {
            "name": (candidate.parsed_name if candidate else None) or "Candidate",
            "email": (candidate.parsed_email if candidate else None) or "",
            "phone": (candidate.phone if candidate else None) or "",
            "location": (candidate.address if candidate else None) or "Remote",
            "summary": (candidate.summary if candidate else None) or ""
        },
        "career_classification": {
            "career_family": career_family,
            "experience_level": career_level,
            "employability_score": 80,
            "profile_strength": 75
        },
        "skills": structured_skills,
        "skill_graph_edges": edges,
        "career_dna": {
            "personality": personality,
            "traits": {
                "working_style": "Highly Autonomous & Solution-Oriented",
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
