"""
VidyaMarg AI OS — Memory Models
Database tables for agent memory, learning preferences, application histories, and recruiter outreach.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class CandidatePreferences(Base):
    """
    Structured candidate preferences, updated continuously by the memory service.
    """
    __tablename__ = "candidate_preferences"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), unique=True, nullable=False)
    preferred_companies = Column(JSON, default=list)       # List of strings
    rejected_companies = Column(JSON, default=list)        # List of strings
    preferred_roles = Column(JSON, default=list)           # List of strings
    blacklisted_roles = Column(JSON, default=list)         # List of strings
    salary_min_lpa = Column(Float, default=0.0)
    salary_max_lpa = Column(Float, default=100.0)
    location_preferences = Column(JSON, default=list)      # List of locations e.g. ["Remote", "Bangalore"]
    work_mode = Column(String(50), default="any")          # "remote", "hybrid", "onsite", "any"
    max_commute_minutes = Column(Integer, default=60)
    company_size_preference = Column(String(50), default="any")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("Candidate")

    __table_args__ = (
        Index("idx_cp_candidate", "candidate_id"),
    )


class ApplicationHistory(Base):
    """
    Audited history of applications, views, and outcomes. Used by SuccessLearningLoop.
    """
    __tablename__ = "application_history"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)       # "job_rejected", "job_applied", "interview_passed", "interview_rejected", "ghosted"
    company = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    resume_id = Column(Integer, ForeignKey("candidate_resumes.id", ondelete="SET NULL"), nullable=True)
    match_score = Column(Float, nullable=True)             # Score at the time of application
    reason = Column(Text, nullable=True)                   # Dismissal or feedback reason
    created_at = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate")
    resume = relationship("CandidateResume")

    __table_args__ = (
        Index("idx_ah_candidate_event", "candidate_id", "event_type"),
    )


class RecruiterInteraction(Base):
    """
    Logs direct outreach messages and recruiter responses.
    """
    __tablename__ = "recruiter_interactions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    recruiter_name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=False)
    platform = Column(String(100), nullable=False)         # "linkedin", "email"
    message_sent = Column(Text, nullable=False)
    response_received = Column(Text, nullable=True)
    status = Column(String(50), default="sent")            # "sent", "viewed", "replied", "ignored"
    sent_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)

    candidate = relationship("Candidate")

    __table_args__ = (
        Index("idx_ri_candidate", "candidate_id"),
    )


class CompanyIntelligenceCache(Base):
    """
    Caches scraped company signals (funding, hiring velocity, glassdoor score).
    Expires regularly using cleanup workers.
    """
    __tablename__ = "company_intelligence_cache"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), unique=True, index=True, nullable=False)
    quality_score = Column(Float, default=50.0)
    data = Column(JSON, default=dict)                      # Full metrics dictionary
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_cic_company_name", "company_name"),
    )
