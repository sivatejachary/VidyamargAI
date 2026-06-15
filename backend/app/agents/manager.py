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
        from app.agents.resume_intelligence import ResumeIntelligenceAgent
        from app.agents.planning import PlanningAgent
        from app.agents.search import SearchAgent
        from app.agents.verification import VerificationAgent
        from app.agents.matching import MatchingAgent
        from app.agents.ranking import RankingAgent
        from app.agents.skill_gap import SkillGapAgent
        from app.agents.recommendation import RecommendationAgent
        import app.services.job_cache as job_cache

        # 1. Resume Intelligence Agent
        log_step(db, run_id, "Resume Agent", "Loading candidate profile and latest resume...", "info")
        await asyncio.sleep(0.5)  # small pause to make log visible
        resume_agent = ResumeIntelligenceAgent(db, candidate_id)
        profile = resume_agent.extract_profile()
        log_step(db, run_id, "Resume Agent", f"Found {len(profile.skills)} skills and {profile.experience_years} years of experience.", "success")

        # 2. Planning Agent
        log_step(db, run_id, "Planning Agent", "Creating search strategy...", "info")
        await asyncio.sleep(0.5)
        planning_agent = PlanningAgent(profile)
        queries = planning_agent.generate_strategy()
        log_step(db, run_id, "Planning Agent", f"Generated {len(queries)} search query variations.", "success")

        # 3. Portal Search & Telegram Community Agents
        log_step(db, run_id, "Search Agent", "Searching job portals and Telegram channels concurrently...", "info")
        await asyncio.sleep(0.5)
        
        search_agent = SearchAgent(queries, profile.skills, profile.experience_years)
        from app.agents.telegram import TelegramCommunityAgent
        telegram_agent = TelegramCommunityAgent(db)
        
        def portal_log_callback(msg, status="info"):
            log_step(db, run_id, "Portal Search Agent", msg, status)
            
        def tg_log_callback(msg, status="info"):
            log_step(db, run_id, "Telegram Community Agent", msg, status)
            
        loop = asyncio.get_event_loop()
        portal_task = loop.run_in_executor(None, lambda: search_agent.execute_search(portal_log_callback))
        tg_task = loop.run_in_executor(None, lambda: telegram_agent.collect_jobs(tg_log_callback))
        
        portal_jobs, tg_jobs = await asyncio.gather(portal_task, tg_task)
        raw_jobs = portal_jobs + tg_jobs
        log_step(db, run_id, "Search Agent", f"Completed aggregation. Collected {len(portal_jobs)} jobs from portals and {len(tg_jobs)} jobs from Telegram channels.", "success")

        # 4. Verification Agent
        log_step(db, run_id, "Verification Agent", "Filtering out expired jobs, scam indicators, and duplicates...", "info")
        await asyncio.sleep(0.5)
        verification_agent = VerificationAgent(raw_jobs)
        
        def ver_log_callback(msg, status="info"):
            log_step(db, run_id, "Verification Agent", msg, status)
            
        verified_jobs = verification_agent.verify_and_deduplicate(ver_log_callback)

        # 4b. Job Consistency Agent
        log_step(db, run_id, "Job Consistency Agent", "Auditing landing page details in parallel for title, company, and location consistency...", "info")
        await asyncio.sleep(0.5)
        from app.agents.consistency import JobConsistencyAgent
        consistency_agent = JobConsistencyAgent(db)
        
        final_verified_jobs = []
        consistency_rejected_count = 0
        
        loop = asyncio.get_running_loop()
        def audit_job(job):
            score, status = consistency_agent.verify_job_consistency(job)
            return job, score, status

        tasks = [
            loop.run_in_executor(None, audit_job, j)
            for j in verified_jobs
        ]
        
        results = await asyncio.gather(*tasks)
        for job, score, status in results:
            job.verification_score = score
            job.verification_status = status
            
            if status == "Rejected":
                consistency_rejected_count += 1
                log_step(db, run_id, "Job Consistency Agent", f"Rejected job '{job.title}' at '{job.company}' (Score: {score}): Landing page details did not match", "warning")
            else:
                final_verified_jobs.append(job)
                
        log_step(db, run_id, "Job Consistency Agent", f"Completed consistency audits. Approved {len(final_verified_jobs)} jobs, filtered out {consistency_rejected_count} mismatched listings.", "success")

        # 5. Matching Agent
        log_step(db, run_id, "Matching Agent", "Calculating resume-to-job match scores using 4-factor formula...", "info")
        await asyncio.sleep(0.5)
        matching_agent = MatchingAgent(profile)
        
        matched_jobs = []
        for j in final_verified_jobs:
            match_res = matching_agent.match_job(j)
            
            # Merge job details with match outputs
            job_dict = {
                "id": j.stable_id,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "experience": j.experience,
                "work_mode": j.work_mode,
                "skills": j.skills,
                "apply_url": j.apply_url,
                "posted_date": j.posted_date,
                "source": j.source,
                "description": j.description,
                "company_logo": j.company_logo,
                
                # Match scores
                "match_score": match_res["match_score"],
                "matched_skills": match_res["matched_skills"],
                "missing_skills": match_res["missing_skills"],
                "reasoning": match_res["reasoning"],
                
                # Verification Details
                "verification_score": getattr(j, "verification_score", 100),
                "verification_status": getattr(j, "verification_status", "Fully Verified")
            }
            matched_jobs.append(job_dict)
        log_step(db, run_id, "Matching Agent", "Completed compatibility calculations.", "success")

        # 6. Ranking Agent
        log_step(db, run_id, "Ranking Agent", "Ranking jobs by match score relevance, freshness, and reliability...", "info")
        await asyncio.sleep(0.5)
        ranking_agent = RankingAgent(matched_jobs)
        
        def rank_log_callback(msg, status="info"):
            log_step(db, run_id, "Ranking Agent", msg, status)
            
        ranked_jobs = ranking_agent.rank_jobs(rank_log_callback)

        # 7. Skill Gap Agent
        log_step(db, run_id, "Skill Gap Agent", "Analyzing missing skills in top matching opportunities...", "info")
        await asyncio.sleep(0.5)
        skill_gap_agent = SkillGapAgent(ranked_jobs)
        skill_gaps = skill_gap_agent.analyze_gaps()
        if skill_gaps:
            top_missing = ", ".join([g["skill"] for g in skill_gaps[:3]])
            log_step(db, run_id, "Skill Gap Agent", f"Most requested missing skills: {top_missing}", "warning")
        else:
            log_step(db, run_id, "Skill Gap Agent", "No significant skill gaps found.", "success")

        # 8. Recommendation Agent
        log_step(db, run_id, "Recommendation Agent", "Generating recommended certifications, projects, and learning paths...", "info")
        await asyncio.sleep(0.5)
        rec_agent = RecommendationAgent(skill_gaps)
        recommendations = rec_agent.generate_recommendations()
        log_step(db, run_id, "Recommendation Agent", "Roadmap generated successfully.", "success")

        # Sync/Persist all matched jobs and their match scores to the database
        log_step(db, run_id, "Database Sync", "Persisting discovered jobs to the database...", "info")
        from app.models.models import Job, Company, JobSource, JobMatch, Candidate
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
        # Re-save to LIVE_JOB_STORE in endpoints as well for detail modal clicks
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
        log_step(db, run_id, "Completed", f"Top {len(ranked_jobs)} opportunities generated successfully.", "success")

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
