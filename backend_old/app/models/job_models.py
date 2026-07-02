"""
VidyaMarg AI — Job Intelligence Models
Full production-grade schema for the AI Career Agent system.

Tables:
  companies, job_sources, jobs, job_skill_graph,
  candidate_agents, candidate_agent_preferences, agent_runs, agent_actions, agent_notifications,
  matches, recommendations, applications, application_events,
  career_insights, market_intelligence, interview_preparations,
  skill_gap_analysis, analytics_events
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float,
    ForeignKey, Index, JSON, CheckConstraint, UniqueConstraint, BigInteger
)
from sqlalchemy.orm import relationship
from app.core.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# COMPANY INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────

class Company(Base):
    """Company intelligence record — enriched from job postings and external sources."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    normalized_name = Column(String(255), nullable=False, index=True)  # lowercase, no punctuation
    domain = Column(String(255), nullable=True, index=True)
    industry = Column(String(100), nullable=True, index=True)
    sub_industry = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)   # startup, sme, mid, enterprise, fortune500
    founded_year = Column(Integer, nullable=True)
    headquarters = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    website = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    glassdoor_rating = Column(Float, nullable=True)
    glassdoor_reviews = Column(Integer, nullable=True)
    trust_score = Column(Float, default=0.5)     # 0.0-1.0
    is_verified = Column(Boolean, default=False)
    is_blacklisted = Column(Boolean, default=False)
    blacklist_reason = Column(String(255), nullable=True)
    meta = Column(JSON, default=dict)
    embedding_id = Column(String(100), nullable=True)  # Qdrant point ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    jobs = relationship("Job", back_populates="company")

    __table_args__ = (
        UniqueConstraint("normalized_name", name="uq_company_normalized_name"),
        Index("idx_company_industry", "industry"),
        Index("idx_company_trust", "trust_score"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# JOB SOURCE CONNECTORS
# ─────────────────────────────────────────────────────────────────────────────

class JobSource(Base):
    """Registry of job discovery connectors with health tracking."""
    __tablename__ = "job_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)   # linkedin, indeed, naukri, serper
    display_name = Column(String(100), nullable=False)
    source_type = Column(String(50), nullable=False)          # api, scraper, partner, rss
    base_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=5)                     # 1-10, lower = higher priority
    rate_limit_rpm = Column(Integer, default=60)              # requests per minute
    rate_limit_daily = Column(Integer, default=10000)
    health_score = Column(Float, default=1.0)                 # 0.0-1.0
    last_success_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    total_jobs_discovered = Column(BigInteger, default=0)
    total_jobs_accepted = Column(BigInteger, default=0)
    total_jobs_rejected = Column(BigInteger, default=0)
    config = Column(JSON, default=dict)   # connector-specific config
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    jobs = relationship("Job", back_populates="source")

    __table_args__ = (
        Index("idx_jobsource_active_priority", "is_active", "priority"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# CORE JOB ENTITY
# ─────────────────────────────────────────────────────────────────────────────

class Job(Base):
    """
    Core job intelligence entity.
    Partitioned by created_at for scale (handled at DB level).
    All intelligence scores are pre-computed at ingestion time.
    """
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(500), nullable=True, index=True)   # source-specific ID
    source_id = Column(Integer, ForeignKey("job_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)

    # Core fields
    title = Column(String(500), nullable=False, index=True)
    title_normalized = Column(String(500), nullable=True, index=True)  # cleaned, lowercased
    company_name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    description_summary = Column(Text, nullable=True)   # AI-generated 3-sentence summary
    apply_url = Column(String(1000), nullable=True)
    job_url = Column(String(1000), nullable=True)

    # Location
    location = Column(String(500), nullable=True, index=True)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)
    is_remote = Column(Boolean, default=False, index=True)
    is_hybrid = Column(Boolean, default=False)

    # Classification (AI-generated)
    role_category = Column(String(100), nullable=True, index=True)     # engineering, healthcare, finance...
    role_sub_category = Column(String(100), nullable=True, index=True)  # backend, frontend, devops...
    industry = Column(String(100), nullable=True, index=True)
    seniority = Column(String(50), nullable=True, index=True)           # intern, junior, mid, senior, lead, director, vp, cxo
    employment_type = Column(String(50), nullable=True)                 # full_time, part_time, contract, freelance
    work_mode = Column(String(50), nullable=True)                       # remote, onsite, hybrid

    # Skills (AI-extracted)
    required_skills = Column(JSON, default=list)    # ["Python", "FastAPI", ...]
    preferred_skills = Column(JSON, default=list)
    skill_graph = Column(JSON, default=dict)         # {skill: weight}

    # Compensation
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String(10), default="USD")
    salary_period = Column(String(20), default="yearly")   # yearly, monthly, hourly
    salary_raw = Column(String(255), nullable=True)        # raw text from source

    # Experience requirements
    experience_min_years = Column(Float, nullable=True)
    experience_max_years = Column(Float, nullable=True)

    # Quality Intelligence Scores (0.0-1.0)
    trust_score = Column(Float, default=0.5, index=True)        # is this a real company?
    quality_score = Column(Float, default=0.5, index=True)      # is this a quality posting?
    freshness_score = Column(Float, default=1.0, index=True)    # how recent?
    spam_score = Column(Float, default=0.0, index=True)         # probability of spam/fake

    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    rejection_reason = Column(String(255), nullable=True)      # spam, duplicate, expired, fake

    # Embedding
    embedding_id = Column(String(100), nullable=True)          # Qdrant point ID
    embedding_version = Column(Integer, default=0)

    # Dates
    posted_at = Column(DateTime, nullable=True, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    discovered_at = Column(DateTime, default=datetime.utcnow, index=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    source = relationship("JobSource", back_populates="jobs")
    company = relationship("Company", back_populates="jobs")
    matches = relationship("Match", back_populates="job")
    applications = relationship("Application", back_populates="job")

    __table_args__ = (
        Index("idx_job_active_quality", "is_active", "quality_score"),
        Index("idx_job_active_trust", "is_active", "trust_score"),
        Index("idx_job_active_fresh", "is_active", "freshness_score"),
        Index("idx_job_role_seniority", "role_category", "seniority"),
        Index("idx_job_country_city", "country", "city"),
        Index("idx_job_company_posted", "company_id", "posted_at"),
        Index("idx_job_external_source", "external_id", "source_id"),
        CheckConstraint("trust_score >= 0.0 AND trust_score <= 1.0", name="chk_job_trust_range"),
        CheckConstraint("quality_score >= 0.0 AND quality_score <= 1.0", name="chk_job_quality_range"),
        CheckConstraint("spam_score >= 0.0 AND spam_score <= 1.0", name="chk_job_spam_range"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# AI AGENT STATE
# ─────────────────────────────────────────────────────────────────────────────

class CandidateAgent(Base):
    """
    Per-candidate AI Job Agent instance.
    Tracks agent state, preferences, and lifecycle.
    """
    __tablename__ = "candidate_agents"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    status = Column(String(50), default="active")       # active, paused, stopped
    career_dna = Column(JSON, default=dict)              # AI-generated career identity
    skill_graph = Column(JSON, default=dict)             # {skill: {level, years, last_used}}
    career_graph = Column(JSON, default=dict)            # career path tree
    industry_dna = Column(JSON, default=dict)            # industry + domain analysis
    target_roles = Column(JSON, default=list)            # list of target role objects
    target_locations = Column(JSON, default=list)        # preferred locations
    target_salary_min = Column(Float, nullable=True)
    target_salary_max = Column(Float, nullable=True)
    target_salary_currency = Column(String(10), default="USD")
    work_mode_preference = Column(String(50), default="any")  # remote, hybrid, onsite, any
    employment_type_preference = Column(String(50), default="full_time")
    min_match_score = Column(Float, default=60.0)        # minimum match % to surface
    last_discovery_at = Column(DateTime, nullable=True)
    last_match_at = Column(DateTime, nullable=True)
    next_scheduled_at = Column(DateTime, nullable=True)
    total_jobs_discovered = Column(Integer, default=0)
    total_jobs_matched = Column(Integer, default=0)
    total_applications = Column(Integer, default=0)
    embedding_version = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    agent_runs = relationship("AgentRun", back_populates="agent")
    notifications = relationship("AgentNotification", back_populates="agent")

    __table_args__ = (
        Index("idx_agent_status_next", "status", "next_scheduled_at"),
    )


class CandidateAgentPreferences(Base):
    """User-controlled agent preferences (editable from UI)."""
    __tablename__ = "candidate_agent_preferences"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True)
    auto_discover = Column(Boolean, default=True)
    discovery_frequency_hours = Column(Integer, default=6)    # how often to run discovery
    notify_new_matches = Column(Boolean, default=True)
    notify_application_updates = Column(Boolean, default=True)
    notify_skill_gaps = Column(Boolean, default=True)
    notify_market_changes = Column(Boolean, default=False)
    min_match_score_notify = Column(Float, default=70.0)     # only notify if match > X
    excluded_companies = Column(JSON, default=list)           # company names to skip
    excluded_keywords = Column(JSON, default=list)            # job title keywords to skip
    preferred_company_sizes = Column(JSON, default=list)     # startup, enterprise, etc
    preferred_industries = Column(JSON, default=list)
    open_to_relocation = Column(Boolean, default=False)
    max_commute_km = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentRun(Base):
    """Single execution run of the AI Job Agent pipeline."""
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("candidate_agents.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    run_type = Column(String(50), nullable=False)   # discovery, matching, recommendation, full
    status = Column(String(50), default="running")  # running, completed, failed, cancelled
    trigger = Column(String(50), default="scheduled")  # scheduled, resume_upload, manual, webhook
    jobs_discovered = Column(Integer, default=0)
    jobs_matched = Column(Integer, default=0)
    jobs_rejected = Column(Integer, default=0)
    recommendations_generated = Column(Integer, default=0)
    skill_gaps_updated = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    llm_cost_usd = Column(Float, default=0.0)
    embedding_cost_usd = Column(Float, default=0.0)
    meta = Column(JSON, default=dict)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    agent = relationship("CandidateAgent", back_populates="agent_runs")

    __table_args__ = (
        Index("idx_agentrun_agent_status", "agent_id", "status"),
        Index("idx_agentrun_candidate_started", "candidate_id", "started_at"),
    )


class AgentAction(Base):
    """Individual actions taken by the AI agent during a run."""
    __tablename__ = "agent_actions"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(100), nullable=False)  # discover_jobs, match_job, generate_recommendation, etc.
    agent_name = Column(String(100), nullable=False)   # which sub-agent took this action
    status = Column(String(50), default="completed")   # completed, failed, skipped
    input_summary = Column(Text, nullable=True)        # brief description of input
    output_summary = Column(Text, nullable=True)       # brief description of output
    duration_ms = Column(Integer, nullable=True)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_agentaction_run", "run_id"),
        Index("idx_agentaction_candidate", "candidate_id"),
    )


class AgentNotification(Base):
    """Agent-generated notifications for users."""
    __tablename__ = "agent_notifications"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("candidate_agents.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = Column(String(100), nullable=False)  # new_match, application_update, skill_gap, market_change
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    action_url = Column(String(500), nullable=True)          # deep link
    entity_type = Column(String(50), nullable=True)          # job, application, skill
    entity_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime, nullable=True)
    priority = Column(String(20), default="normal")          # low, normal, high, urgent
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    agent = relationship("CandidateAgent", back_populates="notifications")

    __table_args__ = (
        Index("idx_agentnotif_candidate_unread", "candidate_id", "is_read"),
        Index("idx_agentnotif_created", "created_at"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# MATCHING ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class Match(Base):
    """
    Candidate ↔ Job match record with full score breakdown.
    Generated by the matching engine — never by user search.
    """
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)

    # Composite score
    overall_score = Column(Float, nullable=False, index=True)         # 0-100

    # Component scores (0-100 each)
    semantic_score = Column(Float, default=0.0)        # Qdrant cosine similarity
    skill_score = Column(Float, default=0.0)           # required skills overlap
    experience_score = Column(Float, default=0.0)      # years of experience fit
    education_score = Column(Float, default=0.0)       # education match
    location_score = Column(Float, default=0.0)        # location preference match
    salary_score = Column(Float, default=0.0)          # salary range match
    career_progression_score = Column(Float, default=0.0)  # is this a career advancement?
    seniority_score = Column(Float, default=0.0)       # seniority level fit

    # Intelligence
    match_reasons = Column(JSON, default=list)          # ["Strong Python match", "Relevant fintech experience"]
    missing_skills = Column(JSON, default=list)         # ["Kubernetes", "Rust"]
    skill_gap_severity = Column(String(20), default="none")  # none, minor, moderate, major
    career_growth_score = Column(Float, default=0.0)   # 0-100, would this advance career?
    match_explanation = Column(Text, nullable=True)    # AI-generated paragraph

    # Status
    status = Column(String(50), default="new", index=True)   # new, viewed, saved, applied, hidden, expired
    is_seen = Column(Boolean, default=False)
    seen_at = Column(DateTime, nullable=True)
    is_saved = Column(Boolean, default=False)
    saved_at = Column(DateTime, nullable=True)
    is_hidden = Column(Boolean, default=False)

    # Feedback signals for recommendation learning
    user_reaction = Column(String(50), nullable=True)   # liked, disliked, not_relevant, too_junior, too_senior

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("Candidate")
    job = relationship("Job", back_populates="matches")

    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_match_candidate_job"),
        Index("idx_match_candidate_score", "candidate_id", "overall_score"),
        Index("idx_match_candidate_status", "candidate_id", "status"),
        Index("idx_match_candidate_created", "candidate_id", "created_at"),
        CheckConstraint("overall_score >= 0.0 AND overall_score <= 100.0", name="chk_match_score_range"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# RECOMMENDATIONS
# ─────────────────────────────────────────────────────────────────────────────

class Recommendation(Base):
    """AI-generated personalized recommendations (jobs, career paths, learning)."""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    rec_type = Column(String(50), nullable=False)        # job, career_path, skill, certification, course
    entity_id = Column(Integer, nullable=True)           # job_id if type=job
    entity_data = Column(JSON, default=dict)             # full data snapshot for non-job recs
    score = Column(Float, default=0.0)                   # recommendation confidence 0-100
    reason = Column(Text, nullable=True)                 # AI-generated explanation
    is_seen = Column(Boolean, default=False)
    is_actioned = Column(Boolean, default=False)         # user clicked / enrolled / applied
    actioned_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_rec_candidate_type", "candidate_id", "rec_type"),
        Index("idx_rec_candidate_seen", "candidate_id", "is_seen"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION TRACKING
# ─────────────────────────────────────────────────────────────────────────────

class Application(Base):
    """
    Full application lifecycle tracking.
    One record per candidate ↔ job pair.
    """
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="SET NULL"), nullable=True)

    # Kanban status
    status = Column(String(50), default="saved", index=True)
    # saved → applied → resume_viewed → shortlisted → interview_scheduled
    # → interview_completed → offer_received → accepted → rejected → withdrawn

    # Application details
    applied_via = Column(String(100), nullable=True)    # portal name, direct, referral
    resume_version_id = Column(Integer, ForeignKey("candidate_resumes.id", ondelete="SET NULL"), nullable=True)
    cover_letter = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)                 # user's personal notes

    # Key dates
    saved_at = Column(DateTime, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    resume_viewed_at = Column(DateTime, nullable=True)
    shortlisted_at = Column(DateTime, nullable=True)
    first_interview_at = Column(DateTime, nullable=True)
    offer_received_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    withdrawn_at = Column(DateTime, nullable=True)

    # Interview tracking
    interview_rounds = Column(Integer, default=0)
    interview_notes = Column(Text, nullable=True)
    offer_salary = Column(Float, nullable=True)
    offer_currency = Column(String(10), nullable=True)
    rejection_reason = Column(String(255), nullable=True)  # user's record of rejection reason

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("Candidate")
    job = relationship("Job", back_populates="applications")
    events = relationship("ApplicationEvent", back_populates="application", order_by="ApplicationEvent.created_at")

    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_application_candidate_job"),
        Index("idx_application_candidate_status", "candidate_id", "status"),
        Index("idx_application_candidate_created", "candidate_id", "created_at"),
    )


class ApplicationEvent(Base):
    """Immutable event log for every application status change."""
    __tablename__ = "application_events"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)    # status_changed, note_added, interview_scheduled
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=True)
    actor = Column(String(50), default="user")          # user, agent, system
    note = Column(Text, nullable=True)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    application = relationship("Application", back_populates="events")

    __table_args__ = (
        Index("idx_appevent_application", "application_id"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# INTERVIEW PREPARATION
# ─────────────────────────────────────────────────────────────────────────────

class InterviewPreparation(Base):
    """AI-generated interview preparation package for a specific job."""
    __tablename__ = "interview_preparations"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=True)

    company_analysis = Column(JSON, default=dict)          # products, culture, recent news, funding
    technical_questions = Column(JSON, default=list)       # [{question, hint, example_answer}]
    hr_questions = Column(JSON, default=list)
    behavioral_questions = Column(JSON, default=list)      # STAR format
    culture_fit_questions = Column(JSON, default=list)
    study_topics = Column(JSON, default=list)              # what to study
    estimated_prep_hours = Column(Float, nullable=True)
    difficulty_level = Column(String(50), nullable=True)   # easy, medium, hard
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_interviewprep_candidate_job", "candidate_id", "job_id"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# SKILL GAP ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

class SkillGapAnalysis(Base):
    """Per-candidate aggregate skill gap analysis across all target roles."""
    __tablename__ = "skill_gap_analysis"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_type = Column(String(50), default="overall")  # overall, per_role, per_job
    reference_id = Column(Integer, nullable=True)          # job_id or null for overall
    current_skills = Column(JSON, default=list)
    required_skills = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    skill_scores = Column(JSON, default=dict)     # {skill: match_score}
    learning_roadmap = Column(JSON, default=list) # [{skill, priority, resources, est_hours, career_impact}]
    overall_gap_score = Column(Float, default=0.0)  # 0=no gap, 100=complete mismatch
    estimated_upskill_months = Column(Float, nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_skillgap_candidate", "candidate_id"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# MARKET INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────

class CareerInsight(Base):
    """AI-generated career insights for a candidate."""
    __tablename__ = "career_insights"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    insight_category = Column(String(100), nullable=False)  # market_demand, salary_trend, role_trajectory
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    data = Column(JSON, default=dict)               # structured insight data
    confidence = Column(Float, default=0.8)         # AI confidence 0-1
    is_positive = Column(Boolean, nullable=True)    # is this a positive signal?
    actionable_steps = Column(JSON, default=list)   # what user can do
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_careerinsight_candidate", "candidate_id", "created_at"),
    )


class MarketIntelligence(Base):
    """Aggregated market intelligence snapshots (not per-candidate)."""
    __tablename__ = "market_intelligence"

    id = Column(Integer, primary_key=True, index=True)
    role_category = Column(String(100), nullable=False, index=True)
    industry = Column(String(100), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)
    city = Column(String(100), nullable=True)
    seniority = Column(String(50), nullable=True)

    # Metrics
    active_job_count = Column(Integer, default=0)
    avg_salary_min = Column(Float, nullable=True)
    avg_salary_max = Column(Float, nullable=True)
    salary_currency = Column(String(10), default="USD")
    demand_trend = Column(String(20), default="stable")   # growing, stable, declining
    demand_score = Column(Float, default=0.5)              # 0-1
    top_required_skills = Column(JSON, default=list)       # [{skill, count, trend}]
    top_companies_hiring = Column(JSON, default=list)
    emerging_skills = Column(JSON, default=list)
    average_time_to_fill_days = Column(Float, nullable=True)
    competition_score = Column(Float, default=0.5)         # how competitive is the market?
    snapshot_date = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_market_role_country_date", "role_category", "country", "snapshot_date"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────

class AnalyticsEvent(Base):
    """Immutable analytics event stream for learning signals."""
    __tablename__ = "analytics_events"

    id = Column(BigInteger, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    # job_viewed, job_saved, job_applied, job_hidden, match_liked, match_disliked
    # career_path_viewed, skill_gap_viewed, interview_prep_opened, recommendation_clicked
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    session_id = Column(String(100), nullable=True)
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_analytics_candidate_event", "candidate_id", "event_type"),
        Index("idx_analytics_created", "created_at"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# RESUME & CAREER INTELLIGENCE SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

class ResumeVersion(Base):
    """Stores full file upload history, raw text, and parsed JSON metadata for a candidate's resume."""
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_url = Column(String, nullable=False)
    extracted_text = Column(Text, nullable=True)
    parsed_json = Column(JSON, nullable=True)
    version_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)


class ResumeEmbedding(Base):
    """Stores embeddings per resume version."""
    __tablename__ = "resume_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = Column(Integer, ForeignKey("candidate_resumes.id", ondelete="CASCADE"), nullable=True)
    resume_version_id = Column(Integer, ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=True)
    embedding_model = Column(String(100), nullable=False)
    embedding_vector = Column(Text, nullable=False)  # JSON-serialized floats
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CandidateSkillGraph(Base):
    """Stores structured node/edge skill mappings for a candidate."""
    __tablename__ = "candidate_skill_graph"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    skills = Column(JSON, nullable=False)  # array of skills with score, confidence, market demand, experience estimate
    edges = Column(JSON, nullable=True)  # edges of the graph
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CandidateCareerGraph(Base):
    """Stores projected career graph stages."""
    __tablename__ = "candidate_career_graph"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    career_paths = Column(JSON, nullable=False)  # career paths tree
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CandidateCareerDNA(Base):
    """Stores career personalities (Builder, Researcher, Operator, etc.) and growth potential."""
    __tablename__ = "candidate_career_dna"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    personality = Column(String(100), nullable=True)
    traits = Column(JSON, nullable=False)  # working style, pattern, leadership potential, growth potential
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CareerPath(Base):
    """Project multi-role advancement sequences."""
    __tablename__ = "career_paths"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    path_name = Column(String(255), nullable=False)
    steps = Column(JSON, nullable=False)
    milestones = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CareerOpportunity(Base):
    """Stores the Top 100 potential jobs/exam tracks, scoring remote, government, and international potential."""
    __tablename__ = "career_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    role_title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)  # core, related, adjacent, transferable, future, leadership
    confidence_score = Column(Float, default=0.0)
    growth_score = Column(Float, default=0.0)
    salary_potential = Column(JSON, default=dict)
    remote_potential = Column(Float, default=0.0)
    government_potential = Column(Float, default=0.0)
    international_potential = Column(Float, default=0.0)
    requirements_match = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class ResumeImprovement(Base):
    """Stores ATS scores, keyword matching metrics, and AI recommendations for resume rewrites."""
    __tablename__ = "resume_improvements"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    ats_score = Column(Integer, default=0)
    formatting_score = Column(Integer, default=0)
    content_score = Column(Integer, default=0)
    keyword_score = Column(Integer, default=0)
    improvement_suggestions = Column(JSON, default=list)
    resume_rewrite_suggestions = Column(JSON, default=list)
    achievement_suggestions = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CareerEligibilityMatrix(Base):
    """Stores career family, eligible government/private exams and jobs, opportunity scores, and risk analysis."""
    __tablename__ = "career_eligibility_matrix"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    career_family = Column(String(100), nullable=True)  # Government, Private, PSU, etc.
    eligible_exams = Column(JSON, default=list)
    eligible_gov_jobs = Column(JSON, default=list)
    eligible_psu_jobs = Column(JSON, default=list)
    eligible_banking_jobs = Column(JSON, default=list)
    eligible_defence_jobs = Column(JSON, default=list)
    eligible_private_roles = Column(JSON, default=list)
    eligible_international_roles = Column(JSON, default=list)
    opportunity_scores = Column(JSON, default=dict)  # government, private, remote, international, leadership
    risk_analysis = Column(JSON, default=dict)  # demand_risk, automation_risk, competition, future_demand, salary_growth
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ResumeAIAnalysis(Base):
    """Stores full history of resume intelligence runs for a candidate, including source type and confidence."""
    __tablename__ = "resume_ai_analysis"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)  # GEMINI, FALLBACK
    raw_response = Column(Text, nullable=True)
    parsed_json = Column(JSON, nullable=True)
    confidence_score = Column(String(50), nullable=False)  # HIGH, MEDIUM
    created_at = Column(DateTime, default=datetime.utcnow)
