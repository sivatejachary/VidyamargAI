import logging
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import JobAgentRun, JobAgentLog
from app.agents.resume_intelligence import ResumeIntelligenceAgent, CandidateProfileData
from app.agents.planning import PlanningAgent

logger = logging.getLogger(__name__)

# Active WebSocket connections dictionary to push live logs
# { run_id: [WebSocket, ...] }
_ACTIVE_WEBSOCKETS: Dict[int, List[Any]] = {}
_MAIN_LOOP = None

def register_websocket(run_id: int, websocket: Any):
    if run_id not in _ACTIVE_WEBSOCKETS:
        _ACTIVE_WEBSOCKETS[run_id] = []
    _ACTIVE_WEBSOCKETS[run_id].append(websocket)

def unregister_websocket(run_id: int, websocket: Any):
    if run_id in _ACTIVE_WEBSOCKETS:
        if websocket in _ACTIVE_WEBSOCKETS[run_id]:
            _ACTIVE_WEBSOCKETS[run_id].remove(websocket)
        if not _ACTIVE_WEBSOCKETS[run_id]:
            del _ACTIVE_WEBSOCKETS[run_id]

async def broadcast_log(run_id: int, message: str, status: str = "info"):
    """
    Broadcasts a log message in real-time to all WebSockets listening to this run.
    """
    if run_id in _ACTIVE_WEBSOCKETS:
        payload = json.dumps({
            "message": message,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        })
        for ws in _ACTIVE_WEBSOCKETS[run_id]:
            try:
                await ws.send_text(payload)
            except Exception:
                pass


def log_step(db: Session, run_id: int, agent_name: str, message: str, status: str = "info"):
    """
    Logs a step into the database and triggers real-time broadcast.
    """
    full_msg = f"[{agent_name}] {message}"
    
    # Open a local session to ensure thread-safety when called from concurrent threads
    from app.core.database import SessionLocal
    local_db = SessionLocal()
    try:
        log = JobAgentLog(run_id=run_id, message=full_msg, status=status)
        local_db.add(log)
        local_db.commit()
    except Exception as e:
        logger.error(f"Error logging step: {e}")
    finally:
        local_db.close()
        
    logger.info(full_msg)
    
    # Trigger async broadcast thread-safely using the main loop reference
    global _MAIN_LOOP
    if _MAIN_LOOP and _MAIN_LOOP.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_log(run_id, full_msg, status), _MAIN_LOOP)


async def run_agent_flow(run_id: int, candidate_id: int):
    """
    Centralized Agent flow orchestrator (Manager Agent).
    Runs asynchronously in the background.
    """
    global _MAIN_LOOP
    try:
        _MAIN_LOOP = asyncio.get_running_loop()
    except RuntimeError:
        pass

    db = SessionLocal()
    try:
        from app.agents.job_supervisor_agent import JobSupervisorAgent
        import app.services.job_cache as job_cache
        from app.models.models import Job, Company, JobSource, JobMatch, Candidate

        supervisor = JobSupervisorAgent(db, candidate_id)
        
        def log_callback(msg, status="info"):
            log_step(db, run_id, "Job Supervisor", msg, status)

        # Execute flow
        flow_result = await supervisor.execute_run_flow(run_id, log_callback)
        db.rollback()  # Refresh connection after long-running flow before starting db sync
        
        ranked_jobs = flow_result["jobs"]
        skill_gaps = flow_result["skill_gaps"]
        recommendations = flow_result["recommendations"]

        # Sync/Persist all matched jobs and their match scores to the database
        log_step(db, run_id, "Database Sync", "Persisting discovered jobs to the database...", "info")
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        
        for rj in ranked_jobs:
            # Check if this job already exists in DB (same title and company/department)
            db_job = db.query(Job).filter(
                Job.title == rj["title"],
                Job.department == rj["company"]
            ).first()
            
            if db_job:
                # Update existing job
                db_job.description = rj["description"]
                db_job.required_skills = ", ".join(rj.get("skills", []))
                db_job.experience_level = rj.get("experience", "Not Specified")
                db_job.location = rj["location"]
                db_job.status = "active"
                db.commit()
            else:
                # Create company if not exists
                company = db.query(Company).filter(Company.name.ilike(rj["company"])).first()
                if not company:
                    company = Company(name=rj["company"])
                    db.add(company)
                    db.commit()
                    db.refresh(company)
                
                # Insert new job
                db_job = Job(
                    title=rj["title"],
                    description=rj["description"],
                    required_skills=", ".join(rj.get("skills", [])),
                    experience_level=rj.get("experience", "Not Specified"),
                    salary_range=None,
                    location=rj["location"],
                    department=rj["company"],
                    company_id=company.id,
                    status="active"
                )
                db.add(db_job)
                db.commit()
                db.refresh(db_job)
                
                # Add job source details
                db.add(JobSource(
                    job_id=db_job.id,
                    source_platform=rj.get("source", "Internet"),
                    source_url=rj.get("apply_url", "")
                ))
                db.commit()

            # Update the ranked job ID to the persistent database ID!
            rj["id"] = str(db_job.id)

            # Update/save match score in 'job_matches' table
            match_rec = db.query(JobMatch).filter(JobMatch.candidate_id == candidate.id, JobMatch.job_id == db_job.id).first()
            if not match_rec:
                match_rec = JobMatch(
                    candidate_id=candidate.id,
                    job_id=db_job.id,
                    skill_match=rj["match_score"],
                    experience_match=rj["match_score"],
                    location_match=rj["match_score"],
                    match_score=rj["match_score"],
                    skills_gap=", ".join(rj.get("missing_skills", []))
                )
                db.add(match_rec)
            else:
                match_rec.match_score = rj["match_score"]
                match_rec.skills_gap = ", ".join(rj.get("missing_skills", []))
            db.commit()

        log_step(db, run_id, "Database Sync", f"Successfully synced and updated {len(ranked_jobs)} jobs in database.", "success")

        # 9. Store complete outputs in cache for 30 minutes
        from app.api.endpoints import _LIVE_JOB_STORE
        for rj in ranked_jobs:
            _LIVE_JOB_STORE[rj["id"]] = rj

        cache_payload = {
            "jobs": ranked_jobs,
            "skill_gaps": skill_gaps,
            "recommendations": recommendations
        }
        await job_cache.set(candidate_id, "agent_run_result", cache_payload, ttl=1800)

        # Mark Run as Completed
        run = db.query(JobAgentRun).filter(JobAgentRun.id == run_id).first()
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        db.commit()
        log_step(db, run_id, "Completed", f"[Completed] Agent run successful. Top {len(ranked_jobs)} opportunities matched and ready.", "success")

    except Exception as e:
        logger.exception("Error in autonomous agent flow")
        # Mark Run as Failed
        try:
            run = db.query(JobAgentRun).filter(JobAgentRun.id == run_id).first()
            if run:
                run.status = "failed"
                run.completed_at = datetime.utcnow()
                db.commit()
            log_step(db, run_id, "Failed", f"Agent run failed: {str(e)}", "error")
        except Exception:
            pass
    finally:
        db.close()
