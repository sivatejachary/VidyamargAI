"""
Agent Activity Feed — logs every meaningful agent action.
Powers the live dashboard feed showing what agents have done.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.mcp_models import AgentActivity

logger = logging.getLogger("app.services.activity_feed")


ACTION_DESCRIPTIONS = {
    "job_search":        lambda n: f"Job Agent found {n} matching positions",
    "skill_gap":         lambda n: f"Skill Gap Agent detected {n} missing skills",
    "resume_improve":    lambda n: "Resume Agent analyzed your resume and found improvements",
    "course_recommend":  lambda n: f"Learning Agent recommended {n} courses",
    "resume_uploaded":   lambda n: "Resume Agent processed your new resume",
    "interview_prep":    lambda n: "Interview Agent prepared practice questions",
    "general":           lambda n: "Tush AI responded to your question",
}


def log(
    user_id: int,
    agent_name: str,
    action: str,
    card_count: int = 0,
    meta: dict = None,
    db: Session = None
):
    """Logs an agent activity to the feed."""
    if not db:
        return
    try:
        describe_fn = ACTION_DESCRIPTIONS.get(action, lambda n: f"{agent_name} completed {action}")
        detail = describe_fn(card_count)
        activity = AgentActivity(
            user_id=user_id,
            agent_name=agent_name,
            action=action,
            detail=detail,
            meta=meta or {"card_count": card_count},
        )
        db.add(activity)
        db.commit()
        logger.info(f"Activity logged: user={user_id}, agent={agent_name}, action={action}")
    except Exception as e:
        logger.error(f"Activity feed log failed: {e}")


def get_feed(user_id: int, limit: int = 20, db: Session = None) -> list:
    """Returns the latest agent activities for a user."""
    if not db:
        return []
    try:
        activities = db.query(AgentActivity).filter(
            AgentActivity.user_id == user_id
        ).order_by(AgentActivity.created_at.desc()).limit(limit).all()
        return [
            {
                "id": a.id,
                "agent_name": a.agent_name,
                "action": a.action,
                "detail": a.detail,
                "meta": a.meta,
                "created_at": a.created_at.isoformat(),
            }
            for a in activities
        ]
    except Exception as e:
        logger.error(f"Activity feed fetch failed: {e}")
        return []
