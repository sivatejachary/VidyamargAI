"""
Job Supervisor Agent — central orchestrator for job discovery, matching, gap analysis, and recommendations.
"""
import logging
from collections import Counter
from typing import List, Set
from sqlalchemy.orm import Session
from app.agents.discovery_agent import DiscoveryAgent
from app.agents.matching_agent import MatchingAgent
from app.core.events import publish_event_sync
from app.models.models import Candidate

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


class JobSupervisorAgent:
    """
    Coordinates Job Discovery, Matching, Verification, and Application sub-agents.
    Acts as the entry point for the job-agent background workspace flow.
    """
    def __init__(self, db: Session, candidate_id: int):
        self.db = db
        self.candidate_id = candidate_id

    async def execute_run_flow(self, run_id: int, log_cb) -> dict:
        log_cb("Initializing job intelligence workflow...", "info")

        # Load user ID for candidate
        candidate = self.db.query(Candidate).filter(Candidate.id == self.candidate_id).first()
        user_id = candidate.user_id if candidate else self.candidate_id

        # 1. Load Profile
        from app.agents.resume_intelligence import ResumeIntelligenceAgent
        resume_agent = ResumeIntelligenceAgent(self.db, self.candidate_id)
        profile = resume_agent.extract_profile()
        self.db.rollback()  # Release connection to pool during network scans
        log_cb(f"Loaded resume profile: {len(profile.skills)} skills, {profile.experience_years} yrs experience.", "success")

        # Candidate skill list for intersection computation
        candidate_skills = [s.strip() for s in profile.skills if s.strip()]

        # 2. Generate Queries via Candidate Query Generator Service
        from app.services.job_connectors.candidate_query_generator import generate_queries
        queries = generate_queries(profile.domain, profile.preferred_roles)
        log_cb(f"Generated {len(queries)} job query variations based on domain '{profile.domain}' and roles.", "success")

        # 3. Discovery Agent (tiered: Tier1 APIs → Google → Playwright)
        discovery_agent = DiscoveryAgent()
        query = queries[0] if queries else "Developer"
        discovered_jobs = await discovery_agent.discover_jobs(
            user_id=user_id,
            query=query,
            skills=profile.skills,
            db=self.db,
            log_cb=log_cb
        )
        self.db.rollback()  # Release connection during matching

        # 4. Matching & Ranking with correct skill analysis
        log_cb("Matching discovered jobs against candidate profile...", "info")
        matching_agent = MatchingAgent()
        ranked_jobs = []
        all_missing_skills: List[str] = []

        from app.models.models import Job as JobModel
        from app.services.job_connectors.base import is_indian_job
        for job in discovered_jobs:
            db_job = self.db.query(JobModel).filter(
                JobModel.title == job["title"],
                JobModel.department == job["company"]
            ).first()
            if db_job:
                # Reject non-India locations
                if not is_indian_job(db_job.location or job.get("location", ""), db_job.description or job.get("description", "")):
                    logger.info(f"Supervisor Agent: Skipping non-India job: {db_job.title} at {db_job.location}")
                    continue

                score = matching_agent.score_job(self.candidate_id, db_job.id, self.db)
                # Reject matches below 60%
                if score < 60.0:
                    logger.info(f"Supervisor Agent: Skipping job with score {score} < 60%: {db_job.title}")
                    continue

                # ── FIX: Compute real matched/missing skills ──────────────────
                job_skills = [s.strip() for s in (db_job.required_skills or "").split(",") if s.strip()]
                matched_skills, missing_skills = _compute_skill_sets(candidate_skills, job_skills)
                all_missing_skills.extend(missing_skills)
                # ─────────────────────────────────────────────────────────────

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
                    "matched_skills": matched_skills,     # ← FIXED: real intersection
                    "missing_skills": missing_skills,     # ← FIXED: only truly missing
                    "reasoning": (
                        f"Matched {len(matched_skills)}/{len(job_skills)} required skills. "
                        f"Overall score: {score}%."
                    ),
                    "source": job.get("source", "Portal")
                })

        # Sort ranked jobs by match score descending
        ranked_jobs.sort(key=lambda j: j["match_score"], reverse=True)
        log_cb(f"Completed match scoring for {len(ranked_jobs)} positions.", "success")

        # 5. Aggregate real skill gaps across all discovered jobs
        skill_freq = Counter(all_missing_skills)
        skill_gaps = [
            {"skill": skill, "job_count": count, "priority": "high" if count >= 3 else "medium"}
            for skill, count in skill_freq.most_common(10)
            if count >= 1
        ]

        # 6. Learning-based recommendations from skill gaps
        recommendations = []
        for gap in skill_gaps[:5]:
            recommendations.append({
                "skill": gap["skill"],
                "reason": f"Required in {gap['job_count']} matched job(s). Learning this unlocks more opportunities.",
                "priority": gap["priority"]
            })

        # 7. Pipeline Status
        from app.agents.status_agent import StatusAgent
        status_agent = StatusAgent(self.db)
        pipeline_info = status_agent.get_pipeline_status(self.candidate_id)

        publish_event_sync("agent_run_completed", {
            "run_id": run_id,
            "candidate_id": self.candidate_id,
            "jobs_count": len(ranked_jobs)
        })

        return {
            "jobs": ranked_jobs,
            "skill_gaps": skill_gaps,           # ← REAL: aggregated from all jobs
            "recommendations": recommendations,  # ← REAL: skill-gap driven
            "pipeline": pipeline_info
        }
