"""
VidyaMarg AI — Job Discovery Domain Models
==========================================
Pure Python dataclasses representing core domain entities.
Zero framework dependencies — these are the canonical truth objects.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class JobLifecycle(str, Enum):
    DISCOVERED = "discovered"
    NORMALIZED = "normalized"
    VALIDATED = "validated"
    DEDUPLICATED = "deduplicated"
    ENRICHED = "enriched"
    PERSISTED = "persisted"
    EMBEDDED = "embedded"
    MATCHED = "matched"
    RECOMMENDED = "recommended"
    NOTIFIED = "notified"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class ConnectorStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    OFFLINE = "offline"
    CIRCUIT_OPEN = "circuit_open"


class MatchStatus(str, Enum):
    NEW = "new"
    VIEWED = "viewed"
    SAVED = "saved"
    APPLIED = "applied"
    HIDDEN = "hidden"
    EXPIRED = "expired"


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"


class WorkMode(str, Enum):
    REMOTE = "remote"
    ONSITE = "onsite"
    HYBRID = "hybrid"


class Seniority(str, Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"
    DIRECTOR = "director"
    VP = "vp"
    CXO = "cxo"


# ---------------------------------------------------------------------------
# Domain Entities
# ---------------------------------------------------------------------------

@dataclass
class RawJob:
    """
    Represents a job payload as received directly from a connector.
    This is the input to the normalization pipeline.
    """
    external_id: str
    source_name: str
    title: str
    company_name: str
    description: str = ""
    apply_url: str = ""
    job_url: str = ""
    location: str = ""
    city: str = ""
    state: str = ""
    country: str = "IN"
    is_remote: bool = False
    salary_raw: str = ""
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "INR"
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    posted_at: Optional[datetime] = None
    raw_payload: Dict[str, Any] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in vars(self).items()}


@dataclass
class NormalizedJob:
    """
    A job that has passed through the normalization pipeline.
    Schema is now canonical and ready for validation.
    """
    external_id: str
    source_name: str
    title: str
    title_normalized: str
    company_name: str
    company_normalized: str
    description: str
    description_summary: str = ""
    apply_url: str = ""
    job_url: str = ""
    location: str = ""
    city: str = ""
    state: str = ""
    country: str = "IN"
    is_remote: bool = False
    is_hybrid: bool = False
    work_mode: WorkMode = WorkMode.ONSITE
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    seniority: Seniority = Seniority.MID
    role_category: str = ""
    role_sub_category: str = ""
    industry: str = ""
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "INR"
    salary_period: str = "yearly"
    salary_raw: str = ""
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    posted_at: Optional[datetime] = None
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    lifecycle_status: JobLifecycle = JobLifecycle.NORMALIZED

    def to_dict(self) -> Dict[str, Any]:
        d = vars(self).copy()
        d["work_mode"] = self.work_mode.value
        d["employment_type"] = self.employment_type.value
        d["seniority"] = self.seniority.value
        d["lifecycle_status"] = self.lifecycle_status.value
        d["posted_at"] = self.posted_at.isoformat() if self.posted_at else None
        d["discovered_at"] = self.discovered_at.isoformat()
        return d


@dataclass
class ValidatedJob(NormalizedJob):
    """A job that has passed all validation checks."""
    trust_score: float = 0.5
    quality_score: float = 0.5
    spam_score: float = 0.0
    validation_errors: List[str] = field(default_factory=list)
    is_valid: bool = True


@dataclass
class EnrichedJob(ValidatedJob):
    """A job enriched with AI-generated metadata and scores."""
    skill_graph: Dict[str, float] = field(default_factory=dict)  # {skill: relevance_weight}
    freshness_score: float = 1.0
    lifecycle_status: JobLifecycle = JobLifecycle.ENRICHED


@dataclass
class PersistedJob:
    """Reference returned after a job has been committed to PostgreSQL."""
    id: int
    external_id: str
    source_name: str
    company_id: int
    embedding_id: Optional[str] = None
    lifecycle_status: JobLifecycle = JobLifecycle.PERSISTED
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Company:
    """Enriched company entity resolved from job postings."""
    id: Optional[int] = None
    name: str = ""
    normalized_name: str = ""
    domain: str = ""
    industry: str = ""
    trust_score: float = 0.5
    is_verified: bool = False
    is_blacklisted: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidatePreference:
    """Candidate job preference profile used by matching engine."""
    candidate_id: int
    target_roles: List[str] = field(default_factory=list)
    required_skills: List[str] = field(default_factory=list)
    target_locations: List[str] = field(default_factory=list)
    target_salary_min: Optional[float] = None
    target_salary_max: Optional[float] = None
    target_salary_currency: str = "INR"
    work_mode_preference: WorkMode = WorkMode.REMOTE
    employment_type_preference: EmploymentType = EmploymentType.FULL_TIME
    experience_years: Optional[float] = None
    preferred_companies: List[str] = field(default_factory=list)
    excluded_companies: List[str] = field(default_factory=list)
    min_match_score: float = 60.0


@dataclass
class JobMatch:
    """Computed match between a candidate and a job."""
    match_id: Optional[int] = None
    candidate_id: int = 0
    job_id: int = 0
    overall_score: float = 0.0
    semantic_score: float = 0.0
    skill_score: float = 0.0
    experience_score: float = 0.0
    salary_score: float = 0.0
    location_score: float = 0.0
    remote_preference_score: float = 0.0
    company_preference_score: float = 0.0
    freshness_score: float = 0.0
    match_reasons: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    skill_gap_severity: str = "none"  # none | minor | moderate | major
    match_explanation: str = ""
    status: MatchStatus = MatchStatus.NEW
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Recommendation:
    """AI-generated recommendation linking a candidate to a job."""
    id: Optional[int] = None
    candidate_id: int = 0
    match_id: Optional[int] = None
    job_id: int = 0
    score: float = 0.0
    reason: str = ""
    is_seen: bool = False
    is_actioned: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConnectorHealthReport:
    """Health status snapshot from a single connector."""
    source_name: str
    status: ConnectorStatus
    latency_ms: Optional[int] = None
    jobs_found: int = 0
    error_details: Optional[str] = None
    checked_at: datetime = field(default_factory=datetime.utcnow)
