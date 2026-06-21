"""
Job Supervisor Agent — central orchestrator for job discovery, matching, and ranking.
Uses LangGraph to compile the Job Discovery Pipeline.
"""
import logging
import json
import re
import asyncio
from typing import List, Dict, Any, TypedDict, Optional
from sqlalchemy.orm import Session

from app.models.models import (
    Candidate, CandidateResume, CandidateProfile, CandidateEmbedding, JobMatch, RecommendationMemory
)
from app.services.vector_store import vector_store
from app.services.embedding_service import embedding_service
import app.services.job_cache as job_cache
from langgraph.graph import StateGraph, END

logger = logging.getLogger("app.agents.job_supervisor")


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


class AgentState(TypedDict):
    run_id: int
    candidate_id: int
    profile: dict
    resume_id: int
    resume_version: str
    candidate_embedding: List[float]
    generated_roles: List[str]
    search_strategy: dict
    jobs: List[dict]
    ranked_jobs: List[dict]
    cached_found: bool


class JobSupervisorAgent:
    def __init__(self, db: Session, candidate_id: int):
        self.db = db
        self.candidate_id = candidate_id
        self.log_cb = None

    async def _load_profile(self, state: AgentState) -> Dict[str, Any]:
        self.db.rollback()
        if self.log_cb:
            self.log_cb("Loading candidate profile (LangGraph node: LoadCandidateProfile)...", "info")

        # 1. Fetch active resume
        active_resume = self.db.query(CandidateResume).filter(
            CandidateResume.candidate_id == self.candidate_id,
            CandidateResume.is_active == True
        ).first()

        # Fallback to latest resume
        if not active_resume:
            active_resume = self.db.query(CandidateResume).filter(
                CandidateResume.candidate_id == self.candidate_id
            ).order_by(CandidateResume.uploaded_at.desc()).first()

        if not active_resume:
            if self.log_cb:
                self.log_cb("No resume uploaded yet.", "error")
            return {"skip_processing": True}

        # 2. Fetch profile from CandidateProfile
        profile_obj = self.db.query(CandidateProfile).filter(
            CandidateProfile.candidate_id == self.candidate_id,
            CandidateProfile.resume_id == active_resume.id
        ).first()

        # Fallback to latest CandidateProfile
        if not profile_obj:
            profile_obj = self.db.query(CandidateProfile).filter(
                CandidateProfile.candidate_id == self.candidate_id
            ).order_by(CandidateProfile.created_at.desc()).first()

        # If profile doesn't exist, trigger Resume Intelligence Agent sync run
        if not profile_obj:
            if self.log_cb:
                self.log_cb("First-time profile setup. Building candidate intelligence...", "info")
            from app.agents.resume_intelligence_agent import ResumeIntelligenceAgent as RIA
            ria = RIA(self.db, self.candidate_id)
            await ria.execute_pipeline()
            
            profile_obj = self.db.query(CandidateProfile).filter(
                CandidateProfile.candidate_id == self.candidate_id
            ).order_by(CandidateProfile.created_at.desc()).first()

        profile_data = {}
        if profile_obj and profile_obj.parsed_metadata:
            profile_data = safe_loads(profile_obj.parsed_metadata)

        if self.log_cb:
            self.log_cb(f"Candidate Profile loaded successfully: {profile_data.get('current_role', 'Professional')}.", "success")

        return {
            "profile": profile_data,
            "resume_id": profile_obj.resume_id if profile_obj else active_resume.id,
            "resume_version": profile_obj.resume_hash if profile_obj else "v1"
        }

    async def _load_embedding(self, state: AgentState) -> Dict[str, Any]:
        if state.get("skip_processing"):
            return {}
        if self.log_cb:
            self.log_cb("Retrieving profile embedding (LangGraph node: LoadCandidateEmbedding)...", "info")

        resume_id = state["resume_id"]
        # Fetch embedding vector from CandidateEmbedding table
        emb_obj = self.db.query(CandidateEmbedding).filter(
            CandidateEmbedding.candidate_id == self.candidate_id,
            CandidateEmbedding.resume_id == resume_id
        ).first()

        # If missing, regenerate embedding
        if not emb_obj:
            from app.agents.resume_intelligence_agent import ResumeIntelligenceAgent as RIA
            ria = RIA(self.db, self.candidate_id)
            await ria.execute_pipeline()
            
            emb_obj = self.db.query(CandidateEmbedding).filter(
                CandidateEmbedding.candidate_id == self.candidate_id,
                CandidateEmbedding.resume_id == resume_id
            ).first()

        vector = []
        if emb_obj and emb_obj.embedding_vector:
            vector = safe_loads(emb_obj.embedding_vector, [])
        else:
            vector = [0.0] * 768

        return {"candidate_embedding": vector}

    def _generate_roles(self, state: AgentState) -> Dict[str, Any]:
        if state.get("skip_processing"):
            return {}
            
        profile_obj = self.db.query(CandidateProfile).filter(
            CandidateProfile.candidate_id == self.candidate_id,
            CandidateProfile.resume_id == state["resume_id"]
        ).first()
        
        roles = []
        if profile_obj and profile_obj.generated_roles:
            roles = safe_loads(profile_obj.generated_roles, [])
            
        if not roles:
            roles = [state["profile"].get("current_role", "Software Engineer")]
            
        return {"generated_roles": roles}

    def _generate_search_strategy(self, state: AgentState) -> Dict[str, Any]:
        if state.get("skip_processing"):
            return {}
            
        profile_obj = self.db.query(CandidateProfile).filter(
            CandidateProfile.candidate_id == self.candidate_id,
            CandidateProfile.resume_id == state["resume_id"]
        ).first()
        
        strategy = {}
        if profile_obj and profile_obj.search_strategy:
            strategy = safe_loads(profile_obj.search_strategy)
            
        if not strategy:
            strategy = {
                "primary_roles": state["generated_roles"][:5],
                "secondary_roles": state["generated_roles"][5:15],
                "locations": [state["profile"].get("location", "India")],
                "experience_range": "0-5 Years",
                "keywords": (state["profile"].get("skills") or [])[:5]
            }
            
        return {"search_strategy": strategy}

    async def _fetch_cached_jobs(self, state: AgentState) -> Dict[str, Any]:
        if self.log_cb:
            self.log_cb("Checking search cache (LangGraph node: FetchCachedJobs)...", "info")
            
        cached = await job_cache.get(self.candidate_id, "agent_run_result")
        if cached and isinstance(cached, dict) and "jobs" in cached:
            if self.log_cb:
                self.log_cb(f"Cache hit: Loaded {len(cached['jobs'])} jobs instantly.", "success")
            return {"jobs": cached["jobs"], "cached_found": True}
            
        return {"jobs": [], "cached_found": False}

    async def _vector_search(self, state: AgentState) -> Dict[str, Any]:
        if state.get("cached_found"):
            return {}
            
        if self.log_cb:
            self.log_cb("Searching candidate jobs pool via Qdrant (LangGraph node: VectorSearch)...", "info")
            
        vector = state["candidate_embedding"]
        limit = 100
        job_ids = []
        
        if vector_store.enabled:
            try:
                job_ids = await vector_store.search_jobs_by_vector(vector, limit)
            except Exception as e:
                logger.error(f"Vector search failed: {e}")

        # Fetch actual jobs from JobPool database table
        jobs_list = []
        from app.models.pool_models import JobPool
        
        if job_ids:
            pool_jobs = self.db.query(JobPool).filter(JobPool.id.in_(job_ids)).all()
            job_map = {j.id: j for j in pool_jobs}
            jobs_list = [job_map[jid] for jid in job_ids if jid in job_map]

        # Fallback keyword DB search if Qdrant is offline/empty
        if not jobs_list:
            if self.log_cb:
                self.log_cb("Vector search empty. Running fallback database keyword search...", "info")
            strategy = state["search_strategy"]
            roles = strategy.get("primary_roles", [])[:3]
            keywords = strategy.get("keywords", [])[:3]
            
            filters = []
            for r in roles:
                filters.append(JobPool.title.ilike(f"%{r}%"))
            for k in keywords:
                filters.append(JobPool.description.ilike(f"%{k}%"))
                
            if filters:
                from sqlalchemy import or_
                jobs_list = self.db.query(JobPool).filter(or_(*filters)).order_by(JobPool.created_at.desc()).limit(limit).all()

        # Convert records to simple dictionaries
        raw_jobs = []
        for j in jobs_list:
            raw_jobs.append({
                "id": j.id,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "experience": j.experience,
                "skills": j.skills,
                "apply_url": j.apply_url,
                "posted_date": j.posted_date,
                "source": j.source,
                "description": j.description,
                "work_mode": j.work_mode,
                "domain": j.domain,
                "job_type": j.job_type,
                "career_level": j.career_level
            })
            
        if self.log_cb:
            self.log_cb(f"Discovered {len(raw_jobs)} matches in jobs pool database.", "success")
            
        return {"jobs": raw_jobs}

    def _normalize_jobs(self, state: AgentState) -> Dict[str, Any]:
        if state.get("cached_found"):
            return {}
            
        jobs = state["jobs"]
        normalized = []
        seen = set()
        
        for j in jobs:
            company_norm = j.get("company", "").strip().lower()
            title_norm = j.get("title", "").strip().lower()
            key = (company_norm, title_norm)
            
            if key in seen:
                continue
            seen.add(key)
            
            normalized.append({
                "title": j.get("title", ""),
                "company": j.get("company", ""),
                "location": j.get("location", ""),
                "salary": "Not Specified",
                "description": j.get("description", ""),
                "source": j.get("source", "Google Search"),
                "url": j.get("apply_url", ""),
                "posted_date": j.get("posted_date", "Recently"),
                "experience_required": j.get("experience", "Not Specified"),
                "skills": j.get("skills", []),
                "work_mode": j.get("work_mode", "On-site"),
                "domain": j.get("domain", "Other"),
                "job_type": j.get("job_type", "Full-time"),
                "career_level": j.get("career_level", "Mid-level")
            })
            
        return {"jobs": normalized}

    def _job_filtering_agent(self, state: AgentState) -> Dict[str, Any]:
        if state.get("cached_found"):
            return {}
            
        if self.log_cb:
            self.log_cb("Filtering jobs against hard requirements (LangGraph node: JobFilteringAgent)...", "info")
            
        jobs = state["jobs"]
        profile = state["profile"]
        
        cand_exp = float(profile.get("experience_years") or 0.0)
        cand_domain = (profile.get("domain") or "").lower().strip()
        cand_location = (profile.get("location") or "").lower().strip()
        
        filtered = []
        
        def get_exp_years(exp_str: str) -> int:
            exp_str = exp_str.lower()
            if "fresher" in exp_str or "intern" in exp_str or "0-" in exp_str:
                return 0
            match = re.search(r'(\d+)\s*(?:-|to)?\s*(?:\d+)?\s*year', exp_str)
            if match:
                return int(match.group(1))
            match = re.search(r'(\d+)\s*\+', exp_str)
            if match:
                return int(match.group(1))
            return 0
            
        for j in jobs:
            # 1. Experience gap check (Reject if required > candidate + 5)
            req_exp = get_exp_years(j.get("experience_required", ""))
            if req_exp - cand_exp > 5.0:
                continue
                
            # 2. Industry/Domain mismatch check
            job_title = j.get("title", "").lower()
            job_desc = j.get("description", "").lower()
            
            is_swe_candidate = "software" in cand_domain or "developer" in cand_domain or "engineer" in cand_domain
            is_swe_job = any(kw in job_title or kw in job_desc for kw in ["software", "developer", "programmer", "coding", "fullstack", "backend", "frontend"])
            
            is_civil_candidate = "civil" in cand_domain or "construction" in cand_domain or "site engineer" in cand_domain
            is_civil_job = any(kw in job_title or kw in job_desc for kw in ["civil", "construction", "site engineer", "structural engineer", "quantity surveyor"])
            
            if is_swe_candidate and is_civil_job and not is_swe_job:
                continue
            if is_civil_candidate and is_swe_job and not is_civil_job:
                continue
                
            # 3. Location exclusion checks
            filtered.append(j)
            
        if self.log_cb:
            self.log_cb(f"Hard filters complete. Bypassed {len(jobs) - len(filtered)} unqualified positions.", "success")
            
        return {"jobs": filtered}

    def _match_jobs(self, state: AgentState) -> Dict[str, Any]:
        if state.get("cached_found"):
            return {}
            
        if self.log_cb:
            self.log_cb("Scoring matches & computing embeddings similarity (LangGraph node: MatchJobs)...", "info")
            
        jobs = state["jobs"]
        profile = state["profile"]
        
        # Load skills graph from CandidateProfile
        profile_obj = self.db.query(CandidateProfile).filter(
            CandidateProfile.candidate_id == self.candidate_id,
            CandidateProfile.resume_id == state["resume_id"]
        ).first()
        
        skills_graph = {}
        if profile_obj and profile_obj.skills_graph:
            skills_graph = safe_loads(profile_obj.skills_graph)
            
        cand_skills = set(s.lower().strip() for s in skills_graph.get("primary_skills", profile.get("skills", [])))
        cand_tools = set(t.lower().strip() for t in skills_graph.get("tools", []))
        cand_domains = set(d.lower().strip() for d in skills_graph.get("domains", [profile.get("domain", "")]))
        cand_exp = float(profile.get("experience_years") or 0.0)
        cand_location = (profile.get("location") or "").lower().strip()
        
        # Load recommendation memory for behavioral boost
        rec_mem = self.db.query(RecommendationMemory).filter(RecommendationMemory.candidate_id == self.candidate_id).first()
        
        def safe_parse_list(val) -> list:
            if not val:
                return []
            if isinstance(val, list):
                return val
            if isinstance(val, str):
                try:
                    res = json.loads(val)
                    if isinstance(res, list):
                        return res
                except Exception:
                    pass
            return []

        pref_roles = [r.lower().strip() for r in safe_parse_list(rec_mem.preferred_roles)] if rec_mem else []
        pref_locs = [l.lower().strip() for l in safe_parse_list(rec_mem.preferred_locations)] if rec_mem else []
        pref_companies = [c.lower().strip() for c in safe_parse_list(rec_mem.preferred_companies)] if rec_mem else []
        ignored_roles = [r.lower().strip() for r in safe_parse_list(rec_mem.ignored_roles)] if rec_mem else []
        
        matched_jobs = []
        
        def get_source_score(source: str) -> float:
            s = source.lower()
            if "linkedin" in s:
                return 95.0
            if "greenhouse" in s:
                return 95.0
            if "lever" in s:
                return 95.0
            if "workday" in s:
                return 90.0
            if "career" in s:
                return 90.0
            if "naukri" in s:
                return 85.0
            if "indeed" in s:
                return 80.0
            if "telegram" in s:
                return 50.0
            return 70.0
            
        def parse_freshness_score(posted_date: str) -> float:
            if not posted_date:
                return 60.0
            pd = posted_date.lower().strip()
            if any(k in pd for k in ["today", "hour", "minute", "second", "just now", "recent"]):
                return 100.0
            if "yesterday" in pd or "1 day" in pd:
                return 95.0
            if "2 day" in pd or "3 day" in pd:
                return 90.0
            if "4 day" in pd or "5 day" in pd or "6 day" in pd or "7 day" in pd or "1 week" in pd:
                return 80.0
            if "week" in pd or "14 day" in pd:
                return 60.0
            if "month" in pd or "30 day" in pd:
                return 30.0
            return 10.0
            
        for j in jobs:
            title_lower = j["title"].lower().strip()
            if any(ir in title_lower for ir in ignored_roles):
                continue
                
            # 1. Skill Match
            job_skills = set(s.lower().strip() for s in j.get("skills", []))
            if job_skills:
                overlap = cand_skills.intersection(job_skills)
                skill_score = (len(overlap) / len(job_skills)) * 100.0
            else:
                desc_lower = j["description"].lower()
                overlap = [s for s in cand_skills if s in desc_lower]
                skill_score = min(100.0, len(overlap) * 20.0)
                
            # 2. Embedding Similarity (Using semantic fallback representing Qdrant relevance)
            emb_score = min(100.0, 50.0 + (skill_score * 0.5))
            
            # 3. Experience Match
            req_exp = 0
            match = re.search(r'(\d+)\s*(?:-|to)?\s*(?:\d+)?\s*year', j["experience_required"].lower())
            if match:
                req_exp = int(match.group(1))
            diff = cand_exp - req_exp
            if diff >= 0:
                exp_score = 100.0
            elif diff >= -2:
                exp_score = 70.0
            else:
                exp_score = 40.0
                
            # 4. Industry Match
            ind_score = 100.0
            job_domain = j.get("domain", "Other").lower()
            if cand_domains and not any(d in job_domain or job_domain in d for d in cand_domains):
                ind_score = 50.0
                
            # 5. Location Match
            loc_score = 100.0
            job_loc = j["location"].lower()
            if cand_location and cand_location not in job_loc:
                loc_score = 60.0
                
            # 6. Freshness score
            fresh_score = parse_freshness_score(j["posted_date"])
            
            # 7. Source reliability score
            src_score = get_source_score(j["source"])
            
            # Base match score computation (weighted sum out of 100)
            base_match_score = (
                (skill_score * 0.30) +
                (emb_score * 0.20) +
                (exp_score * 0.15) +
                (ind_score * 0.10) +
                (loc_score * 0.10) +
                (fresh_score * 0.10)
            )
            
            # 8. Behavioral score bonus
            behavior_bonus = 0.0
            if any(role in title_lower for role in pref_roles):
                behavior_bonus += 3.0
            if any(loc in job_loc for loc in pref_locs):
                behavior_bonus += 2.0
            company_lower = j["company"].lower().strip()
            if any(c in company_lower for c in pref_companies):
                behavior_bonus += 5.0
                
            # Final scoring (Match factor 95% + Source factor 5% + Behavior bonus)
            final_score = (base_match_score * 0.95) + (src_score * 0.05) + behavior_bonus
            final_score = min(100.0, round(final_score, 1))
            
            matched_jobs.append({
                "title": j["title"],
                "company": j["company"],
                "location": j["location"],
                "salary": j["salary"],
                "description": j["description"],
                "source": j["source"],
                "url": j["url"],
                "posted_date": j["posted_date"],
                "experience_required": j["experience_required"],
                "skills": list(job_skills),
                "match_score": final_score,
                "base_match_score": base_match_score,
                "skills_score": skill_score,
                "exp_score": exp_score,
                "ind_score": ind_score,
                "loc_score": loc_score,
                "fresh_score": fresh_score,
                "src_score": src_score,
                "missing_skills": list(cand_skills.difference(job_skills))[:5]
            })
            
        return {"jobs": matched_jobs}

    def _rank_jobs(self, state: AgentState) -> Dict[str, Any]:
        if state.get("cached_found"):
            return {}
            
        jobs = state["jobs"]
        # Rank by match score descending
        jobs.sort(key=lambda x: x["match_score"], reverse=True)
        return {"ranked_jobs": jobs}

    async def _store_results(self, state: AgentState) -> Dict[str, Any]:
        if state.get("cached_found"):
            return {"ranked_jobs": state["jobs"], "skill_gaps": [], "recommendations": []}
            
        ranked_jobs = state["ranked_jobs"]
        
        # Sync top matches to backend DB
        from app.mcp.servers import JobsServer
        from app.models.models import Job as JobModel, JobMatch, Candidate
        
        candidate = self.db.query(Candidate).filter(Candidate.id == self.candidate_id).first()
        user_id = candidate.user_id if candidate else self.candidate_id
        
        db_synced_jobs = []
        
        # Limit DB persist to top 20 matches for response time targets
        for rj in ranked_jobs[:20]:
            arguments = {
                "title": rj["title"],
                "description": rj["description"],
                "required_skills": ", ".join(rj["skills"]),
                "company_name": rj["company"],
                "location": rj["location"]
            }
            
            db_job = None
            try:
                db_job = JobsServer().store_job(user_id, arguments, self.db)
                if isinstance(db_job, dict) and "job_id" in db_job:
                    db_job = self.db.query(JobModel).filter(JobModel.id == db_job["job_id"]).first()
            except Exception as e:
                logger.error(f"Failed to persist match {rj['title']} to database: {e}")
                continue
                
            if db_job:
                rj["id"] = str(db_job.id)
                # Check duplicate match record
                match_rec = self.db.query(JobMatch).filter(
                    JobMatch.candidate_id == self.candidate_id,
                    JobMatch.job_id == db_job.id
                ).first()
                
                if not match_rec:
                    match_rec = JobMatch(
                        candidate_id=self.candidate_id,
                        job_id=db_job.id,
                        skill_match=rj["skills_score"],
                        experience_match=rj["exp_score"],
                        education_match=rj["ind_score"],
                        location_match=rj["loc_score"],
                        project_match=rj["fresh_score"],
                        match_score=rj["match_score"],
                        skills_gap=", ".join(rj["missing_skills"]),
                        apply_status="NEW",
                        resume_version=state["resume_version"],
                        interaction_status="VIEWED"
                    )
                    self.db.add(match_rec)
                else:
                    match_rec.match_score = rj["match_score"]
                    match_rec.skills_gap = ", ".join(rj["missing_skills"])
                    match_rec.resume_version = state["resume_version"]
                self.db.commit()
                db_synced_jobs.append(rj)

        # Cache top jobs in Redis for 30 minutes
        cache_payload = {
            "jobs": db_synced_jobs,
            "skill_gaps": [],
            "recommendations": []
        }
        
        await job_cache.set(self.candidate_id, "agent_run_result", cache_payload, ttl=1800)
        
        if self.log_cb:
            self.log_cb(f"Job Discovery complete. Persisted and ranked {len(db_synced_jobs)} matching jobs.", "success")
            
        return {
            "ranked_jobs": db_synced_jobs,
            "skill_gaps": [],
            "recommendations": []
        }

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("load_profile", self._load_profile)
        workflow.add_node("load_embedding", self._load_embedding)
        workflow.add_node("generate_roles", self._generate_roles)
        workflow.add_node("generate_search_strategy", self._generate_search_strategy)
        workflow.add_node("fetch_cached_jobs", self._fetch_cached_jobs)
        workflow.add_node("vector_search", self._vector_search)
        workflow.add_node("normalize_jobs", self._normalize_jobs)
        workflow.add_node("job_filtering_agent", self._job_filtering_agent)
        workflow.add_node("match_jobs", self._match_jobs)
        workflow.add_node("rank_jobs", self._rank_jobs)
        workflow.add_node("store_results", self._store_results)
        
        # Set entry
        workflow.set_entry_point("load_profile")
        
        # Sequential edges
        workflow.add_edge("load_profile", "load_embedding")
        workflow.add_edge("load_embedding", "generate_roles")
        workflow.add_edge("generate_roles", "generate_search_strategy")
        workflow.add_edge("generate_search_strategy", "fetch_cached_jobs")
        workflow.add_edge("fetch_cached_jobs", "vector_search")
        workflow.add_edge("vector_search", "normalize_jobs")
        workflow.add_edge("normalize_jobs", "job_filtering_agent")
        workflow.add_edge("job_filtering_agent", "match_jobs")
        workflow.add_edge("match_jobs", "rank_jobs")
        workflow.add_edge("rank_jobs", "store_results")
        workflow.add_edge("store_results", END)
        
        return workflow.compile()

    async def execute_run_flow(self, run_id: int, log_cb) -> dict:
        self.log_cb = log_cb
        
        initial_state = AgentState(
            run_id=run_id,
            candidate_id=self.candidate_id,
            profile={},
            resume_id=0,
            resume_version="v1",
            candidate_embedding=[],
            generated_roles=[],
            search_strategy={},
            jobs=[],
            ranked_jobs=[],
            cached_found=False
        )
        
        app = self._build_graph()
        final_state = await app.ainvoke(initial_state)
        
        # Make sure return dict is compatible with manager.py
        jobs_res = final_state.get("ranked_jobs", [])
        if not jobs_res and final_state.get("cached_found"):
            # Load cached jobs
            cached = await job_cache.get(self.candidate_id, "agent_run_result")
            if cached:
                jobs_res = cached.get("jobs", [])
                
        return {
            "jobs": jobs_res,
            "skill_gaps": [],
            "recommendations": [],
            "pipeline": {}
        }
