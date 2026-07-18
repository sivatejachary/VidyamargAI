"""
HR Agent Sync Webhook Router
Receives real-time events from HR Agent AI and updates VidyamargAI candidate data.
"""
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request, Header, HTTPException, status
import hmac
import hashlib
import os
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db

async def verify_event_signature(
    request: Request,
    x_event_signature: Optional[str] = Header(None, alias="X-Event-Signature"),
    x_integration_key: Optional[str] = Header(None, alias="X-Integration-Key")
):
    secret = os.getenv("INTEGRATION_SECRET") or "nirvahai-shared-integration-secret-2026"

    if request.method == "GET":
        if x_integration_key == secret or x_event_signature == secret:
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid integration key for GET request."
        )

    if not x_event_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Event-Signature header."
        )

    body = await request.body()
    computed = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()

    computed_stripped = hmac.new(
        secret.encode("utf-8"),
        body.strip(),
        hashlib.sha256
    ).hexdigest()

    if not (hmac.compare_digest(computed, x_event_signature) or hmac.compare_digest(computed_stripped, x_event_signature)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid event signature."
        )

router = APIRouter(prefix="/sync", tags=["HR Agent Sync"], dependencies=[Depends(verify_event_signature)])
events_router = APIRouter(prefix="/events", tags=["HR Agent Events"], dependencies=[Depends(verify_event_signature)])


class JobSyncPayload(BaseModel):
    job_id: str
    tenant_slug: str
    action: str
    title: Optional[str] = None
    description: Optional[str] = None
    company_name: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = None
    employment_type: Optional[str] = None
    location_type: Optional[str] = None
    requirements: Optional[List[str]] = None
    skills: Optional[List[str]] = None


class ApplicationSyncPayload(BaseModel):
    application_id: str
    hr_agent_application_id: str
    candidate_email: str
    job_id: str
    job_title: Optional[str] = None
    status: Optional[str] = None


class StageSyncPayload(BaseModel):
    application_id: str
    stage_number: int
    stage_name: str
    status: str
    score: Optional[float] = None
    feedback: Optional[str] = None
    scheduled_at: Optional[str] = None
    completed_at: Optional[str] = None


@router.post("/jobs")
def sync_job(payload: JobSyncPayload, db: Session = Depends(get_db)):
    if payload.action == "delete":
        db.execute(text("DELETE FROM hr_synced_jobs WHERE hr_job_id = :jid"), {"jid": payload.job_id})
    else:
        db.execute(text("""
            INSERT INTO hr_synced_jobs 
                (hr_job_id, tenant_slug, title, description, company_name, location,
                 salary_min, salary_max, currency, employment_type, location_type,
                 requirements, skills, synced_at)
            VALUES (:jid,:slug,:title,:desc,:company,:loc,:smin,:smax,:cur,:etype,:ltype,:req,:skills,now())
            ON CONFLICT (hr_job_id) DO UPDATE SET
                title=EXCLUDED.title, description=EXCLUDED.description,
                company_name=EXCLUDED.company_name, location=EXCLUDED.location,
                salary_min=EXCLUDED.salary_min, salary_max=EXCLUDED.salary_max,
                currency=EXCLUDED.currency, employment_type=EXCLUDED.employment_type,
                location_type=EXCLUDED.location_type, requirements=EXCLUDED.requirements,
                skills=EXCLUDED.skills, synced_at=now()
        """), {
            "jid": payload.job_id, "slug": payload.tenant_slug, "title": payload.title,
            "desc": payload.description, "company": payload.company_name, "loc": payload.location,
            "smin": payload.salary_min, "smax": payload.salary_max, "cur": payload.currency,
            "etype": payload.employment_type, "ltype": payload.location_type,
            "req": str(payload.requirements or []), "skills": str(payload.skills or [])
        })
    db.commit()
    return {"success": True}


@router.post("/applications")
def sync_application(payload: ApplicationSyncPayload, db: Session = Depends(get_db)):
    db.execute(text("""
        INSERT INTO hr_synced_applications
            (hr_application_id, candidate_email, hr_job_id, job_title, current_status, synced_at)
        VALUES (:appid,:email,:jid,:jtitle,:status,now())
        ON CONFLICT (hr_application_id) DO UPDATE SET
            current_status=EXCLUDED.current_status, synced_at=now()
    """), {
        "appid": payload.hr_agent_application_id, "email": payload.candidate_email,
        "jid": payload.job_id, "jtitle": payload.job_title, "status": payload.status or "APPLIED"
    })
    db.commit()
    return {"success": True}


@router.post("/stages")
def sync_stage(payload: StageSyncPayload, db: Session = Depends(get_db)):
    db.execute(text("""
        INSERT INTO hr_application_stages
            (hr_application_id, stage_number, stage_name, status, score, feedback,
             scheduled_at, completed_at, synced_at)
        VALUES (:appid,:snum,:sname,:status,:score,:feedback,:sched,:done,now())
        ON CONFLICT (hr_application_id, stage_number) DO UPDATE SET
            status=EXCLUDED.status, score=EXCLUDED.score, feedback=EXCLUDED.feedback,
            scheduled_at=EXCLUDED.scheduled_at, completed_at=EXCLUDED.completed_at, synced_at=now()
    """), {
        "appid": payload.application_id, "snum": payload.stage_number, "sname": payload.stage_name,
        "status": payload.status, "score": payload.score, "feedback": payload.feedback,
        "sched": payload.scheduled_at, "done": payload.completed_at
    })
    db.commit()
    return {"success": True}


