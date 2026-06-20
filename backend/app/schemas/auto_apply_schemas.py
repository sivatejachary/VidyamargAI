"""
Auto Apply — Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ─── Task Schemas ─────────────────────────────────────────────────────────────

class ApplicationTaskResponse(BaseModel):
    id: int
    run_id: int
    job_title: str
    company: str
    apply_url: str
    platform: str
    adapter_version: Optional[str] = None
    status: str
    match_score: float
    skill_match_score: float
    approval_mode: str
    rejection_reason: Optional[str] = None
    checkpoint_thread_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApplicationTaskDetailResponse(ApplicationTaskResponse):
    """Extended task detail with history."""
    status_history: List[dict] = Field(default_factory=list)
    audit_entries: List[dict] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ─── Run Schemas ──────────────────────────────────────────────────────────────

class ApplicationRunResponse(BaseModel):
    id: int
    candidate_id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    stats: Optional[dict] = None
    tasks: List[ApplicationTaskResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class TriggerRunResponse(BaseModel):
    run_id: int
    status: str
    message: str


# ─── Metrics Schemas ──────────────────────────────────────────────────────────

class ApplicationMetricsResponse(BaseModel):
    run_id: int
    jobs_queued: int = 0
    jobs_skipped: int = 0
    jobs_rate_limited: int = 0
    applications_started: int = 0
    applications_submitted: int = 0
    applications_failed: int = 0
    otp_required: int = 0
    review_required: int = 0
    review_approved: int = 0
    review_rejected: int = 0
    requirements_failed: int = 0
    cover_letters_generated: int = 0
    questions_answered: int = 0

    class Config:
        from_attributes = True


# ─── Rules Schemas ────────────────────────────────────────────────────────────

class AutoApplyRulesRequest(BaseModel):
    auto_apply_enabled: Optional[bool] = None
    auto_apply_approval_mode: Optional[str] = Field(
        None, description="auto | always | new_company"
    )
    auto_apply_min_score: Optional[float] = Field(None, ge=0, le=100)
    auto_apply_min_skill_match: Optional[float] = Field(None, ge=0, le=100)
    auto_apply_daily_cap: Optional[int] = Field(None, ge=1, le=500)
    auto_apply_remote_only: Optional[bool] = None
    auto_apply_max_job_age_days: Optional[int] = Field(None, ge=1, le=30)
    auto_apply_locations: Optional[List[str]] = None
    auto_apply_domains: Optional[List[str]] = None


class AutoApplyRulesResponse(BaseModel):
    auto_apply_enabled: bool = False
    auto_apply_approval_mode: str = "always"
    auto_apply_min_score: float = 80.0
    auto_apply_min_skill_match: float = 70.0
    auto_apply_daily_cap: int = 50
    auto_apply_remote_only: bool = False
    auto_apply_max_job_age_days: int = 2
    auto_apply_locations: List[str] = Field(default_factory=list)
    auto_apply_domains: List[str] = Field(default_factory=list)


# ─── Account Schemas ──────────────────────────────────────────────────────────

class ApplicationAccountResponse(BaseModel):
    """Credentials are ALWAYS redacted — never exposed via API."""
    id: int
    platform: str
    website: Optional[str] = None
    requires_password_storage: bool
    session_valid_until: Optional[datetime] = None
    fingerprint_profile_id: Optional[str] = None
    # All encrypted_* fields are intentionally OMITTED
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Audit Schemas ────────────────────────────────────────────────────────────

class ApplicationAuditResponse(BaseModel):
    id: int
    task_id: Optional[int] = None
    run_id: Optional[int] = None
    actor: str
    action: str
    timestamp: datetime
    details: Optional[dict] = None

    class Config:
        from_attributes = True


# ─── Platform Health Schemas ──────────────────────────────────────────────────

class PlatformHealthResponse(BaseModel):
    platform: str
    total_attempts: int
    total_successes: int
    total_failures: int
    success_rate: float
    avg_duration_seconds: float
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_error: Optional[str] = None
    is_disabled: bool
    disabled_at: Optional[datetime] = None
    disabled_reason: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Consent Schemas ──────────────────────────────────────────────────────────

class ConsentRequest(BaseModel):
    metadata: Optional[dict] = None


class ConsentResponse(BaseModel):
    consent_type: str
    granted: bool
    granted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Cover Letter & Answer Schemas ────────────────────────────────────────────

class CoverLetterResponse(BaseModel):
    id: int
    task_id: int
    job_title: Optional[str] = None
    company: Optional[str] = None
    content: str
    provider: str
    created_at: datetime

    class Config:
        from_attributes = True


class ScreeningAnswerResponse(BaseModel):
    id: int
    question_text: str
    answer_text: str
    provider: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Runs + Tasks Combined (for frontend polling) ─────────────────────────────

class AutoApplyDashboardResponse(BaseModel):
    """Combined response for the frontend Auto Apply tab polling endpoint."""
    run_id: Optional[int] = None
    tasks: List[ApplicationTaskResponse] = Field(default_factory=list)
    metrics: ApplicationMetricsResponse = Field(
        default_factory=lambda: ApplicationMetricsResponse(run_id=0)
    )