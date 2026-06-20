"""
VidyaMarg AI OS — Auto Apply Models
All database tables for the Enterprise Auto Apply Agent.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime,
    ForeignKey, Index, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.core.database import Base


# ─── Application Lifecycle ────────────────────────────────────────────────────

class ApplicationRun(Base):
    """
    One record per Auto Apply trigger. Tracks the overall run state and metrics snapshot.
    """
    __tablename__ = "application_runs"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="queued")     # queued | running | completed | failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    stats = Column(JSON, default=dict)                # metrics snapshot at completion

    tasks = relationship("ApplicationTask", back_populates="run", cascade="all, delete-orphan")
    metrics = relationship("ApplicationMetrics", back_populates="run", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ar_candidate", "candidate_id"),
    )


class ApplicationTask(Base):
    """
    One record per job queued for application. Tracks the full lifecycle of a single application.
    """
    __tablename__ = "application_tasks"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("application_runs.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)

    # Job info (denormalized for history)
    job_title = Column(String(500), nullable=False)
    company = Column(String(255), nullable=False)
    apply_url = Column(Text, nullable=False)

    # Platform
    platform = Column(String(100), default="generic")    # detected platform key, never "linkedin" for auto-apply
    adapter_version = Column(String(100), nullable=True) # e.g. "greenhouse:1.0" — frozen at submission

    # Status
    status = Column(String(50), default="QUEUED")
    # QUEUED | RATE_LIMITED | READY_TO_APPLY | REVIEW_REQUIRED | APPLYING
    # WAITING_FOR_USER | OTP_REQUIRED | SUBMITTED | FAILED | SKIPPED | CANCELLED

    # Scores
    match_score = Column(Float, default=0.0)
    skill_match_score = Column(Float, default=0.0)

    # Resume
    selected_resume_id = Column(Integer, ForeignKey("candidate_resumes.id", ondelete="SET NULL"), nullable=True)

    # Control
    approval_mode = Column(String(20), default="always")  # snapshot at queueing
    rejection_reason = Column(Text, nullable=True)
    consent_ref = Column(String(255), nullable=True)      # FK UserConsent.consent_ref

    # LangGraph checkpoint for crash recovery
    checkpoint_thread_id = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    run = relationship("ApplicationRun", back_populates="tasks")
    status_history = relationship("ApplicationStatusHistory", back_populates="task", cascade="all, delete-orphan")
    audit_entries = relationship("ApplicationAudit", back_populates="task", cascade="all, delete-orphan")
    logs = relationship("ApplicationLog", back_populates="task", cascade="all, delete-orphan")
    documents = relationship("ApplicationDocument", back_populates="task", cascade="all, delete-orphan")
    cover_letters = relationship("ApplicationCoverLetter", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_at_run", "run_id"),
        Index("idx_at_candidate_status", "candidate_id", "status"),
    )


class ApplicationStatusHistory(Base):
    """
    Full audit trail of status transitions for each ApplicationTask.
    """
    __tablename__ = "application_status_history"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("application_tasks.id", ondelete="CASCADE"), nullable=False)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    reason = Column(Text, nullable=True)

    task = relationship("ApplicationTask", back_populates="status_history")

    __table_args__ = (
        Index("idx_ash_task", "task_id"),
    )


class ApplicationLog(Base):
    """
    Timestamped log lines for debugging and monitoring.
    """
    __tablename__ = "application_logs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("application_runs.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("application_tasks.id", ondelete="SET NULL"), nullable=True)
    level = Column(String(20), default="info")   # info | warning | error | success
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    task = relationship("ApplicationTask", back_populates="logs")

    __table_args__ = (
        Index("idx_al_run", "run_id"),
        Index("idx_al_task", "task_id"),
    )


class ApplicationMetrics(Base):
    """
    Aggregate counters per application run.
    """
    __tablename__ = "application_metrics"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("application_runs.id", ondelete="CASCADE"), nullable=False, unique=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)

    jobs_selected = Column(Integer, default=0)
    jobs_queued = Column(Integer, default=0)
    jobs_skipped = Column(Integer, default=0)
    jobs_rate_limited = Column(Integer, default=0)
    applications_started = Column(Integer, default=0)
    applications_submitted = Column(Integer, default=0)
    applications_failed = Column(Integer, default=0)
    otp_required = Column(Integer, default=0)
    email_verifications = Column(Integer, default=0)
    accounts_created = Column(Integer, default=0)
    review_required = Column(Integer, default=0)
    review_approved = Column(Integer, default=0)
    review_rejected = Column(Integer, default=0)
    requirements_failed = Column(Integer, default=0)
    platform_disabled_skips = Column(Integer, default=0)
    questions_answered = Column(Integer, default=0)
    cover_letters_generated = Column(Integer, default=0)
    forms_submitted = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("ApplicationRun", back_populates="metrics")

    __table_args__ = (
        Index("idx_am_candidate", "candidate_id"),
    )


# ─── Credential Vault ─────────────────────────────────────────────────────────

class ApplicationAccount(Base):
    """
    Encrypted credential store per user per platform.
    Password is NEVER stored by default — only session cookies and tokens.
    Password field is populated ONLY when the platform adapter sets requires_password_storage=True
    and the user has granted explicit consent.
    """
    __tablename__ = "application_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(100), nullable=False)        # e.g. "greenhouse", "lever", "workday"
    website = Column(String(500), nullable=True)          # base domain of the platform

    # Session-first credential storage (Fernet-encrypted)
    encrypted_cookies = Column(Text, nullable=True)        # Primary auth: serialized Playwright cookies
    encrypted_session_tokens = Column(Text, nullable=True) # OAuth / JWT tokens
    encrypted_username = Column(Text, nullable=True)       # Only if platform requires re-auth
    encrypted_password = Column(Text, nullable=True)       # NULLABLE — only for workday/taleo/oracle/sap

    # Flags
    requires_password_storage = Column(Boolean, default=False)  # Set by adapter
    session_valid_until = Column(DateTime, nullable=True)        # Cookie expiry estimate

    # Browser fingerprint isolation
    fingerprint_profile_id = Column(String(255), nullable=True)  # UUID for deterministic browser slot
    proxy_id = Column(String(255), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Consent tracking
    consent_ref = Column(String(255), nullable=True)  # FK UserConsent.consent_ref

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_aa_user_platform", "user_id", "platform"),
        UniqueConstraint("user_id", "platform", name="uq_account_user_platform"),
    )


# ─── LLM Output Cache ─────────────────────────────────────────────────────────

class ApplicationAnswer(Base):
    """
    Cached LLM-generated answers to screening questions.
    Keyed by (candidate_id, question_hash) so identical questions reuse answers.
    """
    __tablename__ = "application_answers"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("application_tasks.id", ondelete="SET NULL"), nullable=True)
    question_hash = Column(String(64), nullable=False)  # SHA-256 of normalized question text
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    provider = Column(String(50), default="gemini")  # gemini | nvidia | template
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_aqa_candidate_hash", "candidate_id", "question_hash"),
    )


class ApplicationCoverLetter(Base):
    """
    Generated cover letters — one per (candidate, task).
    Cached to avoid redundant LLM calls on retries.
    """
    __tablename__ = "application_cover_letters"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("application_tasks.id", ondelete="CASCADE"), nullable=False, unique=True)
    job_title = Column(String(500), nullable=True)
    company = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    provider = Column(String(50), default="gemini")  # gemini | nvidia | template
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("ApplicationTask", back_populates="cover_letters")

    __table_args__ = (
        Index("idx_acl_candidate", "candidate_id"),
    )


# ─── Resume Selection ──────────────────────────────────────────────────────────

class ApplicationDocument(Base):
    """
    Tracks which resume version was selected and submitted for each application task.
    Stores the LLM scoring rationale for audit purposes.
    """
    __tablename__ = "application_documents"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("application_tasks.id", ondelete="CASCADE"), nullable=False, unique=True)
    resume_id = Column(Integer, ForeignKey("candidate_resumes.id", ondelete="SET NULL"), nullable=True)
    resume_type = Column(String(20), nullable=True)      # general | swe | ai | ds | ml
    resume_score = Column(Float, default=0.0)            # LLM score for this resume vs this job
    selection_reason = Column(Text, nullable=True)       # LLM explanation
    submitted_at = Column(DateTime, nullable=True)

    task = relationship("ApplicationTask", back_populates="documents")

    __table_args__ = (
        Index("idx_ad_task", "task_id"),
    )


# ─── Compliance & Audit Trail ─────────────────────────────────────────────────

class ApplicationAudit(Base):
    """
    Structured compliance and debugging audit trail.
    Every significant action in the application lifecycle writes a record here.
    Unlike ApplicationLog (which is free-text), this is a queryable, typed record.
    """
    __tablename__ = "application_audits"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("application_tasks.id", ondelete="SET NULL"), nullable=True)
    run_id = Column(Integer, ForeignKey("application_runs.id", ondelete="SET NULL"), nullable=True)
    actor = Column(String(255), nullable=False)  # "system" | "user:{id}" | "adapter:{platform}"
    action = Column(String(100), nullable=False)
    # Defined action values:
    # TASK_QUEUED TASK_SKIPPED TASK_CANCELLED RATE_LIMITED CONSENT_CHECKED CONSENT_MISSING
    # ACCOUNT_FOUND ACCOUNT_CREATED LOGIN_SUCCESS LOGIN_FAILED VERIFICATION_DETECTED
    # OTP_SENT OTP_VERIFIED REVIEW_REQUIRED USER_APPROVED USER_REJECTED
    # REQUIREMENTS_VALIDATED REQUIREMENTS_FAILED RESUME_SELECTED RESUME_UPLOADED
    # FORM_FILLED COVER_LETTER_GENERATED QUESTION_ANSWERED APPLICATION_SUBMITTED
    # SUBMISSION_FAILED CONFIRMATION_CAPTURED CHECKPOINT_SAVED CHECKPOINT_RESTORED
    # PLATFORM_DISABLED ADAPTER_VERSION_LOGGED
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(JSON, default=dict)  # platform, url, error, note, etc.

    task = relationship("ApplicationTask", back_populates="audit_entries")

    __table_args__ = (
        Index("idx_aa_task", "task_id"),
        Index("idx_aa_run", "run_id"),
        Index("idx_aa_action", "action"),
    )


# ─── Platform Health Monitoring ───────────────────────────────────────────────

class PlatformHealth(Base):
    """
    Tracks success/failure rates per ATS platform.
    Auto-disables adapters when success_rate drops below threshold.
    """
    __tablename__ = "platform_health"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(100), nullable=False, unique=True)

    total_attempts = Column(Integer, default=0)
    total_successes = Column(Integer, default=0)
    total_failures = Column(Integer, default=0)
    success_rate = Column(Float, default=1.0)           # Recomputed after each attempt
    avg_duration_seconds = Column(Float, default=0.0)

    last_success = Column(DateTime, nullable=True)
    last_failure = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    is_disabled = Column(Boolean, default=False)
    disabled_at = Column(DateTime, nullable=True)
    disabled_reason = Column(Text, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_ph_platform", "platform"),
    )