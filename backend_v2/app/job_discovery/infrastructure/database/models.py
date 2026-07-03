"""
VidyaMarg AI — Database ORM Models (SQLAlchemy 2.x)
====================================================
Production schema with range-partitioned jobs table, composite indexes,
and full domain coverage for the autonomous job discovery pipeline.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    REAL, BigInteger, Boolean, CheckConstraint, Column, DateTime,
    ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

class CompanyORM(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    sub_industry = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)  # startup|sme|mid|enterprise|fortune500
    headquarters = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    glassdoor_rating = Column(REAL, nullable=True)
    trust_score = Column(REAL, default=0.5)
    is_verified = Column(Boolean, default=False)
    is_blacklisted = Column(Boolean, default=False)
    blacklist_reason = Column(String(255), nullable=True)
    meta = Column(JSON, default=dict)
    embedding_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    jobs = relationship("JobORM", back_populates="company", lazy="dynamic")

    __table_args__ = (
        UniqueConstraint("normalized_name", name="uq_company_normalized_name"),
        Index("idx_company_industry", "industry"),
        Index("idx_company_trust", "trust_score"),
        CheckConstraint("trust_score >= 0.0 AND trust_score <= 1.0", name="chk_company_trust"),
    )


# ---------------------------------------------------------------------------
# Job Sources Registry
# ---------------------------------------------------------------------------

class JobSourceORM(Base):
    __tablename__ = "job_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    source_type = Column(String(50), nullable=False)  # api|scraper|rss|telegram|partner
    base_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=5)
    rate_limit_rpm = Column(Integer, default=60)
    rate_limit_daily = Column(Integer, default=10000)
    health_score = Column(REAL, default=1.0)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, default=0)
    total_jobs_discovered = Column(BigInteger, default=0)
    total_jobs_accepted = Column(BigInteger, default=0)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    jobs = relationship("JobORM", back_populates="source", lazy="dynamic")

    __table_args__ = (
        Index("idx_jobsource_active_priority", "is_active", "priority"),
        CheckConstraint("priority >= 1 AND priority <= 10", name="chk_source_priority"),
    )


# ---------------------------------------------------------------------------
# Core Jobs Table
# Note: In production, add PostgreSQL range partitioning via raw DDL migration.
# ---------------------------------------------------------------------------

class JobORM(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(500), nullable=False)
    source_id = Column(Integer, ForeignKey("job_sources.id", ondelete="SET NULL"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)

    # Core identity
    title = Column(String(500), nullable=False)
    title_normalized = Column(String(500), nullable=False)
    company_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    description_summary = Column(Text, nullable=True)
    apply_url = Column(String(1000), nullable=True)
    job_url = Column(String(1000), nullable=True)

    # Location
    location = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(10), default="IN")
    is_remote = Column(Boolean, default=False)
    is_hybrid = Column(Boolean, default=False)
    work_mode = Column(String(50), nullable=True)

    # Classification
    role_category = Column(String(100), nullable=True)
    role_sub_category = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    seniority = Column(String(50), nullable=True)
    employment_type = Column(String(50), nullable=True)

    # Skills (stored as JSON arrays)
    required_skills = Column(JSON, default=list)
    preferred_skills = Column(JSON, default=list)
    skill_graph = Column(JSON, default=dict)

    # Compensation
    salary_min = Column(Numeric(15, 2), nullable=True)
    salary_max = Column(Numeric(15, 2), nullable=True)
    salary_currency = Column(String(10), default="INR")
    salary_period = Column(String(20), default="yearly")
    salary_raw = Column(String(255), nullable=True)

    # Experience
    experience_min_years = Column(REAL, nullable=True)
    experience_max_years = Column(REAL, nullable=True)

    # Quality Scores
    trust_score = Column(REAL, default=0.5)
    quality_score = Column(REAL, default=0.5)
    freshness_score = Column(REAL, default=1.0)
    spam_score = Column(REAL, default=0.0)

    # Lifecycle
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    rejection_reason = Column(String(255), nullable=True)
    lifecycle_status = Column(String(50), default="discovered")

    # Vector Index
    embedding_id = Column(String(100), nullable=True)  # Qdrant point UUID
    embedding_version = Column(Integer, default=0)
    qdrant_sync_pending = Column(Boolean, default=False)

    # Timestamps
    posted_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    discovered_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    source = relationship("JobSourceORM", back_populates="jobs")
    company = relationship("CompanyORM", back_populates="jobs")
    skills = relationship("JobSkillORM", back_populates="job", cascade="all, delete-orphan")
    matches = relationship("CandidateMatchORM", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_job_active_quality", "is_active", "quality_score"),
        Index("idx_job_lifecycle", "lifecycle_status", "created_at"),
        Index("idx_job_role_seniority", "role_category", "seniority"),
        Index("idx_job_country_city", "country", "city"),
        Index("idx_job_external_source", "external_id", "source_id"),
        Index("idx_job_posted_active", "posted_at", "is_active"),
        Index("idx_job_qdrant_pending", "qdrant_sync_pending"),
        CheckConstraint("trust_score >= 0.0 AND trust_score <= 1.0", name="chk_job_trust"),
        CheckConstraint("quality_score >= 0.0 AND quality_score <= 1.0", name="chk_job_quality"),
        CheckConstraint("spam_score >= 0.0 AND spam_score <= 1.0", name="chk_job_spam"),
    )


# ---------------------------------------------------------------------------
# Job Skills (Normalized Bridge)
# ---------------------------------------------------------------------------

class JobSkillORM(Base):
    __tablename__ = "job_skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    skill_name = Column(String(100), nullable=False)
    weight = Column(REAL, default=1.0)
    is_required = Column(Boolean, default=True)

    job = relationship("JobORM", back_populates="skills")

    __table_args__ = (
        Index("idx_job_skill_name", "skill_name"),
        Index("idx_job_skill_job_id", "job_id"),
    )


# ---------------------------------------------------------------------------
# Candidate Matches
# ---------------------------------------------------------------------------

class CandidateMatchORM(Base):
    __tablename__ = "candidate_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    overall_score = Column(REAL, nullable=False)
    semantic_score = Column(REAL, default=0.0)
    skill_score = Column(REAL, default=0.0)
    experience_score = Column(REAL, default=0.0)
    salary_score = Column(REAL, default=0.0)
    location_score = Column(REAL, default=0.0)
    remote_preference_score = Column(REAL, default=0.0)
    company_preference_score = Column(REAL, default=0.0)
    freshness_score = Column(REAL, default=0.0)
    match_reasons = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    skill_gap_severity = Column(String(20), default="none")
    match_explanation = Column(Text, nullable=True)
    status = Column(String(50), default="new")
    is_seen = Column(Boolean, default=False)
    is_saved = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)
    user_reaction = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship("JobORM", back_populates="matches")
    recommendations = relationship("RecommendationORM", back_populates="match")

    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_match_candidate_job"),
        Index("idx_match_candidate_score", "candidate_id", "overall_score"),
        Index("idx_match_candidate_status", "candidate_id", "status"),
        CheckConstraint("overall_score >= 0.0 AND overall_score <= 100.0", name="chk_match_score"),
    )


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

class RecommendationORM(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, nullable=False)
    match_id = Column(Integer, ForeignKey("candidate_matches.id", ondelete="CASCADE"), nullable=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    score = Column(REAL, nullable=False)
    reason = Column(Text, nullable=True)
    is_seen = Column(Boolean, default=False)
    is_actioned = Column(Boolean, default=False)
    actioned_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    match = relationship("CandidateMatchORM", back_populates="recommendations")

    __table_args__ = (
        Index("idx_rec_candidate_seen", "candidate_id", "is_seen"),
        Index("idx_rec_candidate_created", "candidate_id", "created_at"),
    )


# ---------------------------------------------------------------------------
# Crawl History
# ---------------------------------------------------------------------------

class CrawlHistoryORM(Base):
    __tablename__ = "crawl_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), nullable=False)
    source_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # running|success|failed|partial
    jobs_found = Column(Integer, default=0)
    jobs_saved = Column(Integer, default=0)
    jobs_deduplicated = Column(Integer, default=0)
    jobs_rejected = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    execution_ms = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_crawl_run_source", "run_id", "source_name"),
        Index("idx_crawl_started", "started_at"),
    )


# ---------------------------------------------------------------------------
# Connector Health Monitor
# ---------------------------------------------------------------------------

class ConnectorHealthORM(Base):
    __tablename__ = "connector_health"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # healthy|degraded|rate_limited|offline
    latency_ms = Column(Integer, nullable=True)
    error_details = Column(Text, nullable=True)
    checked_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_connector_health_name", "source_name", "checked_at"),
    )


# ---------------------------------------------------------------------------
# Job Events (Immutable Audit Log)
# ---------------------------------------------------------------------------

class JobEventORM(Base):
    __tablename__ = "job_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False)
    event_id = Column(String(36), nullable=False)
    version = Column(Integer, default=1)
    correlation_id = Column(String(36), nullable=True)
    trace_id = Column(String(36), nullable=True)
    producer = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_job_event_type_created", "event_type", "created_at"),
        Index("idx_job_event_correlation", "correlation_id"),
    )
