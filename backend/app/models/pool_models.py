"""
VidyaMarg AI OS — Pool Models
Database tables for pre-collected jobs, precomputed matches, and career health.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, Index, JSON
)
from app.core.database import Base


class JobPool(Base):
    """
    Pre-collected jobs stored in the database for instant UI loading (<100ms).
    Entries are regularly pruned using cleanup workers.
    """
    __tablename__ = "jobs_pool"

    id = Column(Integer, primary_key=True, index=True)
    stable_id = Column(String(16), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    experience = Column(String(100), nullable=True)
    skills = Column(JSON, default=list) # List of extracted skills
    apply_url = Column(Text, nullable=False)
    posted_date = Column(String(100), nullable=True)
    source = Column(String(100), nullable=False) # Greenhouse, Lever, RSS
    description = Column(Text, nullable=True)
    work_mode = Column(String(50), default="On-site") # On-site, Remote, Hybrid
    company_logo = Column(String(500), nullable=True)
    domain = Column(String(100), nullable=True)
    job_type = Column(String(50), default="Full-time")
    career_level = Column(String(50), default="Mid-level")
    all_sources = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_jobs_pool_stable_id", "stable_id"),
        Index("idx_jobs_pool_created_at", "created_at"),
    )


class JobPoolMatch(Base):
    """
    Precomputed match and opportunity scores for candidates.
    Matches are precomputed by background matching workers.
    """
    __tablename__ = "job_pool_matches"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    job_pool_id = Column(Integer, ForeignKey("jobs_pool.id", ondelete="CASCADE"), nullable=False)
    match_score = Column(Float, default=0.0)
    opportunity_score = Column(Float, default=0.0)
    skills_gap = Column(Text, nullable=True) # Comma-separated missing skills
    opportunity_breakdown = Column(JSON, default=dict)
    should_apply = Column(Boolean, default=False)
    reasons_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_jpm_candidate_score", "candidate_id", "opportunity_score"),
        Index("idx_jpm_candidate_job", "candidate_id", "job_pool_id"),
    )


class CareerHealthSnapshot(Base):
    """
    Daily snapshots of candidate's career health score metrics.
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
