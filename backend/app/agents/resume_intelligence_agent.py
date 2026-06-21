"""
Resume Intelligence Agent — Parses resumes, extracts candidate intelligence,
generates roles/strategies, and generates embeddings using NVIDIA NIM services.
Uses LangGraph to compile the Resume Intelligence Pipeline.
"""
import logging
import hashlib
import json
import asyncio
from typing import List, Dict, Any, TypedDict, Optional
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import (
    Candidate, CandidateResume, CandidateProfile, CandidateEmbedding, RecommendationMemory
)
from app.services.orchestrator import call_nvidia
from app.services.embedding_service import embedding_service
from app.services.vector_store import vector_store
from langgraph.graph import StateGraph, END

logger = logging.getLogger("app.agents.resume_intelligence_agent")


class ResumeState(TypedDict):
    candidate_id: int
    resume_id: int
    resume_text: str
    resume_hash: str
    skip_processing: bool
    
    # Extracted fields
    profile_data: dict
    generated_roles: List[str]
    search_strategy: dict
    skills_graph: dict
    embedding: List[float]


class ResumeIntelligenceAgent:
    def __init__(self, db: Session, candidate_id: int):
        self.db = db
        self.candidate_id = candidate_id

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
            profile_obj = self.db.query(CandidateProfile).filter(
                CandidateProfile.candidate_id == candidate_id
            ).order_by(CandidateProfile.created_at.desc()).first()

        if not profile_obj or not profile_obj.resume_text:
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
        
        # Check if the hash matches and role version is v1
        profile_obj = self.db.query(CandidateProfile).filter(
            CandidateProfile.candidate_id == state["candidate_id"],
            CandidateProfile.resume_id == state["resume_id"]
        ).first()
        
        if profile_obj and profile_obj.resume_hash == resume_hash and profile_obj.role_version == "v1":
            logger.info("[Resume Intelligence] Hash and version match. Bypassing AI steps.")
            return {
                "resume_hash": resume_hash,
                "skip_processing": True,
                "profile_data": json.loads(profile_obj.parsed_metadata) if profile_obj.parsed_metadata else {},
                "generated_roles": json.loads(profile_obj.generated_roles) if profile_obj.generated_roles else [],
                "search_strategy": json.loads(profile_obj.search_strategy) if profile_obj.search_strategy else {},
                "skills_graph": json.loads(profile_obj.skills_graph) if profile_obj.skills_graph else {}
            }
            
        return {"resume_hash": resume_hash, "skip_processing": False}

    def extract_candidate_intelligence(self, state: ResumeState) -> Dict[str, Any]:
        if state.get("skip_processing"):
            return {}
            
        logger.info(f"[Resume Intelligence] Extracting details using NVIDIA LLM for candidate {state['candidate_id']}")
        prompt = f"""
You are an expert resume parsing agent. Parse the candidate's resume text and extract structured candidate intelligence.
Return ONLY a strictly valid JSON object with the following keys and data types. Do NOT wrap in markdown blocks, backticks, or write any explanatory text. Ensure all quotes are escaped properly.

Keys:
- name: string
- email: string
- location: string (default: "Remote")
- current_role: string
- previous_roles: array of strings
- experience_years: float (numerical total experience in years)
- relevant_experience: float (experience in their primary domain)
- industry: string (primary industry, e.g. "Construction", "Software", "Healthcare", "Education")
- domain: string (primary domain, e.g. "Civil Engineering", "Software Engineering", "Nursing")
- specialization: string (core focus area)
- skills: array of strings
- technologies: array of strings
- tools: array of strings
- certifications: array of strings
- education: array of strings/objects
- projects: array of strings/objects
- achievements: array of strings
- remote_eligibility: boolean
- seniority: string (e.g. "Junior", "Mid", "Senior", "Lead", "Executive")

Resume Text:
{state["resume_text"]}
"""
        res = call_nvidia(prompt)
        profile_data = {}
        try:
            profile_data = self._clean_and_parse_json(res)
        except Exception as e:
            logger.error(f"Failed to parse NVIDIA output for candidate intelligence: {e}")
            profile_data = {
                "name": "Candidate",
                "email": "",
                "location": "Remote",
                "current_role": "Professional",
                "previous_roles": [],
                "experience_years": 1.0,
                "relevant_experience": 1.0,
                "industry": "Other",
                "domain": "General",
                "specialization": "Generalist",
                "skills": [],
                "technologies": [],
                "tools": [],
                "certifications": [],
                "education": [],
                "projects": [],
                "achievements": [],
                "remote_eligibility": True,
                "seniority": "Mid"
            }
            
        return {"profile_data": profile_data}

    def generate_roles(self, state: ResumeState) -> Dict[str, Any]:
        if state.get("skip_processing"):
            return {}
            
        logger.info(f"[Resume Intelligence] Generating job roles (20-50) using NVIDIA LLM for candidate {state['candidate_id']}")
        profile = state["profile_data"]
        
        prompt = f"""
You are a job role expansion agent. Analyze the candidate intelligence profile and generate between 20 to 50 highly relevant job titles / job roles that this candidate should search for.
These must include primary direct matches, adjacent roles, and expanded titles to maximize job search recall.
Support all professions (including engineering, medical, marketing, finance, HR, etc.) based strictly on their profile.
Return ONLY a valid JSON list of strings, e.g. ["Software Engineer", "React Developer", ...]. Do NOT wrap in markdown or write text.

Candidate Profile:
- Current Role: {profile.get("current_role")}
- Previous Roles: {profile.get("previous_roles")}
- Industry: {profile.get("industry")}
- Domain: {profile.get("domain")}
- Skills: {profile.get("skills")}
- Technologies: {profile.get("technologies")}
- Tools: {profile.get("tools")}
"""
        res = call_nvidia(prompt)
        roles = []
        try:
            roles = self._clean_and_parse_json(res)
            if not isinstance(roles, list):
                roles = [roles]
        except Exception as e:
            logger.error(f"Failed to parse roles: {e}")
            roles = [profile.get("current_role") or "Professional"]

        # Pad to reach at least 20 roles
        if len(roles) < 20:
            base = profile.get("current_role") or "Professional"
            additions = [
                f"{base} Specialist", f"Senior {base}", f"Lead {base}", f"Associate {base}",
                f"{base} Engineer", f"Principal {base}", f"Junior {base}", f"Contract {base}"
            ]
            for a in additions:
                if a not in roles:
                    roles.append(a)
                    
        return {"generated_roles": roles[:50]}

    def generate_search_strategy(self, state: ResumeState) -> Dict[str, Any]:
        if state.get("skip_processing"):
            return {}
            
        profile = state["profile_data"]
        roles = state["generated_roles"]
        
        # Primary roles (top 10), Secondary roles (10 to 30)
        primary_roles = roles[:10]
        secondary_roles = roles[10:30]
        
        # Determine experience range
        exp_years = float(profile.get("experience_years") or 0.0)
        if exp_years <= 2.0:
            exp_range = "0-2 Years"
        elif exp_years <= 5.0:
            exp_range = "2-5 Years"
        elif exp_years <= 8.0:
            exp_range = "5-8 Years"
        else:
            exp_range = "8+ Years"
            
        # Build search query strategy
        strategy = {
            "primary_roles": primary_roles,
            "secondary_roles": secondary_roles,
            "locations": [profile.get("location")] if profile.get("location") else ["India"],
            "experience_range": exp_range,
            "keywords": (profile.get("skills") or [])[:5] + (profile.get("technologies") or [])[:5]
        }
        
        # Build Candidate Skill Graph
        skills_graph = {
            "primary_skills": (profile.get("skills") or [])[:10],
            "secondary_skills": (profile.get("technologies") or [])[:10],
            "tools": (profile.get("tools") or [])[:10],
            "industries": [profile.get("industry")] if profile.get("industry") else [],
            "domains": [profile.get("domain")] if profile.get("domain") else []
        }
        
        return {"search_strategy": strategy, "skills_graph": skills_graph}

    async def generate_embedding(self, state: ResumeState) -> Dict[str, Any]:
        if state.get("skip_processing"):
            # Load candidate embedding from database if available
            db_emb = self.db.query(CandidateEmbedding).filter(
                CandidateEmbedding.candidate_id == state["candidate_id"],
                CandidateEmbedding.resume_id == state["resume_id"]
            ).first()
            if db_emb:
                return {"embedding": json.loads(db_emb.embedding_vector)}
            return {"embedding": [0.0] * 768}
            
        profile = state["profile_data"]
        roles = state["generated_roles"]
        
        resume_text = (
            f"Roles: {', '.join(roles[:10])}\n"
            f"Domain: {profile.get('domain', '')}\n"
            f"Skills: {', '.join(profile.get('skills', []))}\n"
            f"Experience: {profile.get('experience_years', 0)} years\n"
            f"Summary: {profile.get('summary', '')}"
        )
        
        logger.info(f"[Resume Intelligence] Generating profile embedding using NVIDIA Embeddings for candidate {state['candidate_id']}")
        vector = await embedding_service.get_nvidia_embedding(resume_text)
        return {"embedding": vector}

    async def store_candidate_intelligence(self, state: ResumeState) -> Dict[str, Any]:
        if state.get("skip_processing"):
            return {}
            
        candidate_id = state["candidate_id"]
        resume_id = state["resume_id"]
        profile_data = state["profile_data"]
        roles = state["generated_roles"]
        strategy = state["search_strategy"]
        skills_graph = state["skills_graph"]
        embedding = state["embedding"]
        resume_hash = state["resume_hash"]
        
        logger.info(f"[Resume Intelligence] Persisting parsed candidate details for candidate {candidate_id}")
        
        # 1. Update Candidate fields
        candidate = self.db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            candidate.skills = ", ".join(profile_data.get("skills", []))
            candidate.summary = profile_data.get("summary", "")
            candidate.phone = profile_data.get("phone", candidate.phone)
            candidate.parsed_name = profile_data.get("name", candidate.parsed_name)
            candidate.parsed_email = profile_data.get("email", candidate.parsed_email)
            self.db.commit()
            
        # 2. Update CandidateProfile
        profile_obj = self.db.query(CandidateProfile).filter(
            CandidateProfile.candidate_id == candidate_id,
            CandidateProfile.resume_id == resume_id
        ).first()
        
        if not profile_obj:
            profile_obj = CandidateProfile(candidate_id=candidate_id, resume_id=resume_id)
            self.db.add(profile_obj)
            
        profile_obj.resume_hash = resume_hash
        profile_obj.role_version = "v1"
        profile_obj.industry = profile_data.get("industry")
        profile_obj.specialization = profile_data.get("specialization")
        profile_obj.experience_years = float(profile_data.get("experience_years") or 0.0)
        profile_obj.current_role = profile_data.get("current_role")
        profile_obj.generated_roles = json.dumps(roles)
        profile_obj.search_strategy = json.dumps(strategy)
        profile_obj.skills_graph = json.dumps(skills_graph)
        profile_obj.parsed_metadata = json.dumps(profile_data)
        self.db.commit()
        
        # 3. Update CandidateEmbedding
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
        
        # 4. Index in Qdrant candidate_embeddings collection
        try:
            await vector_store.upsert_candidate_vector(
                candidate_id=candidate_id,
                vector=embedding,
                skills=profile_data.get("skills", [])
            )
        except Exception as e:
            logger.error(f"Failed to upsert candidate vector: {e}")
            
        # 5. Initialize RecommendationMemory
        rec_mem = self.db.query(RecommendationMemory).filter(RecommendationMemory.candidate_id == candidate_id).first()
        if not rec_mem:
            rec_mem = RecommendationMemory(
                candidate_id=candidate_id,
                preferred_roles=json.dumps(roles[:5]),
                preferred_locations=json.dumps([profile_data.get("location")] if profile_data.get("location") else []),
                preferred_companies=json.dumps([]),
                ignored_roles=json.dumps([])
            )
            self.db.add(rec_mem)
            self.db.commit()
            
        # Invalidate caches
        try:
            import app.services.job_cache as job_cache
            await job_cache.invalidate_candidate_profile(candidate_id)
            await job_cache.invalidate_generated_roles(candidate_id)
            await job_cache.invalidate_search_strategy(candidate_id)
            await job_cache.invalidate_jobs_pool(candidate_id)
        except Exception as cache_err:
            logger.warning(f"Failed to invalidate cache: {cache_err}")
            
        return {}

    def _build_graph(self):
        workflow = StateGraph(ResumeState)
        
        workflow.add_node("load_resume", self.load_resume)
        workflow.add_node("generate_resume_hash", self.generate_resume_hash)
        workflow.add_node("extract_candidate_intelligence", self.extract_candidate_intelligence)
        workflow.add_node("generate_roles", self.generate_roles)
        workflow.add_node("generate_search_strategy", self.generate_search_strategy)
        workflow.add_node("generate_embedding", self.generate_embedding)
        workflow.add_node("store_candidate_intelligence", self.store_candidate_intelligence)
        
        workflow.set_entry_point("load_resume")
        
        workflow.add_edge("load_resume", "generate_resume_hash")
        workflow.add_edge("generate_resume_hash", "extract_candidate_intelligence")
        workflow.add_edge("extract_candidate_intelligence", "generate_roles")
        workflow.add_edge("generate_roles", "generate_search_strategy")
        workflow.add_edge("generate_search_strategy", "generate_embedding")
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
            profile_data={},
            generated_roles=[],
            search_strategy={},
            skills_graph={},
            embedding=[]
        )
        app = self._build_graph()
        final_state = await app.ainvoke(initial_state)
        return final_state
