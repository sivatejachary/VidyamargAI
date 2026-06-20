"""
Job Supervisor Agent — central orchestrator for job discovery, matching, gap analysis, and recommendations using LangGraph.
"""
import logging
import concurrent.futures
import json
import re
import os
import string
import urllib.parse
from collections import Counter
from typing import List, Set, Dict, Any, TypedDict
from sqlalchemy.orm import Session
from app.agents.matching_agent import MatchingAgent
from app.core.events import publish_event_sync
from app.models.models import Candidate, JobAgentRun
from app.services.orchestrator import call_gemini, call_nvidia

# LangGraph imports
from langgraph.graph import StateGraph, END

logger = logging.getLogger("app.agents.job_supervisor")


def _normalize_skill(skill: str) -> str:
    """Lowercase, strip punctuation for fuzzy comparison."""
    return skill.strip().lower().replace(".", "").replace("-", "").replace(" ", "")


def _compute_skill_sets(candidate_skills: List[str], job_skills: List[str]):
    """
    Correctly computes matched and missing skills using normalized comparison.
    Handles common synonyms: node/nodejs, react/reactjs, ml/machine learning, etc.
    """
    SYNONYMS = {
        "nodejs": "node", "node.js": "node", "reactjs": "react", "react.js": "react",
        "ml": "machinelearning", "machinelearning": "ml", "ai": "artificialintelligence",
        "python3": "python", "typescript": "ts", "javascript": "js",
        "postgresql": "postgres", "k8s": "kubernetes",
    }

    def resolve(s: str) -> str:
        n = _normalize_skill(s)
        return SYNONYMS.get(n, n)

    candidate_resolved: Set[str] = {resolve(s) for s in candidate_skills if s.strip()}

    matched, missing = [], []
    for js in job_skills:
        if not js.strip():
            continue
        if resolve(js) in candidate_resolved:
            matched.append(js.strip())
        else:
            missing.append(js.strip())

    return matched, missing


class AgentState(TypedDict):
    run_id: int
    candidate_id: int
    max_job_age_days: int
    profile: dict
    candidate_skills: list
    candidate_education: str
    queries: list
    portal_jobs: list
    telegram_jobs: list
    ats_jobs: list
    jobs: list
    ranked_jobs: list
    skill_gaps: list
    recommendations: list
    pipeline_info: dict
    query_provider: str
    fallback_used: bool
    # Counts for metrics
    jobs_discovered: int
    jobs_after_dedup: int
    jobs_after_validation: int
    jobs_after_freshness_filter: int
    jobs_after_ranking: int
    stale_jobs_removed: int


