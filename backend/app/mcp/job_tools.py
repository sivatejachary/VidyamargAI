"""
Job MCP Server — tools for AI to access job search data.
"""
import logging
from sqlalchemy.orm import Session
from app.mcp.base import BaseMCPServer
from app.services.mcp_audit import audit_tool_call

logger = logging.getLogger("app.mcp.job")


class JobMCPServer(BaseMCPServer):
    required_permission = "read,apply"
    server_name = "JobMCP"

    @audit_tool_call
    def search_jobs(self, candidate_id: int, db: Session) -> list:
        """Returns top matched jobs for the candidate."""
        self._log_call("search_jobs", candidate_id)
        try:
            from app.models.models import JobMatch, Job
            matches = db.query(JobMatch, Job).join(
                Job, JobMatch.job_id == Job.id
            ).filter(
                JobMatch.candidate_id == candidate_id,
                Job.status == "active"
            ).order_by(JobMatch.match_score.desc()).limit(20).all()
            return [
                {
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.department,
                    "location": job.location,
                    "salary_range": job.salary_range,
                    "match_score": round(match.match_score),
                    "skills_gap": match.skills_gap or "",
                    "experience_level": job.experience_level,
                }
                for match, job in matches
            ]
        except Exception as e:
            logger.error(f"search_jobs error: {e}")
            return []

    @audit_tool_call
    def get_saved_jobs(self, candidate_id: int, db: Session) -> list:
        """Returns jobs saved/bookmarked by the candidate."""
        self._log_call("get_saved_jobs", candidate_id)
        try:
            from app.models.models import SavedJob, Job
            saved = db.query(SavedJob, Job).join(
                Job, SavedJob.job_id == Job.id
            ).filter(SavedJob.candidate_id == candidate_id).all()
            return [
                {"job_id": job.id, "title": job.title, "company": job.department,
                 "saved_at": sv.saved_at.isoformat()}
                for sv, job in saved
            ]
        except Exception as e:
            logger.error(f"get_saved_jobs error: {e}")
            return []

    @audit_tool_call
    def get_applications(self, candidate_id: int, db: Session) -> list:
        """Returns all job applications and their current status."""
        self._log_call("get_applications", candidate_id)
        try:
            from app.models.models import Application, Job
            apps = db.query(Application, Job).join(
                Job, Application.job_id == Job.id
            ).filter(Application.candidate_id == candidate_id).order_by(
                Application.created_at.desc()
            ).all()
            return [
                {
                    "application_id": app.id,
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.department,
                    "status": app.status,
                    "applied_at": app.created_at.isoformat(),
                    "updated_at": app.updated_at.isoformat(),
                }
                for app, job in apps
            ]
        except Exception as e:
            logger.error(f"get_applications error: {e}")
            return []

    @audit_tool_call
    def get_application_timeline(self, candidate_id: int, db: Session) -> list:
        """Returns application pipeline stages for each application."""
        return self.get_applications(candidate_id, db)

    @audit_tool_call
    def get_skill_gaps_for_jobs(self, candidate_id: int, db: Session) -> list:
        """Returns aggregated skill gaps across top job matches."""
        self._log_call("get_skill_gaps_for_jobs", candidate_id)
        try:
            from app.models.models import JobMatch
            matches = db.query(JobMatch).filter(
                JobMatch.candidate_id == candidate_id
            ).order_by(JobMatch.match_score.desc()).limit(15).all()
            gap_counts = {}
            for m in matches:
                if m.skills_gap:
                    for sk in m.skills_gap.split(","):
                        sk = sk.strip().title()
                        if sk:
                            gap_counts[sk] = gap_counts.get(sk, 0) + 1
            gaps = sorted(
                [{"skill": k, "count": v, "priority": "High" if v > 5 else "Medium" if v > 2 else "Low"}
                 for k, v in gap_counts.items()],
                key=lambda x: x["count"], reverse=True
            )
            return gaps[:10]
        except Exception as e:
            logger.error(f"get_skill_gaps_for_jobs error: {e}")
            return []


job_mcp = JobMCPServer()