@router.get("/stages/{candidate_email}")
def get_candidate_stages(candidate_email: str, db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT 
            a.hr_application_id, a.hr_job_id, a.job_title, a.current_status,
            s.stage_number, s.stage_name, s.status as stage_status,
            s.score, s.feedback, s.scheduled_at, s.completed_at
        FROM hr_synced_applications a
        LEFT JOIN hr_application_stages s ON s.hr_application_id = a.hr_application_id
        WHERE a.candidate_email = :email
        ORDER BY a.hr_application_id, s.stage_number
    """), {"email": candidate_email})
    rows = result.fetchall()
    apps: dict = {}
    for row in rows:
        aid = row.hr_application_id
        if aid not in apps:
            apps[aid] = {
                "hr_application_id": aid, "hr_job_id": row.hr_job_id,
                "job_title": row.job_title, "current_status": row.current_status, "stages": []
            }
        if row.stage_number is not None:
            apps[aid]["stages"].append({
                "stage_number": row.stage_number, "stage_name": row.stage_name,
                "status": row.stage_status, "score": row.score, "feedback": row.feedback,
                "scheduled_at": row.scheduled_at.isoformat() if row.scheduled_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            })
    return list(apps.values())


class EventEnvelope(BaseModel):
    event_id: str
    event_type: str
    version: str
    timestamp: str
    source: str
    company_id: str
    job_id: Optional[str] = None
    application_id: Optional[str] = None
    payload: dict


@events_router.post("", summary="Unified Event Gateway Receiver")
def receive_event(envelope: EventEnvelope, db: Session = Depends(get_db)):
    event_type = envelope.event_type
    payload = envelope.payload
    
    if event_type == "job.published":
        db.execute(text("""
            INSERT INTO hr_synced_jobs 
                (hr_job_id, tenant_slug, title, description, company_name, location,
                 salary_min, salary_max, currency, employment_type, location_type,
                 requirements, skills, synced_at)
            VALUES (:jid,:slug,:title,:desc,:company,:loc,:smin,:smax,:cur,:etype,:ltype,:req,:skills,now())
            ON CONFLICT (hr_job_id) DO UPDATE SET
                title=EXCLUDED.title, description=EXCLUDED.description,
                company_name=EXCLUDED.company_name, location=EXCLUDED.location,
                salary_min=EXCLUDED.salary_min, salary_max=EXCLUDED.salary_max,
                currency=EXCLUDED.currency, employment_type=EXCLUDED.employment_type,
                location_type=EXCLUDED.location_type, requirements=EXCLUDED.requirements,
                skills=EXCLUDED.skills, synced_at=now()
        """), {
            "jid": envelope.job_id or payload.get("job_id"),
            "slug": envelope.company_id,
            "title": payload.get("title"),
            "desc": payload.get("description"),
            "company": payload.get("company_name", "NirvahAI Corporation"),
            "loc": payload.get("location", "Remote"),
            "smin": payload.get("salary_min"),
            "smax": payload.get("salary_max"),
            "cur": payload.get("currency", "USD"),
            "etype": payload.get("employment_type", "FULL_TIME"),
            "ltype": payload.get("location_type", "REMOTE"),
            "req": str(payload.get("requirements", [])),
            "skills": str(payload.get("skills", []))
        })
        db.commit()
        
    elif event_type == "job.deleted":
        db.execute(text("DELETE FROM hr_synced_jobs WHERE hr_job_id = :jid"), {"jid": envelope.job_id or payload.get("job_id")})
        db.commit()
        
    elif event_type == "application.created":
        db.execute(text("""
            INSERT INTO hr_synced_applications
                (hr_application_id, candidate_email, hr_job_id, job_title, current_status, synced_at)
            VALUES (:appid,:email,:jid,:jtitle,:status,now())
            ON CONFLICT (hr_application_id) DO UPDATE SET
                current_status=EXCLUDED.current_status, synced_at=now()
        """), {
            "appid": envelope.application_id or payload.get("application_id"),
            "email": payload.get("candidate_email"),
            "jid": envelope.job_id or payload.get("job_id"),
            "jtitle": payload.get("job_title", "Software Engineer"),
            "status": payload.get("status", "APPLIED")
        })
        db.commit()
        
    elif event_type in ("candidate.stage_updated", "candidate.offered", "candidate.hired", "candidate.rejected"):
        db.execute(text("""
            INSERT INTO hr_application_stages
                (hr_application_id, stage_number, stage_name, status, score, feedback,
                 scheduled_at, completed_at, synced_at)
            VALUES (:appid,:snum,:sname,:status,:score,:feedback,:sched,:done,now())
            ON CONFLICT (hr_application_id, stage_number) DO UPDATE SET
                status=EXCLUDED.status, score=EXCLUDED.score, feedback=EXCLUDED.feedback,
                scheduled_at=EXCLUDED.scheduled_at, completed_at=EXCLUDED.completed_at, synced_at=now()
        """), {
            "appid": envelope.application_id or payload.get("application_id"),
            "snum": payload.get("stage_number"),
            "sname": payload.get("stage_name"),
            "status": payload.get("status"),
            "score": payload.get("score"),
            "feedback": payload.get("feedback"),
            "sched": payload.get("scheduled_at"),
            "done": payload.get("completed_at")
        })
        db.commit()
        
    return {"success": True, "event_id": envelope.event_id}
