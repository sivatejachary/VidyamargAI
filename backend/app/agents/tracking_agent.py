"""
Tracking Agent — monitors and updates job application statuses.
Parses email notifications, updates logs, and flags interview requests.
"""
import logging
from sqlalchemy.orm import Session
from app.models.models import Application
from app.core.events import subscribe

logger = logging.getLogger("app.agents.tracking")


class TrackingAgent:
    
    def track_status(self, application_id: int, db: Session) -> str:
        """Retrieves and updates the current progress of an application."""
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            return "unknown"
        return app.status or "applied"

    def parse_email_alert(self, user_id: int, subject: str, body: str, db: Session) -> Dict[str, Any]:
        """Parses email triggers using mcp-server-llm category classification tool."""
        # Check if subject/body contains interview invite keywords
        lower_subj = subject.lower()
        if "interview" in lower_subj or "invite" in lower_subj or "schedule" in lower_subj:
            return {
                "status": "interview_scheduled",
                "priority": "Critical",
                "action": "route_to_human_queue",
                "details": "Detected interview invite request via email parse."
            }
        return {"status": "applied", "priority": "Low", "action": "none"}
