"""
VidyaMarg AI — Job Agent API Router
All endpoints for the AI Job Agent dashboard.

Routes:
  POST /job-agent/initialize         - Create/initialize agent for candidate
  GET  /job-agent/dashboard          - Full dashboard data
  POST /job-agent/run                - Trigger agent run
  GET  /job-agent/status             - Agent + last run status
  GET  /job-agent/jobs               - Paginated job matches feed
  GET  /job-agent/jobs/{job_id}      - Single job detail
  POST /job-agent/jobs/{job_id}/react - React to a match (save/hide/like/dislike)
  GET  /job-agent/applications       - Application tracker
  POST /job-agent/applications       - Create/update application
  PATCH /job-agent/applications/{id} - Update application status
  GET  /job-agent/career-paths       - Career path intelligence
  GET  /job-agent/skill-gaps         - Skill gap analysis
  GET  /job-agent/interview-prep/{job_id} - Interview preparation
  GET  /job-agent/market-intelligence - Market intelligence
  GET  /job-agent/career-insights    - Career insights
  GET  /job-agent/notifications      - Agent notifications
  POST /job-agent/notifications/{id}/read - Mark notification read
  GET  /job-agent/analytics/timeline - Activity timeline
  PUT  /job-agent/preferences        - Update agent preferences
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Candidate, User
from app.models.job_models import (
    CandidateAgent, CandidateAgentPreferences, AgentRun, AgentAction,
    AgentNotification, Job, Company, Match, Recommendation,
    Application, ApplicationEvent, InterviewPreparation,
    SkillGapAnalysis, CareerInsight, MarketIntelligence, AnalyticsEvent,
)

router = APIRouter(prefix="/job-agent", tags=["AI Job Agent"])
logger = logging.getLogger("app.api.job_agent")


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST / RESPONSE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class AgentRunRequest(BaseModel):
    run_type: str = "full"  # full, discovery, matching, resume


class MatchReactionRequest(BaseModel):
    reaction: str  # liked, disliked, not_relevant, too_junior, too_senior, saved, hidden


class ApplicationCreateRequest(BaseModel):
    job_id: int
    status: str = "saved"
    notes: Optional[str] = None
    cover_letter: Optional[str] = None
    applied_via: Optional[str] = None


class ApplicationUpdateRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    interview_notes: Optional[str] = None
    offer_salary: Optional[float] = None
    rejection_reason: Optional[str] = None


class PreferencesUpdateRequest(BaseModel):
    auto_discover: Optional[bool] = None
    discovery_frequency_hours: Optional[int] = None
    notify_new_matches: Optional[bool] = None
    notify_application_updates: Optional[bool] = None
    notify_skill_gaps: Optional[bool] = None
    min_match_score_notify: Optional[float] = None
    excluded_companies: Optional[List[str]] = None
    excluded_keywords: Optional[List[str]] = None
    preferred_industries: Optional[List[str]] = None
    open_to_relocation: Optional[bool] = None


class AnalyticsEventRequest(BaseModel):
    event_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    properties: Optional[Dict[str, Any]] = None


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_candidate(current_user: User, db: Session) -> Candidate:
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found. Please complete your profile first.")
    return candidate


def _get_or_create_agent(candidate: Candidate, db: Session) -> CandidateAgent:
    agent = db.query(CandidateAgent).filter(CandidateAgent.candidate_id == candidate.id).first()
    if not agent:
        agent = CandidateAgent(
            candidate_id=candidate.id,
            status="active",
            next_scheduled_at=datetime.utcnow(),
        )
        db.add(agent)
        db.flush()
        db.commit()
        db.refresh(agent)

        # Create default preferences
        prefs = CandidateAgentPreferences(candidate_id=candidate.id)
        db.add(prefs)
        db.commit()

    return agent


def _job_to_dict(job: Job, match: Optional[Match] = None) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "company_name": job.company_name,
        "location": job.location,
        "city": job.city,
        "country": job.country,
        "is_remote": job.is_remote,
        "is_hybrid": job.is_hybrid,
        "role_category": job.role_category,
        "industry": job.industry,
        "seniority": job.seniority,
        "employment_type": job.employment_type,
        "required_skills": job.required_skills or [],
        "preferred_skills": job.preferred_skills or [],
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.salary_currency,
        "salary_raw": job.salary_raw,
        "experience_min_years": job.experience_min_years,
        "experience_max_years": job.experience_max_years,
        "description_summary": job.description_summary,
        "apply_url": job.apply_url,
        "job_url": job.job_url,
        "quality_score": job.quality_score,
        "trust_score": job.trust_score,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "discovered_at": job.discovered_at.isoformat() if job.discovered_at else None,
        "match": {
            "id": match.id,
            "overall_score": match.overall_score,
            "skill_score": match.skill_score,
            "experience_score": match.experience_score,
            "location_score": match.location_score,
            "match_reasons": match.match_reasons or [],
            "missing_skills": match.missing_skills or [],
            "skill_gap_severity": match.skill_gap_severity,
            "career_growth_score": match.career_growth_score,
            "status": match.status,
            "is_saved": match.is_saved,
            "is_hidden": match.is_hidden,
            "user_reaction": match.user_reaction,
            "created_at": match.created_at.isoformat() if match.created_at else None,
        } if match else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/initialize", status_code=status.HTTP_201_CREATED)
async def initialize_agent(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Initialize or re-initialize the AI Job Agent for this candidate."""
    candidate = _get_candidate(current_user, db)
    agent = _get_or_create_agent(candidate, db)

    # Trigger initial full run in background
    background_tasks.add_task(_run_agent_background, candidate.id, "full", "manual", db)

    return {
        "agent_id": agent.id,
        "status": agent.status,
        "message": "AI Job Agent initialized. First run started in background.",
        "candidate_id": candidate.id,
    }