class JobSupervisorAgent:
    """
    Coordinates Job Discovery, Matching, Verification, and Application sub-agents using LangGraph.
    Acts as the entry point for the job-agent background workspace flow.
    """
    def __init__(self, db: Session, candidate_id: int):
        self.db = db
        self.candidate_id = candidate_id
        self.log_cb = None

    def _load_profile(self, state: AgentState) -> Dict[str, Any]:
        self.db.rollback()  # Ensure database session has clean transaction state
        if self.log_cb:
            self.log_cb("Initializing job intelligence workflow (LangGraph node: load_profile)...", "info")
            
        # Retrieve max_job_age_days from JobAgentRun stats if available
        run_rec = self.db.query(JobAgentRun).filter(JobAgentRun.id == state["run_id"]).first()
        max_job_age_days = 2
        if run_rec and run_rec.stats and isinstance(run_rec.stats, dict):
            max_job_age_days = run_rec.stats.get("max_job_age_days", 2)

        from app.agents.resume_intelligence import ResumeIntelligenceAgent
        resume_agent = ResumeIntelligenceAgent(self.db, self.candidate_id)
        profile = resume_agent.extract_profile()
        self.db.rollback()  # Release connection to pool during network scans
        
        skills = [s.strip() for s in profile.skills if s.strip()]
        profile_dict = {
            "domain": profile.domain,
            "skills": profile.skills,
            "preferred_roles": profile.preferred_roles,
            "experience_years": profile.experience_years
        }
        
        if self.log_cb:
            self.log_cb(f"Loaded resume profile: {len(skills)} skills, {profile.experience_years} yrs experience. Age Limit: {max_job_age_days} Days.", "success")
        
        return {
            "profile": profile_dict,
            "candidate_skills": skills,
            "candidate_education": profile.education or "",
            "max_job_age_days": max_job_age_days
        }

    def _extract_candidate_data(self, state: AgentState) -> Dict[str, Any]:
        self.db.rollback()  # Ensure database session has clean transaction state
        if self.log_cb:
            self.log_cb("Structuring candidate data (LangGraph node: extract_candidate_data)...", "info")
            
        profile = state["profile"]
        skills = state["candidate_skills"]
        education = state.get("candidate_education", "")
        domain = profile.get("domain", "")
        experience_years = profile.get("experience_years", 0.0)
        
        candidate = self.db.query(Candidate).filter(Candidate.id == self.candidate_id).first()
        address = candidate.address if candidate else "Remote"
        
        structured_profile = {
            "skills": skills,
            "experience_years": experience_years,
            "education": education,
            "domain": domain,
            "location": address or "Remote",
            "preferences": candidate.summary if candidate else ""
        }
        
        return {"profile": structured_profile}

    def _generate_queries(self, state: AgentState) -> Dict[str, Any]:
        if self.log_cb:
            self.log_cb("Generating search queries dynamically (LangGraph node: generate_queries)...", "info")
            
        profile = state["profile"]
        prompt = f"""
Generate a JSON list of 4-6 targeted, real-world job search queries for a candidate with the following profile:
- Skills: {profile.get("skills")}
- Experience: {profile.get("experience_years")} years
- Education: {profile.get("education")}
- Domain: {profile.get("domain")}
- Location: {profile.get("location")}
- Summary: {profile.get("preferences")}

The queries must be search engine-friendly, and should combine the skills, experience level, and preferred location (e.g. "Python FastAPI Developer Remote", "React Frontend Engineer Remote").
Do NOT use templates like "Job for [Skill]". Use real job titles.
Do NOT include any hardcoded company names.
Return ONLY a JSON object in this format:
{{
    "queries": [
        "query 1",
        "query 2",
        ...
    ]
}}
"""
        queries = []
        query_provider = "local"
        fallback_used = False

        def call_with_timeout(func, *args, timeout=10, **kwargs):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=timeout)
                except Exception as e:
                    logger.warning(f"Query generation provider failed: {e}")
                    raise e

        def safe_parse_json(text: str) -> dict:
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

        # 1. Primary: Gemini
        try:
            if self.log_cb:
                self.log_cb("Query generation: Trying Gemini...", "info")
            res_text = call_with_timeout(call_gemini, prompt, json_mode=True, timeout=10)
            if res_text:
                data = safe_parse_json(res_text)
                if "queries" in data and isinstance(data["queries"], list):
                    queries = [q.strip() for q in data["queries"] if q.strip()]
                    query_provider = "gemini"
        except Exception as e:
            logger.warning(f"Gemini query generation failed: {e}. Falling back to NVIDIA NIM.")
            if self.log_cb:
                self.log_cb("Gemini query generation failed. Falling back to NVIDIA NIM.", "warning")

        # 2. Secondary Fallback: NVIDIA NIM
        if not queries:
            fallback_used = True
            try:
                if self.log_cb:
                    self.log_cb("Query generation: Trying NVIDIA NIM...", "info")
                res_text = call_with_timeout(call_nvidia, prompt, json_mode=True, timeout=10)
                if res_text:
                    data = safe_parse_json(res_text)
                    if "queries" in data and isinstance(data["queries"], list):
                        queries = [q.strip() for q in data["queries"] if q.strip()]
                        query_provider = "nvidia"
            except Exception as e:
                logger.warning(f"NVIDIA NIM query generation failed: {e}. Falling back to Local Python.")
                if self.log_cb:
                    self.log_cb("NVIDIA NIM query generation failed. Falling back to Local Python.", "warning")

        # 3. Tertiary Fallback: Local Python Generator
        if not queries:
            fallback_used = True
            query_provider = "local"
            if self.log_cb:
                self.log_cb("Query generation: Running Local Python Fallback Generator...", "info")
                
            skills = profile.get("skills", [])
            loc = profile.get("location", "India")
            top_skills = skills[:3] if skills else ["Software"]
            for skill in top_skills:
                queries.append(f"{skill} Developer {loc}")
                queries.append(f"{skill} Engineer {loc}")
                queries.append(f"{skill} jobs {loc}")
            if profile.get("domain") and profile.get("domain") != "Other":
                queries.append(f"{profile.get('domain')} Engineer {loc}")

        if self.log_cb:
            self.log_cb(f"Query generation complete. Provider: {query_provider.upper()}. Generated {len(queries)} queries.", "success")
            
        return {
            "queries": queries,
            "query_provider": query_provider,
            "fallback_used": fallback_used
        }

    def _validate_queries(self, state: AgentState) -> Dict[str, Any]:
        if self.log_cb:
            self.log_cb("Validating generated queries (LangGraph node: validate_queries)...", "info")
            
        raw_queries = state["queries"]
        seen = set()
        valid = []
        
        for q in raw_queries:
            cleaned = q.strip()
            if not cleaned or len(cleaned) < 3:
                continue
            lower = cleaned.lower()
            if lower not in seen:
                seen.add(lower)
                valid.append(cleaned)
                
        # Limit total query count
        valid = valid[:6]
        
        if self.log_cb:
            self.log_cb(f"Sanitized queries list: {valid}", "success")
            
        return {"queries": valid}

    def _discover_portals(self, state: AgentState) -> Dict[str, Any]:
        queries = state["queries"]
        skills = state["candidate_skills"]
        query_list = queries if queries else ["Developer"]
        
        if self.log_cb:
            self.log_cb(f"Starting portal job discovery scans for queries: {query_list} (LangGraph node: discover_portals)...", "info")
            
        from app.agents.search import SearchAgent
        search_agent = SearchAgent(query_list, skills, state["profile"].get("experience_years", 1.0))
        
        try:
            portal_jobs = search_agent.execute_search(
                lambda m, s="info": self.log_cb(f"[Portal] {m}", s) if self.log_cb else None
            )
        except Exception as e:
            logger.error(f"Portal search crawler failed: {e}")
            portal_jobs = []
            
        return {"portal_jobs": portal_jobs}

    async def _discover_telegram(self, state: AgentState) -> Dict[str, Any]:
        self.db.rollback()  # Ensure database session has clean transaction state
        if self.log_cb:
            self.log_cb("Starting Telegram channel job discovery scan (LangGraph node: discover_telegram)...", "info")
            
        from app.agents.telegram import TelegramCommunityAgent
        telegram_agent = TelegramCommunityAgent(self.db)
        
        try:
            tg_jobs = await telegram_agent.async_collect_jobs(
                lambda m, s="info": self.log_cb(f"[Telegram] {m}", s) if self.log_cb else None
            )
        except Exception as e:
            logger.error(f"Telegram collector failed: {e}")
            tg_jobs = []
            
        return {"telegram_jobs": tg_jobs}

    def _discover_ats_sources(self, state: AgentState) -> Dict[str, Any]:
        queries = state["queries"]
        if self.log_cb:
            self.log_cb("Starting ATS job discovery scan (LangGraph node: discover_ats_sources)...", "info")
            
        from app.services.job_connectors import ats_sources
        try:
            ats_jobs = ats_sources.fetch(queries)
        except Exception as e:
            logger.error(f"ATS search crawler failed: {e}")
            ats_jobs = []
            
        return {"ats_jobs": ats_jobs}

    def _merge_jobs(self, state: AgentState) -> Dict[str, Any]:
        portal_jobs = state["portal_jobs"] or []
        telegram_jobs = state["telegram_jobs"] or []
        ats_jobs = state.get("ats_jobs") or []
        
        raw_jobs = []
        for j in (portal_jobs + telegram_jobs + ats_jobs):
            if hasattr(j, "title"):
                raw_jobs.append({
                    "title": j.title,
                    "company": j.company,
                    "location": j.location,
                    "experience": j.experience,
                    "skills": j.skills,
                    "apply_url": j.apply_url,
                    "source": j.source,
                    "description": j.description,
                    "work_mode": j.work_mode
                })
            else:
                raw_jobs.append(j)
                
        if self.log_cb:
            self.log_cb(f"Aggregated {len(raw_jobs)} raw jobs from all sources. (LangGraph node: merge_jobs)", "info")
            
        return {
            "jobs": raw_jobs,
            "jobs_discovered": len(raw_jobs)
        }

    def _deduplicate_jobs(self, state: AgentState) -> Dict[str, Any]:
        if self.log_cb:
            self.log_cb("Starting job deduplication (LangGraph node: deduplicate_jobs)...", "info")
            
        raw_jobs = state["jobs"]
        seen = set()
        deduplicated = []
        duplicates_removed = 0
        
        def normalize(text: str) -> str:
            if not text:
                return ""
            t = text.lower().strip()
            return t.translate(str.maketrans("", "", string.punctuation))
            
        for j in raw_jobs:
            company = normalize(j.get("company", ""))
            title = normalize(j.get("title", ""))
            location = normalize(j.get("location", ""))
            key = (company, title, location)
            
            if key not in seen:
                seen.add(key)
                deduplicated.append(j)
            else:
                duplicates_removed += 1
                
        if self.log_cb:
            self.log_cb(f"Deduplicated jobs: {len(deduplicated)} remaining ({duplicates_removed} duplicates removed).", "success")
            
        info = state.get("pipeline_info", {}) or {}
        info["duplicates_removed"] = duplicates_removed
        
        return {
            "jobs": deduplicated,
            "jobs_after_dedup": len(deduplicated),
            "pipeline_info": info
        }

    def _validate_jobs(self, state: AgentState) -> Dict[str, Any]:
        if self.log_cb:
            self.log_cb("Validating job records and apply URLs (LangGraph node: validate_jobs)...", "info")
            
        def is_generic_homepage(url: str) -> bool:
            if not url:
                return True
            u = url.lower().strip().rstrip("/")
            generic_patterns = [
                "linkedin.com", "www.linkedin.com", "indeed.com", "in.indeed.com",
                "naukri.com", "foundit.in", "monsterindia.com", "internshala.com",
                "wellfound.com", "angel.co", "instahyre.com", "cutshort.io", "hirist.com"
            ]
            parsed = urllib.parse.urlparse(u)
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            path = parsed.path.strip("/")
            if not path:
                return True
            for gp in generic_patterns:
                if gp in u and len(path) < 5:
                    return True
            return False

        jobs = state["jobs"]
        validated = []
        invalid_jobs_removed = 0
        
        for j in jobs:
            apply_url = j.get("apply_url", "").strip()
            company = j.get("company", "").strip()
            title = j.get("title", "").strip()
            source = j.get("source", "").strip()
            
            if not apply_url or not company or not title or not source:
                invalid_jobs_removed += 1
                continue
                
            if is_generic_homepage(apply_url):
                invalid_jobs_removed += 1
                continue
                
            validated.append(j)
            
        if self.log_cb:
            self.log_cb(f"Validation complete: {len(validated)} jobs approved ({invalid_jobs_removed} invalid jobs removed).", "success")
            
        info = state.get("pipeline_info", {}) or {}
        info["invalid_jobs_removed"] = invalid_jobs_removed
        
        return {
            "jobs": validated,
            "jobs_after_validation": len(validated),
            "pipeline_info": info
        }

    def _freshness_filter(self, state: AgentState) -> Dict[str, Any]:
        if self.log_cb:
            self.log_cb("Filtering jobs by posting date freshness (LangGraph node: freshness_filter)...", "info")
            
        def parse_job_age_days(posted_date: str) -> float:
            if not posted_date:
                return 999.0
            pd = posted_date.lower().strip()
            if any(k in pd for k in ["today", "hour", "minute", "second", "just now", "recent"]):
                return 0.0
            if "yesterday" in pd:
                return 1.0
            if "day ago" in pd or "1 day ago" in pd:
                return 1.0
            match = re.search(r'(\d+)\s*day', pd)
            if match:
                return float(match.group(1))
            if "week" in pd:
                match = re.search(r'(\d+)\s*week', pd)
                return float(match.group(1)) * 7 if match else 7.0
            if "month" in pd:
                match = re.search(r'(\d+)\s*month', pd)
                return float(match.group(1)) * 30 if match else 30.0
            if "year" in pd:
                return 365.0
            try:
                from dateutil import parser
                from datetime import datetime
                dt = parser.parse(posted_date)
                diff = datetime.utcnow() - dt.replace(tzinfo=None)
                return float(diff.days)
            except Exception:
                pass
            return 999.0

        jobs = state["jobs"]
        max_age = state.get("max_job_age_days", 2)
        filtered = []
        stale_jobs_removed = 0
        
        for j in jobs:
            posted = j.get("posted_date", "")
            age = parse_job_age_days(posted)
            
            if age >= 990.0:
                j["date_verified"] = False
                j["job_age_days"] = None
                filtered.append(j)
            else:
                j["date_verified"] = True
                j["job_age_days"] = age
                if age <= max_age:
                    filtered.append(j)
                else:
                    stale_jobs_removed += 1
                    
        if self.log_cb:
            self.log_cb(f"Freshness filter complete: {len(filtered)} recent jobs remaining ({stale_jobs_removed} stale jobs removed).", "success")
            
        info = state.get("pipeline_info", {}) or {}
        info["stale_jobs_removed"] = stale_jobs_removed
        info["recent_jobs_remaining"] = len(filtered)
        
        return {
            "jobs": filtered,
            "jobs_after_freshness_filter": len(filtered),
            "stale_jobs_removed": stale_jobs_removed,
            "pipeline_info": info
        }

    def _match_and_rank(self, state: AgentState) -> Dict[str, Any]:
        self.db.rollback()  # Ensure database session has clean transaction state
        if self.log_cb:
            self.log_cb("Matching and ranking jobs against candidate profile (LangGraph node: match_and_rank)...", "info")
            
        # Load source reliability configuration
        config_path = r"c:\Users\jshiv\Downloads\shivateja\backend\app\config\source_reliability.json"
        reliability = {
            "linkedin": 10.0,
            "naukri": 10.0,
            "indeed": 10.0,
            "telegram": 7.0,
            "default": 5.0
        }
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    reliability.update(json.load(f))
            except Exception as e:
                logger.error(f"Error loading source reliability configuration: {e}")

        matching_agent = MatchingAgent()
        ranked_jobs = []
        candidate_skills = state["candidate_skills"]
        max_age = state.get("max_job_age_days", 2)
        
        from app.models.models import Job as JobModel, Candidate
        from app.services.job_connectors.base import is_indian_job
        
        candidate = self.db.query(Candidate).filter(Candidate.id == self.candidate_id).first()
        user_id = candidate.user_id if candidate else self.candidate_id

        # Persist jobs first and check match
        from app.mcp.servers import JobsServer
        for job in state["jobs"]:
            arguments = {
                "title": job["title"],
                "description": job["description"],
                "required_skills": ", ".join(job["skills"]) if isinstance(job["skills"], list) else str(job["skills"]),
                "company_name": job["company"],
                "location": job["location"]
            }
            
            # Reject non-India locations
            if not is_indian_job(job.get("location", ""), job.get("description", "")):
                logger.info(f"Supervisor Agent: Skipping non-India job: {job['title']} at {job['location']}")
                continue
                
            try:
                store_res = JobsServer().store_job(user_id, arguments, self.db)
                if isinstance(store_res, dict) and "job_id" in store_res:
                    db_job = self.db.query(JobModel).filter(JobModel.id == store_res["job_id"]).first()
                else:
                    db_job = store_res
                publish_event_sync("job_discovered", {"user_id": user_id, "job": job})
            except Exception as e:
                logger.error(f"Failed to persist discovered job: {e}")
                continue
                
            if db_job:
                score = matching_agent.score_job(self.candidate_id, db_job.id, self.db)
                if score < 60.0:
                    logger.info(f"Supervisor Agent: Skipping job with score {score} < 60%: {db_job.title}")
                    continue
                    
                job_skills = [s.strip() for s in (db_job.required_skills or "").split(",") if s.strip()]
                matched_skills, missing_skills = _compute_skill_sets(candidate_skills, job_skills)
                
                # Calculate freshness score dynamically: max(0, 1 - (age / max_age))
                date_verified = job.get("date_verified", False)
                age_days = job.get("job_age_days")
                if date_verified and age_days is not None:
                    # Prevent division by zero
                    div = max(1.0, float(max_age))
                    freshness_score = max(0.0, 1.0 - (float(age_days) / div))
                else:
                    freshness_score = 0.0
                    
                # Source reliability score
                src = job.get("source", "Portal").lower()
                source_reliability = reliability.get(src, reliability.get("default", 5.0))
                
                # Combined final score
                final_score = score + (freshness_score * 15.0) + source_reliability
                
                ranked_jobs.append({
                    "id": str(db_job.id),
                    "title": db_job.title,
                    "company": db_job.department,
                    "location": db_job.location,
                    "experience": db_job.experience_level,
                    "skills": job_skills,
                    "apply_url": job.get("apply_url", ""),
                    "description": db_job.description,
                    "match_score": score,
                    "final_score": final_score,
                    "date_verified": date_verified,
                    "job_age_days": age_days,
                    "matched_skills": matched_skills,
                    "missing_skills": missing_skills,
                    "reasoning": (
                      f"Matched {len(matched_skills)}/{len(job_skills)} required skills. "
                      f"Overall score: {score}%. Freshness: {freshness_score:.2f}."
                    ),
                    "source": job.get("source", "Portal"),
                    "work_mode": job.get("work_mode", "On-site")
                })
                
        # Sort ranked jobs using tuple: (1 if date_verified else 0, final_score) descending
        ranked_jobs.sort(key=lambda j: (1 if j["date_verified"] else 0, j["final_score"]), reverse=True)
        
        if self.log_cb:
            self.log_cb(f"Completed match scoring and ranking for {len(ranked_jobs)} positions.", "success")
            
        info = state.get("pipeline_info", {}) or {}
        info["ranked_jobs"] = len(ranked_jobs)
        
        return {
            "ranked_jobs": ranked_jobs,
            "jobs_after_ranking": len(ranked_jobs),
            "pipeline_info": info
        }

    def _compute_recommendations(self, state: AgentState) -> Dict[str, Any]:
        all_missing_skills = []
        for rj in state["ranked_jobs"]:
            all_missing_skills.extend(rj.get("missing_skills", []))
            
        skill_freq = Counter(all_missing_skills)
        skill_gaps = [
            {"skill": skill, "job_count": count, "priority": "high" if count >= 3 else "medium"}
            for skill, count in skill_freq.most_common(10)
            if count >= 1
        ]
        
        recommendations = []
        for gap in skill_gaps[:5]:
            recommendations.append({
                "skill": gap["skill"],
                "reason": f"Required in {gap['job_count']} matched job(s). Learning this unlocks more opportunities.",
                "priority": gap["priority"]
            })
            
        return {"skill_gaps": skill_gaps, "recommendations": recommendations}

    def _get_pipeline_status(self, state: AgentState) -> Dict[str, Any]:
        info = state.get("pipeline_info", {}) or {}
        
        pipeline_info = {
            "queries_generated": len(state.get("queries", [])),
            "portal_jobs_found": len(state.get("portal_jobs", [])),
            "telegram_jobs_found": len(state.get("telegram_jobs", [])),
            "ats_jobs_found": len(state.get("ats_jobs", [])),
            "duplicates_removed": info.get("duplicates_removed", 0),
            "invalid_jobs_removed": info.get("invalid_jobs_removed", 0),
            "stale_jobs_removed": info.get("stale_jobs_removed", 0),
            "recent_jobs_remaining": info.get("recent_jobs_remaining", 0),
            "jobs_discovered": state.get("jobs_discovered", 0),
            "jobs_after_dedup": state.get("jobs_after_dedup", 0),
            "jobs_after_validation": state.get("jobs_after_validation", 0),
            "jobs_after_freshness_filter": state.get("jobs_after_freshness_filter", 0),
            "jobs_after_ranking": state.get("jobs_after_ranking", 0),
            "ranked_jobs": len(state.get("ranked_jobs", [])),
            "recommended_jobs": len(state.get("ranked_jobs", [])),
            "query_provider": state.get("query_provider", "local"),
            "fallback_used": state.get("fallback_used", False)
        }
        
        publish_event_sync("agent_run_completed", {
            "run_id": state["run_id"],
            "candidate_id": self.candidate_id,
            "jobs_count": len(state["ranked_jobs"])
        })
        
        return {"pipeline_info": pipeline_info}

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("load_profile", self._load_profile)
        workflow.add_node("extract_candidate_data", self._extract_candidate_data)
        workflow.add_node("generate_queries", self._generate_queries)
        workflow.add_node("validate_queries", self._validate_queries)
        workflow.add_node("discover_portals", self._discover_portals)
        workflow.add_node("discover_telegram", self._discover_telegram)
        workflow.add_node("discover_ats_sources", self._discover_ats_sources)
        workflow.add_node("merge_jobs", self._merge_jobs)
        workflow.add_node("deduplicate_jobs", self._deduplicate_jobs)
        workflow.add_node("validate_jobs", self._validate_jobs)
        workflow.add_node("freshness_filter", self._freshness_filter)
        workflow.add_node("match_and_rank", self._match_and_rank)
        workflow.add_node("compute_recommendations", self._compute_recommendations)
        workflow.add_node("get_pipeline_status", self._get_pipeline_status)
        
        # Set entry point
        workflow.set_entry_point("load_profile")
        
        # Sequential edges
        workflow.add_edge("load_profile", "extract_candidate_data")
        workflow.add_edge("extract_candidate_data", "generate_queries")
        workflow.add_edge("generate_queries", "validate_queries")
        
        # Parallel branch (fan-out)
        workflow.add_edge("validate_queries", "discover_portals")
        workflow.add_edge("validate_queries", "discover_telegram")
        workflow.add_edge("validate_queries", "discover_ats_sources")
        
        # Parallel merge (fan-in)
        workflow.add_edge("discover_portals", "merge_jobs")
        workflow.add_edge("discover_telegram", "merge_jobs")
        workflow.add_edge("discover_ats_sources", "merge_jobs")
        
        # Final sequential flow
        workflow.add_edge("merge_jobs", "deduplicate_jobs")
        workflow.add_edge("deduplicate_jobs", "validate_jobs")
        workflow.add_edge("validate_jobs", "freshness_filter")
        workflow.add_edge("freshness_filter", "match_and_rank")
        workflow.add_edge("match_and_rank", "compute_recommendations")
        workflow.add_edge("compute_recommendations", "get_pipeline_status")
        workflow.add_edge("get_pipeline_status", END)
        
        return workflow.compile()

    async def execute_run_flow(self, run_id: int, log_cb) -> dict:
        self.log_cb = log_cb
        
        initial_state = AgentState(
            run_id=run_id,
            candidate_id=self.candidate_id,
            max_job_age_days=2,
            profile={},
            candidate_skills=[],
            candidate_education="",
            queries=[],
            portal_jobs=[],
            telegram_jobs=[],
            ats_jobs=[],
            jobs=[],
            ranked_jobs=[],
            skill_gaps=[],
            recommendations=[],
            pipeline_info={},
            query_provider="local",
            fallback_used=False,
            jobs_discovered=0,
            jobs_after_dedup=0,
            jobs_after_validation=0,
            jobs_after_freshness_filter=0,
            jobs_after_ranking=0,
            stale_jobs_removed=0
        )
        
        app = self._build_graph()
        final_state = await app.ainvoke(initial_state)
        
        return {
            "jobs": final_state["ranked_jobs"],
            "skill_gaps": final_state["skill_gaps"],
            "recommendations": final_state["recommendations"],
            "pipeline": final_state["pipeline_info"]
        }
