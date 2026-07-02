"""
VidyaMarg AI OS — Pool Models
Retained: CareerHealthSnapshot for tracking candidate career health over time.
Removed: JobPool, JobPoolMatch (job feature removal).
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, Index, JSON
)
from app.core.database import Base


class CareerHealthSnapshot(Base):
    """
    Daily snapshots of candidate career health score metrics.
    """
    __tablename__ = "career_health_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    overall_score = Column(Float, default=0.0)
    skills_health = Column(Float, default=0.0)
    market_demand = Column(Float, default=0.0)
    experience_score = Column(Float, default=0.0)
    resume_health = Column(Float, default=0.0)
    learning_progress = Column(Float, default=0.0)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_chs_candidate_created", "candidate_id", "created_at"),
    )
