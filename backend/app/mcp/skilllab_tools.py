"""
SkillLab MCP Server — tools for AI to access learning data.
"""
import json
import logging
from sqlalchemy.orm import Session
from app.mcp.base import BaseMCPServer

logger = logging.getLogger("app.mcp.skilllab")


class SkillLabMCPServer(BaseMCPServer):
    required_permission = "read,write"
    server_name = "SkillLabMCP"

    def get_enrolled_courses(self, user_id: int, db: Session) -> list:
        """Returns all courses the user is enrolled in with progress."""
        self._log_call("get_enrolled_courses", user_id)
        try:
            from app.models.models import CourseProgress
            progresses = db.query(CourseProgress).filter(
                CourseProgress.user_id == user_id
            ).all()
            return [
                {
                    "course_id": p.course_id,
                    "overall_progress": p.overall_progress,
                    "video_progress": p.video_progress,
                    "quiz_progress": p.quiz_progress,
                    "last_lesson_id": p.last_lesson_id,
                    "last_activity": p.last_activity.isoformat() if p.last_activity else None,
                }
                for p in progresses
            ]
        except Exception as e:
            logger.error(f"get_enrolled_courses error: {e}")
            return []

    def get_course_progress(self, user_id: int, course_id: str, db: Session) -> dict:
        """Returns detailed progress for a specific course."""
        self._log_call("get_course_progress", user_id)
        try:
            from app.models.models import CourseProgress
            p = db.query(CourseProgress).filter(
                CourseProgress.user_id == user_id,
                CourseProgress.course_id == course_id
            ).first()
            if not p:
                return {"enrolled": False, "course_id": course_id}
            return {
                "enrolled": True,
                "course_id": course_id,
                "overall_progress": p.overall_progress,
                "video_progress": p.video_progress,
                "pdf_progress": p.pdf_progress,
                "quiz_progress": p.quiz_progress,
                "last_lesson_id": p.last_lesson_id,
            }
        except Exception as e:
            logger.error(f"get_course_progress error: {e}")
            return {"error": str(e)}

    def get_skill_gaps(self, candidate_id: int, db: Session) -> list:
        """Returns skill gaps by analyzing job matches vs candidate skills."""
        self._log_call("get_skill_gaps", candidate_id)
        try:
            from app.models.models import JobMatch
            from app.agents.skill_gap import SkillGapAgent
            matches = db.query(JobMatch).filter(
                JobMatch.candidate_id == candidate_id,
                JobMatch.match_score < 80
            ).order_by(JobMatch.match_score.asc()).limit(10).all()
            job_data = []
            for m in matches:
                if m.skills_gap:
                    skills = [s.strip() for s in m.skills_gap.split(",") if s.strip()]
                    job_data.append({"missing_skills": skills, "match_score": m.match_score})
            if job_data:
                agent = SkillGapAgent(job_data)
                return agent.analyze_gaps()
            return []
        except Exception as e:
            logger.error(f"get_skill_gaps error: {e}")
            return []

    def get_learning_health(self, user_id: int, db: Session) -> dict:
        """Returns a learning health summary."""
        self._log_call("get_learning_health", user_id)
        try:
            from app.models.models import LearningEvent, CourseProgress, User
            from datetime import timedelta
            from sqlalchemy import func
            # Count events in last 7 days
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_events = db.query(LearningEvent).filter(
                LearningEvent.user_id == user_id,
                LearningEvent.created_at >= week_ago
            ).count()
            # Count active courses
            active_courses = db.query(CourseProgress).filter(
                CourseProgress.user_id == user_id,
                CourseProgress.overall_progress > 0,
                CourseProgress.overall_progress < 100
            ).count()
            # Completed courses
            completed_courses = db.query(CourseProgress).filter(
                CourseProgress.user_id == user_id,
                CourseProgress.overall_progress >= 100
            ).count()
            user = db.query(User).filter(User.id == user_id).first()
            health_score = min(100, (recent_events * 10) + (completed_courses * 20) + (active_courses * 5))
            return {
                "health_score": health_score,
                "events_this_week": recent_events,
                "active_courses": active_courses,
                "completed_courses": completed_courses,
                "streak_days": user.user_streaks if user else 0,
                "xp": user.user_xp if user else 0,
            }
        except Exception as e:
            logger.error(f"get_learning_health error: {e}")
            return {"health_score": 0, "error": str(e)}


from datetime import datetime
skilllab_mcp = SkillLabMCPServer()
