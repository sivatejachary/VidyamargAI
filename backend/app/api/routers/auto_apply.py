"""
Auto Apply API Router — endpoints for the Enterprise Auto Apply Agent.
"""
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auto_apply_schemas import (
    ApplicationRunResponse, ApplicationTaskResponse, ApplicationTaskDetailResponse,
    ApplicationMetricsResponse, AutoApplyRulesRequest, AutoApplyRulesResponse,
    ApplicationAccountResponse, ApplicationAuditResponse, PlatformHealthResponse,
    ConsentRequest, ConsentResponse, CoverLetterResponse, ScreeningAnswerResponse,
    TriggerRunResponse, AutoApplyDashboardResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auto-apply", tags=["Auto Apply"])


def _get_candidate_id(current_user, db: Session) -> int:
    """Resolve candidate_id from the current user."""
    from app.models.models import Candidate
    candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")
    return candidate.id


# ─── Run Control ─────────────────────────────────────────────────────────────

async def run_auto_apply_agent_background(run_id: int, candidate_id: int):
    """Background task to initialize and execute the AutoApplyAgent flow."""
    from app.core.database import SessionLocal
    from app.agents.auto_apply_agent import AutoApplyAgent
    
    db_session = SessionLocal()
    try:
        agent = AutoApplyAgent(db_session, candidate_id)
        await agent.execute_run_flow(run_id)
    except Exception as e:
        logger.error(f"Background AutoApplyAgent run {run_id} failed: {e}")
    finally:
        db_session.close()


@router.post("/run", response_model=TriggerRunResponse)
async def trigger_auto_apply_run(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Trigger a new Auto Apply run — queues all matched jobs for automated application."""
    from app.models.auto_apply_models import ApplicationRun, ApplicationMetrics
    from app.services.auto_apply.consent_service import consent_service
    from app.services.auto_apply.audit_service import audit_service

    candidate_id = _get_candidate_id(current_user, db)

    # Check consent
    if not consent_service.has_consent(current_user.id, "auto_apply", db):
        if not consent_service.has_consent(current_user.id, "app_submission", db):
            raise HTTPException(
                status_code=403,
                detail="auto_apply consent is required. Please grant consent first."
            )

    # Create run record
    run = ApplicationRun(candidate_id=candidate_id, status="queued")
    db.add(run)
    db.commit()
    db.refresh(run)

    # Create metrics record
    metrics = ApplicationMetrics(run_id=run.id, candidate_id=candidate_id)
    db.add(metrics)
    db.commit()

    audit_service.log(
        actor=f"user:{current_user.id}",
        action="TASK_QUEUED",
        db=db,
        run_id=run.id,
        details={"candidate_id": candidate_id}
    )

    # Background task launch (non-blocking)
    background_tasks.add_task(run_auto_apply_agent_background, run.id, candidate_id)
    logger.info(f"Auto Apply run {run.id} created and queued for candidate {candidate_id}")

    return TriggerRunResponse(
        run_id=run.id,
        status="queued",
        message=f"Auto Apply run #{run.id} has been queued. The agent will begin shortly."
    )


@router.get("/runs", response_model=AutoApplyDashboardResponse)
async def get_auto_apply_runs(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get the latest Auto Apply run with all tasks and metrics — used by frontend polling."""
    from app.models.auto_apply_models import ApplicationRun, ApplicationTask, ApplicationMetrics

    candidate_id = _get_candidate_id(current_user, db)

    # Get latest run
    run = db.query(ApplicationRun).filter(
        ApplicationRun.candidate_id == candidate_id
    ).order_by(ApplicationRun.started_at.desc()).first()

    if not run:
        return AutoApplyDashboardResponse()

    tasks = db.query(ApplicationTask).filter(
        ApplicationTask.run_id == run.id
    ).order_by(ApplicationTask.updated_at.desc()).all()

    metrics_rec = db.query(ApplicationMetrics).filter_by(run_id=run.id).first()
    metrics_data = ApplicationMetricsResponse(
        run_id=run.id,
        jobs_queued=metrics_rec.jobs_queued if metrics_rec else 0,
        jobs_skipped=metrics_rec.jobs_skipped if metrics_rec else 0,
        jobs_rate_limited=metrics_rec.jobs_rate_limited if metrics_rec else 0,
        applications_started=metrics_rec.applications_started if metrics_rec else 0,
        applications_submitted=metrics_rec.applications_submitted if metrics_rec else 0,
        applications_failed=metrics_rec.applications_failed if metrics_rec else 0,
        otp_required=metrics_rec.otp_required if metrics_rec else 0,
        review_required=metrics_rec.review_required if metrics_rec else 0,
        review_approved=metrics_rec.review_approved if metrics_rec else 0,
        review_rejected=metrics_rec.review_rejected if metrics_rec else 0,
        requirements_failed=metrics_rec.requirements_failed if metrics_rec else 0,
        cover_letters_generated=metrics_rec.cover_letters_generated if metrics_rec else 0,
        questions_answered=metrics_rec.questions_answered if metrics_rec else 0,
    )

    return AutoApplyDashboardResponse(
        run_id=run.id,
        tasks=[ApplicationTaskResponse.model_validate(t) for t in tasks],
        metrics=metrics_data
    )


@router.get("/runs/{run_id}", response_model=ApplicationRunResponse)
async def get_run_detail(
    run_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get detailed info for a specific run."""
    from app.models.auto_apply_models import ApplicationRun
    candidate_id = _get_candidate_id(current_user, db)
    run = db.query(ApplicationRun).filter(
        ApplicationRun.id == run_id,
        ApplicationRun.candidate_id == candidate_id
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    return run


# ─── Task Actions ─────────────────────────────────────────────────────────────

@router.post("/tasks/{task_id}/approve")
async def approve_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Approve a REVIEW_REQUIRED task — agent will proceed with application."""
    from app.models.auto_apply_models import ApplicationTask, ApplicationStatusHistory
    from app.services.auto_apply.audit_service import audit_service

    candidate_id = _get_candidate_id(current_user, db)
    task = db.query(ApplicationTask).filter(
        ApplicationTask.id == task_id,
        ApplicationTask.candidate_id == candidate_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    if task.status != "REVIEW_REQUIRED":
        raise HTTPException(status_code=400, detail=f"Task is not in REVIEW_REQUIRED state (current: {task.status}).")

    prev_status = task.status
    task.status = "APPLYING"
    db.add(ApplicationStatusHistory(
        task_id=task.id, from_status=prev_status, to_status="APPLYING", reason="User approved"
    ))
    db.commit()

    audit_service.log(
        actor=f"user:{current_user.id}", action="USER_APPROVED", db=db,
        task_id=task.id, details={"previous_status": prev_status}
    )
    return {"task_id": task_id, "status": "APPLYING", "message": "Application approved and resumed."}


@router.post("/tasks/{task_id}/reject")
async def reject_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Reject a REVIEW_REQUIRED task — application will be cancelled."""
    from app.models.auto_apply_models import ApplicationTask, ApplicationStatusHistory
    from app.services.auto_apply.audit_service import audit_service

    candidate_id = _get_candidate_id(current_user, db)
    task = db.query(ApplicationTask).filter(
        ApplicationTask.id == task_id,
        ApplicationTask.candidate_id == candidate_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    if task.status != "REVIEW_REQUIRED":
        raise HTTPException(status_code=400, detail=f"Task is not in REVIEW_REQUIRED state (current: {task.status}).")

    prev_status = task.status
    task.status = "CANCELLED"
    task.rejection_reason = "Rejected by user during review."
    db.add(ApplicationStatusHistory(
        task_id=task.id, from_status=prev_status, to_status="CANCELLED", reason="User rejected"
    ))
    db.commit()

    audit_service.log(
        actor=f"user:{current_user.id}", action="USER_REJECTED", db=db,
        task_id=task.id, details={"previous_status": prev_status}
    )
    return {"task_id": task_id, "status": "CANCELLED", "message": "Application rejected and cancelled."}


@router.post("/tasks/{task_id}/resume")
async def resume_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Resume a task paused for OTP/verification — marks OTP as verified and resumes."""
    from app.models.auto_apply_models import ApplicationTask, ApplicationStatusHistory
    from app.services.auto_apply.audit_service import audit_service

    candidate_id = _get_candidate_id(current_user, db)
    task = db.query(ApplicationTask).filter(
        ApplicationTask.id == task_id,
        ApplicationTask.candidate_id == candidate_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    if task.status not in ("WAITING_FOR_USER", "OTP_REQUIRED"):
        raise HTTPException(status_code=400, detail=f"Task cannot be resumed from state: {task.status}.")

    prev_status = task.status
    task.status = "APPLYING"
    db.add(ApplicationStatusHistory(
        task_id=task.id, from_status=prev_status, to_status="APPLYING", reason="User verified OTP/email"
    ))
    db.commit()

    audit_service.log(
        actor=f"user:{current_user.id}", action="OTP_VERIFIED", db=db,
        task_id=task.id, details={"previous_status": prev_status}
    )

    # Restore checkpoint if available
    if task.checkpoint_thread_id:
        from app.services.auto_apply.application_queue import application_queue
        application_queue.resume_from_checkpoint(task.checkpoint_thread_id)

    return {"task_id": task_id, "status": "APPLYING", "message": "Application resumed after verification."}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Cancel a queued or ready-to-apply task."""
    from app.models.auto_apply_models import ApplicationTask, ApplicationStatusHistory
    from app.services.auto_apply.audit_service import audit_service

    candidate_id = _get_candidate_id(current_user, db)
    task = db.query(ApplicationTask).filter(
        ApplicationTask.id == task_id,
        ApplicationTask.candidate_id == candidate_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    if task.status not in ("QUEUED", "READY_TO_APPLY", "RATE_LIMITED"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in state: {task.status}.")

    prev_status = task.status
    task.status = "CANCELLED"
    task.rejection_reason = "Cancelled by user."
    db.add(ApplicationStatusHistory(
        task_id=task.id, from_status=prev_status, to_status="CANCELLED", reason="User cancelled"
    ))
    db.commit()

    audit_service.log(
        actor=f"user:{current_user.id}", action="TASK_CANCELLED", db=db,
        task_id=task.id
    )
    return {"task_id": task_id, "status": "CANCELLED", "message": "Task cancelled."}


# ─── Platform Health ──────────────────────────────────────────────────────────

@router.get("/platforms/health", response_model=List[PlatformHealthResponse])
async def get_platform_health(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get health metrics for all tracked ATS platforms."""
    from app.models.auto_apply_models import PlatformHealth
    platforms = db.query(PlatformHealth).order_by(PlatformHealth.platform).all()
    return platforms


@router.post("/platforms/{platform}/enable")
async def enable_platform(
    platform: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Re-enable a disabled ATS platform adapter (admin action)."""
    from app.services.auto_apply.platform_health_service import platform_health_service
    platform_health_service.re_enable(platform, db)
    return {"platform": platform, "status": "enabled", "message": f"Platform '{platform}' re-enabled."}


# ─── Accounts ─────────────────────────────────────────────────────────────────

@router.get("/accounts", response_model=List[ApplicationAccountResponse])
async def get_platform_accounts(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """List saved platform accounts — credential fields are always redacted."""
    from app.models.auto_apply_models import ApplicationAccount
    accounts = db.query(ApplicationAccount).filter(
        ApplicationAccount.user_id == current_user.id
    ).all()
    return accounts


@router.delete("/accounts/{account_id}")
async def delete_platform_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Delete a saved platform account and all its stored credentials."""
    from app.models.auto_apply_models import ApplicationAccount
    account = db.query(ApplicationAccount).filter(
        ApplicationAccount.id == account_id,
        ApplicationAccount.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")
    db.delete(account)
    db.commit()
    return {"message": f"Platform account '{account.platform}' deleted."}


# ─── Rules ────────────────────────────────────────────────────────────────────

@router.get("/rules", response_model=AutoApplyRulesResponse)
async def get_auto_apply_rules(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get this user's auto-apply rule settings."""
    from app.models.models import UserPreference
    prefs = db.query(UserPreference).filter_by(user_id=current_user.id).first()
    if not prefs:
        return AutoApplyRulesResponse()
    locs = []
    doms = []
    try:
        locs = json.loads(getattr(prefs, "auto_apply_locations", "[]") or "[]")
    except Exception:
        pass
    try:
        doms = json.loads(getattr(prefs, "auto_apply_domains", "[]") or "[]")
    except Exception:
        pass
    return AutoApplyRulesResponse(
        auto_apply_enabled=getattr(prefs, "auto_apply_enabled", False) or False,
        auto_apply_approval_mode=getattr(prefs, "auto_apply_approval_mode", "always") or "always",
        auto_apply_min_score=getattr(prefs, "auto_apply_min_score", 80.0) or 80.0,
        auto_apply_min_skill_match=getattr(prefs, "auto_apply_min_skill_match", 70.0) or 70.0,
        auto_apply_daily_cap=getattr(prefs, "auto_apply_daily_cap", 50) or 50,
        auto_apply_remote_only=getattr(prefs, "auto_apply_remote_only", False) or False,
        auto_apply_max_job_age_days=getattr(prefs, "auto_apply_max_job_age_days", 2) or 2,
        auto_apply_locations=locs,
        auto_apply_domains=doms,
    )


@router.put("/rules", response_model=AutoApplyRulesResponse)
async def update_auto_apply_rules(
    rules: AutoApplyRulesRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Update auto-apply rule settings."""
    from app.models.models import UserPreference
    prefs = db.query(UserPreference).filter_by(user_id=current_user.id).first()
    if not prefs:
        prefs = UserPreference(user_id=current_user.id)
        db.add(prefs)
    if rules.auto_apply_enabled is not None:
        prefs.auto_apply_enabled = rules.auto_apply_enabled
    if rules.auto_apply_approval_mode is not None:
        if rules.auto_apply_approval_mode not in ("auto", "always", "new_company"):
            raise HTTPException(status_code=400, detail="approval_mode must be: auto | always | new_company")
        prefs.auto_apply_approval_mode = rules.auto_apply_approval_mode
    if rules.auto_apply_min_score is not None:
        prefs.auto_apply_min_score = rules.auto_apply_min_score
    if rules.auto_apply_min_skill_match is not None:
        prefs.auto_apply_min_skill_match = rules.auto_apply_min_skill_match
    if rules.auto_apply_daily_cap is not None:
        prefs.auto_apply_daily_cap = rules.auto_apply_daily_cap
    if rules.auto_apply_remote_only is not None:
        prefs.auto_apply_remote_only = rules.auto_apply_remote_only
    if rules.auto_apply_max_job_age_days is not None:
        prefs.auto_apply_max_job_age_days = rules.auto_apply_max_job_age_days
    if rules.auto_apply_locations is not None:
        prefs.auto_apply_locations = json.dumps(rules.auto_apply_locations)
    if rules.auto_apply_domains is not None:
        prefs.auto_apply_domains = json.dumps(rules.auto_apply_domains)
    db.commit()
    return await get_auto_apply_rules(db=db, current_user=current_user)


# ─── Consent ──────────────────────────────────────────────────────────────────

@router.post("/consent/{consent_type}/grant", response_model=ConsentResponse)
async def grant_consent(
    consent_type: str,
    body: ConsentRequest = ConsentRequest(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Grant consent for an auto-apply feature."""
    from app.services.auto_apply.consent_service import consent_service
    consent_service.grant(current_user.id, consent_type, db, metadata=body.metadata)
    from app.models.models import UserConsent
    record = db.query(UserConsent).filter(
        UserConsent.user_id == current_user.id,
        UserConsent.consent_type == consent_type
    ).first()
    return ConsentResponse(
        consent_type=consent_type,
        granted=record.granted if record else True,
        granted_at=record.granted_at if record else None
    )


@router.post("/consent/{consent_type}/revoke", response_model=ConsentResponse)
async def revoke_consent(
    consent_type: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Revoke a previously granted consent."""
    from app.services.auto_apply.consent_service import consent_service
    consent_service.revoke(current_user.id, consent_type, db)
    return ConsentResponse(consent_type=consent_type, granted=False)


@router.get("/consent", response_model=List[ConsentResponse])
async def list_consents(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """List all consent records for the current user."""
    from app.models.models import UserConsent
    records = db.query(UserConsent).filter(
        UserConsent.user_id == current_user.id
    ).all()
    return [
        ConsentResponse(
            consent_type=r.consent_type,
            granted=r.granted,
            granted_at=r.granted_at,
            revoked_at=getattr(r, "revoked_at", None)
        )
        for r in records
    ]


# ─── Audit Trail ──────────────────────────────────────────────────────────────

@router.get("/audit", response_model=List[ApplicationAuditResponse])
async def get_audit_trail(
    limit: int = 100,
    task_id: Optional[int] = None,
    run_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Query the application audit trail."""
    from app.models.auto_apply_models import ApplicationAudit
    q = db.query(ApplicationAudit)
    if task_id:
        q = q.filter(ApplicationAudit.task_id == task_id)
    if run_id:
        q = q.filter(ApplicationAudit.run_id == run_id)
    return q.order_by(ApplicationAudit.timestamp.desc()).limit(limit).all()


# ─── LLM Outputs ─────────────────────────────────────────────────────────────

@router.get("/cover-letters", response_model=List[CoverLetterResponse])
async def get_cover_letters(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Browse generated cover letters for the current candidate."""
    from app.models.auto_apply_models import ApplicationCoverLetter
    candidate_id = _get_candidate_id(current_user, db)
    letters = db.query(ApplicationCoverLetter).filter(
        ApplicationCoverLetter.candidate_id == candidate_id
    ).order_by(ApplicationCoverLetter.created_at.desc()).limit(limit).all()
    return letters


@router.get("/answers", response_model=List[ScreeningAnswerResponse])
async def get_screening_answers(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Browse cached LLM-generated screening answers."""
    from app.models.auto_apply_models import ApplicationAnswer
    candidate_id = _get_candidate_id(current_user, db)
    answers = db.query(ApplicationAnswer).filter(
        ApplicationAnswer.candidate_id == candidate_id
    ).order_by(ApplicationAnswer.created_at.desc()).limit(limit).all()
    return answers