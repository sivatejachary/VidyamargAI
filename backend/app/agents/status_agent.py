"""
Status Agent — tracks application progress, pipeline stages, and interview loops.
"""
import logging
from sqlalchemy.orm import Session
from app.models.models import Application

logger = logging.getLogger("app.agents.status")


class StatusAgent:
    def __init__(self, db: Session):
        self.db = db

    def get_pipeline_status(self, candidate_id: int) -> dict:
        """Returns details on the current application pipeline status."""
        apps = self.db.query(Application).filter(Application.candidate_id == candidate_id).all()
        pipeline = {
            "applied": 0,
            "screening": 0,
            "interviewing": 0,
            "offer": 0,
            "rejected": 0
        }
        for app in apps:
            status = (app.status or "applied").lower()
            if status in pipeline:
                pipeline[status] += 1
            else:
                pipeline["applied"] += 1
                
        return {
            "total_applications": len(apps),
            "pipeline": pipeline,
            "active_interviews": pipeline["interviewing"]
        }