@router.post("/run")
async def trigger_agent_run(
    request: AgentRunRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger an agent run."""
    candidate = _get_candidate(current_user, db)
    agent = _get_or_create_agent(candidate, db)

    # Check if already running
    recent_run = (
        db.query(AgentRun)
        .filter(
            AgentRun.candidate_id == candidate.id,
            AgentRun.status == "running",
        )
        .first()
    )
    if recent_run:
        return {"message": "Agent is already running", "run_id": recent_run.id}

    background_tasks.add_task(_run_agent_background, candidate.id, request.run_type, "manual", db)

    return {
        "message": f"Agent {request.run_type} run triggered",
        "candidate_id": candidate.id,
        "run_type": request.run_type,
    }


def _run_agent_background(candidate_id: int, run_type: str, trigger: str, db: Session):
    """Background task to run the career supervisor pipeline."""
    try:
        from app.core.database import SessionLocal
        with SessionLocal() as bg_db:
            from app.agents.career_supervisor import career_supervisor
            career_supervisor.run(
                db=bg_db,
                candidate_id=candidate_id,
                run_type=run_type,
                trigger=trigger,
            )
    except Exception as e:
        logger.error(f"Background agent run failed for candidate {candidate_id}: {e}", exc_info=True)


@router.get("/status")
def get_agent_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get agent status and last run summary."""
    candidate = _get_candidate(current_user, db)
    agent = db.query(CandidateAgent).filter(CandidateAgent.candidate_id == candidate.id).first()

    if not agent:
        return {
            "initialized": False,
            "status": "not_initialized",
            "message": "Call POST /job-agent/initialize to start your AI Job Agent",
        }

    last_run = (
        db.query(AgentRun)
        .filter(AgentRun.agent_id == agent.id)
        .order_by(desc(AgentRun.started_at))
        .first()
    )

    unread_count = (
        db.query(AgentNotification)
        .filter(AgentNotification.candidate_id == candidate.id, AgentNotification.is_read == False)
        .count()
    )

    total_matches = (
        db.query(Match)
        .filter(Match.candidate_id == candidate.id, Match.is_hidden == False)
        .count()
    )

    return {
        "initialized": True,
        "agent_id": agent.id,
        "status": agent.status,
        "total_jobs_discovered": agent.total_jobs_discovered or 0,
        "total_jobs_matched": agent.total_jobs_matched or 0,
        "total_applications": agent.total_applications or 0,
        "last_discovery_at": agent.last_discovery_at.isoformat() if agent.last_discovery_at else None,
        "last_match_at": agent.last_match_at.isoformat() if agent.last_match_at else None,
        "next_scheduled_at": agent.next_scheduled_at.isoformat() if agent.next_scheduled_at else None,
        "unread_notifications": unread_count,
        "total_active_matches": total_matches,
        "last_run": {
            "id": last_run.id,
            "status": last_run.status,
            "run_type": last_run.run_type,
            "trigger": last_run.trigger,
            "jobs_discovered": last_run.jobs_discovered,
            "jobs_matched": last_run.jobs_matched,
            "execution_time_ms": last_run.execution_time_ms,
            "started_at": last_run.started_at.isoformat() if last_run.started_at else None,
            "completed_at": last_run.completed_at.isoformat() if last_run.completed_at else None,
            "error": last_run.error_message,
        } if last_run else None,
    }


@router.get("/dashboard")
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full dashboard data — single endpoint for the job agent page."""
    candidate = _get_candidate(current_user, db)
    agent = _get_or_create_agent(candidate, db)

    # Top matches
    top_matches_query = (
        db.query(Match, Job)
        .join(Job, Match.job_id == Job.id)
        .filter(
            Match.candidate_id == candidate.id,
            Match.is_hidden == False,
            Job.is_active == True,
        )
        .order_by(desc(Match.overall_score))
        .limit(10)
        .all()
    )
    top_matches = [_job_to_dict(job, match) for match, job in top_matches_query]

    # Applications by status
    apps_by_status: Dict[str, int] = {}
    apps = db.query(Application.status, Application.id).filter(Application.candidate_id == candidate.id).all()
    for s, _ in apps:
        apps_by_status[s] = apps_by_status.get(s, 0) + 1

    # Skill gap summary
    skill_gap = db.query(SkillGapAnalysis).filter(
        SkillGapAnalysis.candidate_id == candidate.id,
        SkillGapAnalysis.analysis_type == "overall",
    ).first()

    # Career insights (latest 4)
    insights = (
        db.query(CareerInsight)
        .filter(CareerInsight.candidate_id == candidate.id)
        .order_by(desc(CareerInsight.created_at))
        .limit(4)
        .all()
    )

    # Unread notifications
    notifications = (
        db.query(AgentNotification)
        .filter(AgentNotification.candidate_id == candidate.id, AgentNotification.is_read == False)
        .order_by(desc(AgentNotification.created_at))
        .limit(5)
        .all()
    )

    # Last run
    last_run = (
        db.query(AgentRun)
        .filter(AgentRun.agent_id == agent.id)
        .order_by(desc(AgentRun.started_at))
        .first()
    )

    # Total match count
    total_matches = (
        db.query(Match)
        .filter(Match.candidate_id == candidate.id, Match.is_hidden == False)
        .count()
    )
    new_matches = (
        db.query(Match)
        .filter(Match.candidate_id == candidate.id, Match.status == "new", Match.is_hidden == False)
        .count()
    )

    return {
        "agent": {
            "id": agent.id,
            "status": agent.status,
            "career_dna": agent.career_dna or {},
            "skill_graph": agent.skill_graph or {},
            "career_graph": agent.career_graph or {},
            "target_roles": agent.target_roles or [],
            "total_jobs_discovered": agent.total_jobs_discovered or 0,
            "total_jobs_matched": agent.total_jobs_matched or 0,
            "total_applications": agent.total_applications or 0,
            "last_discovery_at": agent.last_discovery_at.isoformat() if agent.last_discovery_at else None,
        },
        "top_matches": top_matches,
        "total_matches": total_matches,
        "new_matches": new_matches,
        "applications_summary": apps_by_status,
        "total_applications": sum(apps_by_status.values()),
        "skill_gap": {
            "overall_gap_score": skill_gap.overall_gap_score if skill_gap else None,
            "missing_skills": skill_gap.missing_skills[:10] if skill_gap else [],
            "estimated_upskill_months": skill_gap.estimated_upskill_months if skill_gap else None,
        } if skill_gap else None,
        "career_insights": [
            {
                "id": i.id,
                "category": i.insight_category,
                "title": i.title,
                "content": i.content,
                "is_positive": i.is_positive,
                "actionable_steps": i.actionable_steps or [],
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in insights
        ],
        "notifications": [
            {
                "id": n.id,
                "type": n.notification_type,
                "title": n.title,
                "body": n.body,
                "priority": n.priority,
                "action_url": n.action_url,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ],
        "last_run": {
            "status": last_run.status,
            "run_type": last_run.run_type,
            "jobs_discovered": last_run.jobs_discovered,
            "jobs_matched": last_run.jobs_matched,
            "started_at": last_run.started_at.isoformat() if last_run.started_at else None,
        } if last_run else None,
    }


@router.get("/jobs")
def get_job_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    min_score: float = Query(0.0, ge=0, le=100),
    seniority: Optional[str] = Query(None),
    is_remote: Optional[bool] = Query(None),
    status_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Paginated job match feed for the candidate."""
    candidate = _get_candidate(current_user, db)

    query = (
        db.query(Match, Job)
        .join(Job, Match.job_id == Job.id)
        .filter(
            Match.candidate_id == candidate.id,
            Match.is_hidden == False,
            Match.overall_score >= min_score,
            Job.is_active == True,
        )
    )

    if is_remote is not None:
        query = query.filter(Job.is_remote == is_remote)
    if seniority:
        query = query.filter(Job.seniority == seniority)
    if status_filter:
        query = query.filter(Match.status == status_filter)

    total = query.count()
    results = (
        query.order_by(desc(Match.overall_score))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "jobs": [_job_to_dict(job, match) for match, job in results],
    }


@router.get("/jobs/{job_id}")
def get_job_detail(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full job detail with match scores and description."""
    candidate = _get_candidate(current_user, db)
    job = db.query(Job).filter(Job.id == job_id, Job.is_active == True).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    match = db.query(Match).filter(
        Match.candidate_id == candidate.id, Match.job_id == job_id
    ).first()

    # Mark as seen
    if match and not match.is_seen:
        match.is_seen = True
        match.seen_at = datetime.utcnow()
        if match.status == "new":
            match.status = "viewed"
        db.commit()

    # Log analytics
    try:
        ev = AnalyticsEvent(
            candidate_id=candidate.id,
            event_type="job_viewed",
            entity_type="job",
            entity_id=job_id,
        )
        db.add(ev)
        db.commit()
    except Exception:
        pass

    result = _job_to_dict(job, match)
    result["description"] = job.description or ""

    # Check if application exists
    app = db.query(Application).filter(
        Application.candidate_id == candidate.id,
        Application.job_id == job_id,
    ).first()
    result["application"] = {
        "id": app.id,
        "status": app.status,
        "applied_at": app.applied_at.isoformat() if app.applied_at else None,
    } if app else None

    # Interview prep available?
    prep = db.query(InterviewPreparation).filter(
        InterviewPreparation.candidate_id == candidate.id,
        InterviewPreparation.job_id == job_id,
    ).first()
    result["has_interview_prep"] = prep is not None

    return result


@router.post("/jobs/{job_id}/react")
def react_to_match(
    job_id: int,
    request: MatchReactionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """React to a job match — save, hide, like, dislike."""
    candidate = _get_candidate(current_user, db)
    match = db.query(Match).filter(
        Match.candidate_id == candidate.id, Match.job_id == job_id
    ).first()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    reaction = request.reaction
    match.user_reaction = reaction

    if reaction == "saved":
        match.is_saved = True
        match.saved_at = datetime.utcnow()
        match.status = "saved"
    elif reaction == "hidden":
        match.is_hidden = True
        match.status = "hidden"
    elif reaction in ("liked", "disliked", "not_relevant", "too_junior", "too_senior"):
        match.user_reaction = reaction

    db.commit()

    # Log analytics
    try:
        ev = AnalyticsEvent(
            candidate_id=candidate.id,
            event_type=f"job_{reaction}",
            entity_type="job",
            entity_id=job_id,
            properties={"reaction": reaction, "match_score": match.overall_score},
        )
        db.add(ev)
        db.commit()
    except Exception:
        pass

    return {"message": "Reaction recorded", "job_id": job_id, "reaction": reaction}


@router.get("/applications")
def get_applications(
    status_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Application tracker — all applications grouped by status."""
    candidate = _get_candidate(current_user, db)

    query = (
        db.query(Application, Job)
        .join(Job, Application.job_id == Job.id)
        .filter(Application.candidate_id == candidate.id)
    )
    if status_filter:
        query = query.filter(Application.status == status_filter)

    results = query.order_by(desc(Application.updated_at)).all()

    applications = []
    for app, job in results:
        applications.append({
            "id": app.id,
            "job_id": app.job_id,
            "status": app.status,
            "job_title": job.title,
            "company_name": job.company_name,
            "location": job.location,
            "is_remote": job.is_remote,
            "apply_url": job.apply_url,
            "applied_via": app.applied_via,
            "notes": app.notes,
            "interview_rounds": app.interview_rounds,
            "offer_salary": app.offer_salary,
            "saved_at": app.saved_at.isoformat() if app.saved_at else None,
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "first_interview_at": app.first_interview_at.isoformat() if app.first_interview_at else None,
            "offer_received_at": app.offer_received_at.isoformat() if app.offer_received_at else None,
            "rejected_at": app.rejected_at.isoformat() if app.rejected_at else None,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
        })

    # Kanban summary
    summary: Dict[str, int] = {}
    for app_data in applications:
        s = app_data["status"]
        summary[s] = summary.get(s, 0) + 1

    return {"applications": applications, "summary": summary, "total": len(applications)}


@router.post("/applications", status_code=status.HTTP_201_CREATED)
def create_application(
    request: ApplicationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update an application record."""
    candidate = _get_candidate(current_user, db)
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = db.query(Application).filter(
        Application.candidate_id == candidate.id,
        Application.job_id == request.job_id,
    ).first()

    now = datetime.utcnow()
    if existing:
        if request.status:
            existing.status = request.status
        if request.notes:
            existing.notes = request.notes
        if request.cover_letter:
            existing.cover_letter = request.cover_letter
        if request.status == "applied" and not existing.applied_at:
            existing.applied_at = now
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        return {"id": existing.id, "status": existing.status, "message": "Application updated"}

    # Create new
    match = db.query(Match).filter(
        Match.candidate_id == candidate.id, Match.job_id == request.job_id
    ).first()

    app = Application(
        candidate_id=candidate.id,
        job_id=request.job_id,
        match_id=match.id if match else None,
        status=request.status,
        notes=request.notes,
        cover_letter=request.cover_letter,
        applied_via=request.applied_via,
        saved_at=now if request.status == "saved" else None,
        applied_at=now if request.status == "applied" else None,
    )
    db.add(app)
    db.flush()

    # Log event
    event = ApplicationEvent(
        application_id=app.id,
        candidate_id=candidate.id,
        event_type="status_changed",
        from_status=None,
        to_status=request.status,
        actor="user",
    )
    db.add(event)

    # Update match status
    if match:
        match.status = request.status if request.status in ("saved", "applied") else match.status
        if request.status == "saved":
            match.is_saved = True

    # Update agent totals
    agent = db.query(CandidateAgent).filter(CandidateAgent.candidate_id == candidate.id).first()
    if agent:
        agent.total_applications = (agent.total_applications or 0) + 1

    db.commit()
    db.refresh(app)

    return {"id": app.id, "status": app.status, "message": "Application created"}


@router.patch("/applications/{app_id}")
def update_application(
    app_id: int,
    request: ApplicationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update application status (Kanban move)."""
    candidate = _get_candidate(current_user, db)
    app = db.query(Application).filter(
        Application.id == app_id, Application.candidate_id == candidate.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    old_status = app.status
    now = datetime.utcnow()

    if request.status and request.status != old_status:
        app.status = request.status
        # Set status-specific timestamps
        status_timestamps = {
            "applied": "applied_at",
            "shortlisted": "shortlisted_at",
            "interview_scheduled": "first_interview_at",
            "offer_received": "offer_received_at",
            "rejected": "rejected_at",
            "withdrawn": "withdrawn_at",
        }
        ts_field = status_timestamps.get(request.status)
        if ts_field and not getattr(app, ts_field):
            setattr(app, ts_field, now)

        # Log event
        event = ApplicationEvent(
            application_id=app.id,
            candidate_id=candidate.id,
            event_type="status_changed",
            from_status=old_status,
            to_status=request.status,
            actor="user",
        )
        db.add(event)

    if request.notes is not None:
        app.notes = request.notes
    if request.interview_notes is not None:
        app.interview_notes = request.interview_notes
    if request.offer_salary is not None:
        app.offer_salary = request.offer_salary
    if request.rejection_reason is not None:
        app.rejection_reason = request.rejection_reason

    app.updated_at = now
    db.commit()

    return {"id": app.id, "status": app.status, "message": "Application updated"}


@router.get("/career-paths")
def get_career_paths(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Career path trajectories generated by Career Agent."""
    candidate = _get_candidate(current_user, db)
    agent = db.query(CandidateAgent).filter(CandidateAgent.candidate_id == candidate.id).first()

    if not agent:
        return {"career_paths": [], "career_dna": {}, "target_roles": []}

    return {
        "career_paths": (agent.career_graph or {}).get("paths", []),
        "career_dna": agent.career_dna or {},
        "skill_graph": agent.skill_graph or {},
        "target_roles": agent.target_roles or [],
        "industry_dna": agent.industry_dna or {},
    }


@router.get("/skill-gaps")
def get_skill_gaps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Skill gap analysis with learning roadmap."""
    candidate = _get_candidate(current_user, db)
    gap = db.query(SkillGapAnalysis).filter(
        SkillGapAnalysis.candidate_id == candidate.id,
        SkillGapAnalysis.analysis_type == "overall",
    ).first()

    if not gap:
        return {"gap_available": False, "message": "Skill gap analysis not yet generated. Trigger an agent run first."}

    return {
        "gap_available": True,
        "overall_gap_score": gap.overall_gap_score,
        "current_skills": gap.current_skills or [],
        "missing_skills": gap.missing_skills or [],
        "skill_scores": gap.skill_scores or {},
        "learning_roadmap": gap.learning_roadmap or [],
        "estimated_upskill_months": gap.estimated_upskill_months,
        "version": gap.version,
        "updated_at": gap.updated_at.isoformat() if gap.updated_at else None,
    }


@router.get("/interview-prep/{job_id}")
async def get_interview_prep(
    job_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get or generate interview preparation for a specific job."""
    candidate = _get_candidate(current_user, db)
    job = db.query(Job).filter(Job.id == job_id, Job.is_active == True).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    prep = db.query(InterviewPreparation).filter(
        InterviewPreparation.candidate_id == candidate.id,
        InterviewPreparation.job_id == job_id,
    ).first()

    if not prep:
        # Generate on demand
        background_tasks.add_task(_generate_interview_prep_background, candidate.id, job_id, db)
        return {
            "status": "generating",
            "message": "Interview preparation is being generated. Please check back in 30 seconds.",
            "job_title": job.title,
            "company_name": job.company_name,
        }

    return {
        "status": "ready",
        "job_id": job_id,
        "job_title": job.title,
        "company_name": job.company_name,
        "company_analysis": prep.company_analysis or {},
        "technical_questions": prep.technical_questions or [],
        "hr_questions": prep.hr_questions or [],
        "behavioral_questions": prep.behavioral_questions or [],
        "culture_fit_questions": prep.culture_fit_questions or [],
        "study_topics": prep.study_topics or [],
        "estimated_prep_hours": prep.estimated_prep_hours,
        "difficulty_level": prep.difficulty_level,
        "version": prep.version,
        "created_at": prep.created_at.isoformat() if prep.created_at else None,
    }


def _generate_interview_prep_background(candidate_id: int, job_id: int, db: Session):
    """Generate interview prep in background."""
    try:
        from app.core.database import SessionLocal
        with SessionLocal() as bg_db:
            from app.agents.career_supervisor import InterviewAgent, _default_state
            from app.models.models import CandidateProfile

            candidate = bg_db.query(Candidate).filter(Candidate.id == candidate_id).first()
            profile_obj = bg_db.query(CandidateProfile).filter(
                CandidateProfile.candidate_id == candidate_id
            ).order_by(CandidateProfile.created_at.desc()).first()

            profile = {}
            if profile_obj and profile_obj.parsed_metadata:
                try:
                    import json
                    profile = json.loads(profile_obj.parsed_metadata) if isinstance(profile_obj.parsed_metadata, str) else profile_obj.parsed_metadata
                except Exception:
                    pass

            agent = db.query(CandidateAgent).filter(CandidateAgent.candidate_id == candidate_id).first()
            if not agent:
                return

            state = _default_state(candidate_id, agent.id, 0, "interview", "manual")
            state["candidate_profile"] = profile
            state["matches"] = [{"job_id": job_id, "overall_score": 80.0, "missing_skills": []}]

            interview_agent = InterviewAgent()
            interview_agent.run(state, bg_db)
    except Exception as e:
        logger.error(f"Background interview prep generation failed: {e}", exc_info=True)


@router.get("/market-intelligence")
def get_market_intelligence(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Market intelligence for the candidate's domain."""
    candidate = _get_candidate(current_user, db)

    # Get career insights (market category)
    market_insights = (
        db.query(CareerInsight)
        .filter(
            CareerInsight.candidate_id == candidate.id,
            CareerInsight.insight_category.in_(["market_demand", "salary_trend", "opportunity"])
        )
        .order_by(desc(CareerInsight.created_at))
        .limit(5)
        .all()
    )

    # Get agent career dna for domain context
    agent = db.query(CandidateAgent).filter(CandidateAgent.candidate_id == candidate.id).first()
    career_dna = agent.career_dna if agent else {}

    return {
        "insights": [
            {
                "id": i.id,
                "category": i.insight_category,
                "title": i.title,
                "content": i.content,
                "is_positive": i.is_positive,
                "data": i.data or {},
                "actionable_steps": i.actionable_steps or [],
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in market_insights
        ],
        "career_dna": career_dna,
        "domain": (career_dna or {}).get("domain_expertise", ""),
    }


@router.get("/career-insights")
def get_career_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """All career insights for the candidate."""
    candidate = _get_candidate(current_user, db)
    insights = (
        db.query(CareerInsight)
        .filter(CareerInsight.candidate_id == candidate.id)
        .order_by(desc(CareerInsight.created_at))
        .limit(10)
        .all()
    )

    return {
        "insights": [
            {
                "id": i.id,
                "category": i.insight_category,
                "title": i.title,
                "content": i.content,
                "is_positive": i.is_positive,
                "confidence": i.confidence,
                "actionable_steps": i.actionable_steps or [],
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in insights
        ]
    }


@router.get("/notifications")
def get_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get agent notifications."""
    candidate = _get_candidate(current_user, db)
    query = db.query(AgentNotification).filter(AgentNotification.candidate_id == candidate.id)
    if unread_only:
        query = query.filter(AgentNotification.is_read == False)

    notifications = query.order_by(desc(AgentNotification.created_at)).limit(limit).all()

    return {
        "notifications": [
            {
                "id": n.id,
                "type": n.notification_type,
                "title": n.title,
                "body": n.body,
                "priority": n.priority,
                "action_url": n.action_url,
                "is_read": n.is_read,
                "read_at": n.read_at.isoformat() if n.read_at else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ],
        "unread_count": sum(1 for n in notifications if not n.is_read),
    }


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a notification as read."""
    candidate = _get_candidate(current_user, db)
    notification = db.query(AgentNotification).filter(
        AgentNotification.id == notification_id,
        AgentNotification.candidate_id == candidate.id,
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    return {"message": "Marked as read"}


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read."""
    candidate = _get_candidate(current_user, db)
    db.query(AgentNotification).filter(
        AgentNotification.candidate_id == candidate.id,
        AgentNotification.is_read == False,
    ).update({"is_read": True, "read_at": datetime.utcnow()})
    db.commit()
    return {"message": "All notifications marked as read"}


@router.get("/analytics/timeline")
def get_activity_timeline(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Activity timeline for the candidate."""
    candidate = _get_candidate(current_user, db)
    since = datetime.utcnow() - timedelta(days=days)

    events = (
        db.query(AnalyticsEvent)
        .filter(AnalyticsEvent.candidate_id == candidate.id, AnalyticsEvent.created_at >= since)
        .order_by(desc(AnalyticsEvent.created_at))
        .limit(100)
        .all()
    )

    return {
        "timeline": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "properties": e.properties or {},
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]
    }


@router.put("/preferences")
def update_preferences(
    request: PreferencesUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update agent preferences."""
    candidate = _get_candidate(current_user, db)
    prefs = db.query(CandidateAgentPreferences).filter(
        CandidateAgentPreferences.candidate_id == candidate.id
    ).first()

    if not prefs:
        prefs = CandidateAgentPreferences(candidate_id=candidate.id)
        db.add(prefs)
        db.flush()

    update_fields = request.dict(exclude_none=True)
    for field, value in update_fields.items():
        if hasattr(prefs, field):
            setattr(prefs, field, value)

    prefs.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Preferences updated"}


@router.post("/analytics/event")
def track_event(
    request: AnalyticsEventRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Track a frontend analytics event."""
    candidate = _get_candidate(current_user, db)
    ev = AnalyticsEvent(
        candidate_id=candidate.id,
        event_type=request.event_type,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        properties=request.properties or {},
    )
    db.add(ev)
    db.commit()
    return {"tracked": True}
