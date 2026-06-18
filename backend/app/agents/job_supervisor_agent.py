"""
Job Supervisor Agent — central orchestrator for job discovery, matching, gap analysis, and recommendations.
"""
import logging
from sqlalchemy.orm import Session
from app.agents.job_discovery_agent import JobDiscoveryAgent
from app.agents.job_match_agent import JobMatchAgent
from app.agents.status_agent import StatusAgent
from app.agents.company_research_agent import CompanyResearchAgent
from app.agents.salary_agent import SalaryAgent

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
        
        # 1. Load Profile
        from app.agents.resume_intelligence import ResumeIntelligenceAgent
        resume_agent = ResumeIntelligenceAgent(self.db, self.candidate_id)
        profile = resume_agent.extract_profile()
        self.db.rollback()  # Release connection to pool during planning and network scans
        log_cb(f"Loaded resume profile containing {len(profile.skills)} skills and {profile.experience_years} years of experience.", "success")

        # 2. Plan Queries
        from app.agents.planning import PlanningAgent
        planning_agent = PlanningAgent(profile)
        queries = planning_agent.generate_strategy()
        log_cb(f"Generated {len(queries)} job query variations based on target goals.", "success")

        # 3. Discovery Agent (search + telegram + deduplicate)
        discovery_agent = JobDiscoveryAgent(self.db, queries, profile.skills, profile.experience_years)
        verified_jobs = await discovery_agent.discover(log_cb)
        self.db.rollback()  # Release connection to pool during consistency and matching checks

        # 4. Consistency Checks
        log_cb("Performing job consistency verification checks...", "info")
        from app.agents.consistency import JobConsistencyAgent
        consistency_agent = JobConsistencyAgent(self.db)
        final_verified_jobs = []
        for j in verified_jobs:
            score, status = consistency_agent.verify_job_consistency(j)
            j.verification_score = score
            j.verification_status = status
            if status != "Rejected":
                final_verified_jobs.append(j)
        log_cb(f"Approved {len(final_verified_jobs)} jobs after consistency verification.", "success")

        # 5. Matching & Ranking Agent
        match_agent = JobMatchAgent(profile)
        ranked_jobs = match_agent.match_and_rank(final_verified_jobs, log_cb)

        # 6. Skill Gap Analysis
        from app.agents.skill_gap import SkillGapAgent
        log_cb("Starting missing skill analysis for top opportunities...", "info")
        skill_gap_agent = SkillGapAgent(ranked_jobs)
        skill_gaps = skill_gap_agent.analyze_gaps()
        if skill_gaps:
            log_cb(f"Skill Gap Agent detected {len(skill_gaps)} key missing skills.", "warning")

        # 7. Recommendations (courses, certifications)
        from app.agents.recommendation import RecommendationAgent
        rec_agent = RecommendationAgent(skill_gaps)
        recommendations = rec_agent.generate_recommendations()
        log_cb("Successfully created learning recommendations.", "success")

        # 8. Pipeline Status
        self.db.rollback()  # Refresh connection before status query
        status_agent = StatusAgent(self.db)
        pipeline_info = status_agent.get_pipeline_status(self.candidate_id)
        log_cb(f"Status Agent tracked {pipeline_info['total_applications']} current applications in pipeline.", "info")

        return {
            "jobs": ranked_jobs,
            "skill_gaps": skill_gaps,
            "recommendations": recommendations,
            "pipeline": pipeline_info
        }
