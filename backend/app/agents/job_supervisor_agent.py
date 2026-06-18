"""
Job Supervisor Agent — central orchestrator for job discovery, matching, gap analysis, and recommendations.
"""
import logging
from sqlalchemy.orm import Session
from app.agents.discovery_agent import DiscoveryAgent
from app.agents.matching_agent import MatchingAgent
from app.core.events import publish_event_sync
from app.models.models import Candidate

logger = logging.getLogger("app.agents.job_supervisor")


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
        log_cb(f"Loaded resume profile containing {len(profile.skills)} skills and {profile.experience_years} years of experience.", "success")

        # 2. Plan Queries
        from app.agents.planning import PlanningAgent
        planning_agent = PlanningAgent(profile)
        queries = planning_agent.generate_strategy()
        log_cb(f"Generated {len(queries)} job query variations based on target goals.", "success")

        # 3. Discovery Agent (search + modular connectors + deduplicate)
        discovery_agent = DiscoveryAgent()
        query = queries[0] if queries else "Developer"
        discovered_jobs = await discovery_agent.discover_jobs(
            user_id=user_id,
            query=query,
            skills=profile.skills,
            db=self.db,
            log_cb=log_cb
        )
        self.db.rollback()  # Release connection during consistency and matching checks

        # 4. Matching & Ranking Agent
        log_cb("Matching discovered jobs against candidate dimensions...", "info")
        matching_agent = MatchingAgent()
        ranked_jobs = []
        
        # We query stored jobs from DB to score them
        from app.models.models import Job as JobModel
        for job in discovered_jobs:
            db_job = self.db.query(JobModel).filter(
                JobModel.title == job["title"],
                JobModel.department == job["company"]
            ).first()
            if db_job:
                score = matching_agent.score_job(self.candidate_id, db_job.id, self.db)
                # Form match item for manager flow compatibility
                ranked_jobs.append({
                    "id": str(db_job.id),
                    "title": db_job.title,
                    "company": db_job.department,
                    "location": db_job.location,
                    "experience": db_job.experience_level,
                    "skills": [s.strip() for s in db_job.required_skills.split(",") if s.strip()],
                    "apply_url": job.get("apply_url", ""),
                    "description": db_job.description,
                    "match_score": score,
                    "missing_skills": [s.strip() for s in (db_job.required_skills.split(",") if db_job.required_skills else [])],
                    "reasoning": f"Overall match score is {score}%.",
                    "source": job.get("source", "Portal")
                })
                
        log_cb(f"Completed match scoring for {len(ranked_jobs)} positions.", "success")

        # 5. Pipeline Status
        from app.agents.status_agent import StatusAgent
        status_agent = StatusAgent(self.db)
        pipeline_info = status_agent.get_pipeline_status(self.candidate_id)

        # Publish final flow completion event to decoupled Event Bus
        publish_event_sync("agent_run_completed", {
            "run_id": run_id,
            "candidate_id": self.candidate_id,
            "jobs_count": len(ranked_jobs)
        })

        return {
            "jobs": ranked_jobs,
            "skill_gaps": [],  # Handled directly inside MatchingAgent via Skill Lab path creation
            "recommendations": [],
            "pipeline": pipeline_info
        }
