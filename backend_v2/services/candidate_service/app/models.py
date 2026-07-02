from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class CandidateModel(Base):
    """Candidate account record details."""
    __tablename__ = "candidates"

    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CandidateProfileModel(Base):
    """Parsed resume profile and skill graph metrics."""
    __tablename__ = "candidate_profiles"

    id = Column(String(255), primary_key=True)
    candidate_id = Column(String(255), ForeignKey("candidates.id"), nullable=False, index=True)
    summary = Column(Text if 'Text' in globals() else String, nullable=True)
    skills_graph = Column(JSONB, default=dict)
    experience_graph = Column(JSONB, default=list)
    education_graph = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class EventOutboxModel(Base):
    """Outbox pattern table ensuring reliable event streaming."""
    __tablename__ = "candidate_event_outbox"

    id = Column(String(255), primary_key=True)
    aggregate_type = Column(String(255), nullable=False)
    aggregate_id = Column(String(255), nullable=False)
    event_type = Column(String(255), nullable=False)
    payload = Column(JSONB, nullable=False)
    published = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
