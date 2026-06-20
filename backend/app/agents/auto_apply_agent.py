"""
VidyaMarg AI OS — Auto Apply Agent
LangGraph-based central orchestrator for automated job applications.
Coordinates profile loading, resume matchmaking, cover letter generation,
form filling, verification handling, and platform health monitoring.
"""
import asyncio
import logging
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional

from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.models.models import Candidate, CandidateResume, UserPreference
from app.models.auto_apply_models import (
    ApplicationRun, ApplicationTask, ApplicationMetrics,
    ApplicationDocument, ApplicationCoverLetter, ApplicationAnswer
)

# Services
from app.services.auto_apply.consent_service import consent_service
from app.services.auto_apply.audit_service import audit_service
from app.services.auto_apply.platform_health_service import platform_health_service
from app.services.auto_apply.platform_rate_limiter import platform_rate_limiter
from app.services.auto_apply.requirements_validator import requirements_validator
from app.services.auto_apply.resume_match_agent import resume_match_agent
from app.services.auto_apply.cover_letter_generator import cover_letter_generator
from app.services.auto_apply.screening_answer_engine import screening_answer_engine
from app.services.auto_apply.browser_fleet import fleet_manager
from app.services.auto_apply.adapters import detect_platform, load_adapter
from app.services.auto_apply.application_queue import application_queue

logger = logging.getLogger("app.agents.auto_apply")


class AgentState(TypedDict):
    run_id: int
    candidate_id: int
    profile: dict
    ranked_jobs: List[dict]
    filtered_jobs: List[dict]
    task_ids: List[int]
    status: str
    error: Optional[str]


class AutoApplyAgent:
    """
    LangGraph Auto Apply central agent.
    """

    def __init__(self, db: Session, candidate_id: int):
        self.db = db
        self.candidate_id = candidate_id

    def _load_profile(self, state: AgentState) -> dict:
        logger.info("AutoApplyAgent: Loading candidate profile...")
        candidate = self.db.query(Candidate).filter_by(id=state["candidate_id"]).first()
        if not candidate:
            return {"status": "failed", "error": "Candidate not found"}
        
        profile = {
            "id": candidate.id,
            "user_id": candidate.user_id,
            "phone": candidate.phone,
            "address": candidate.address,
            "location": candidate.location or "",
            "visa_eligible": getattr(candidate, "visa_eligible", True),
            "experience_years": getattr(candidate, "experience_years", 0),
            "education": getattr(candidate, "education", ""),
            "skills": [s.name for s in candidate.skills] if hasattr(candidate, "skills") else [],
        }
        return {"profile": profile}

    def _load_resume_builder_data(self, state: AgentState) -> dict:
        # Placeholder for loading any resume-builder custom configurations
        return {}

    def _load_ranked_jobs(self, state: AgentState) -> dict:
        logger.info("AutoApplyAgent: Fetching matched ranked jobs...")
        from app.models.models import JobMatch, Job, JobSource
        
        matches = self.db.query(JobMatch).join(Job).filter(
            JobMatch.candidate_id == state["candidate_id"],
            Job.status == "active"
        ).all()
        
        ranked_jobs = []
        for match in matches:
            job = match.job
            source = self.db.query(JobSource).filter_by(job_id=job.id).first()
            apply_url = source.source_url if source else ""
            if not apply_url:
                continue
            
            ranked_jobs.append({
                "job_id": job.id,
                "title": job.title,
                "company": job.company.name if job.company else "Unknown",
                "apply_url": apply_url,
                "match_score": match.match_score,
                "skill_match": match.skill_match,
                "description": job.description,
                "location": job.location,
                "required_skills": job.required_skills,
                "experience_level": job.experience_level,
                "job_type": getattr(job, "job_type", "Full-time"),
                "domain": getattr(job, "domain", ""),
            })
            
        ranked_jobs.sort(key=lambda x: x["match_score"], reverse=True)
        logger.info(f"AutoApplyAgent: Loaded {len(ranked_jobs)} potential jobs.")
        return {"ranked_jobs": ranked_jobs}

    def _filter_already_applied(self, state: AgentState) -> dict:
        logger.info("AutoApplyAgent: Filtering out already applied jobs...")
        from app.models.models import Application
        
        applied_job_ids = set(
            r[0] for r in self.db.query(Application.job_id).filter_by(candidate_id=state["candidate_id"]).all()
        )
        
        filtered = []
        for job in state["ranked_jobs"]:
            if job["job_id"] in applied_job_ids:
                continue
            
            # Check denormalized task logs to avoid duplicating tries
            already_applied = self.db.query(ApplicationTask).filter(
                ApplicationTask.candidate_id == state["candidate_id"],
                ApplicationTask.job_title == job["title"],
                ApplicationTask.company == job["company"],
                ApplicationTask.status == "SUBMITTED"
            ).first()
            if already_applied:
                continue
                
            filtered.append(job)
            
        return {"ranked_jobs": filtered}

    def _filter_auto_apply_rules(self, state: AgentState) -> dict:
        logger.info("AutoApplyAgent: Applying rule filters...")
        profile = state["profile"]
        prefs = self.db.query(UserPreference).filter_by(user_id=profile["user_id"]).first()
        
        min_score = prefs.auto_apply_min_score if prefs else 80.0
        min_skill = prefs.auto_apply_min_skill_match if prefs else 70.0
        
        filtered = []
        for job in state["ranked_jobs"]:
            if job["match_score"] < min_score:
                continue
            if job["skill_match"] < min_skill:
                continue
            filtered.append(job)
            
        logger.info(f"AutoApplyAgent: {len(filtered)} jobs passed rule filtering.")
        return {"filtered_jobs": filtered}

    def _create_application_queue(self, state: AgentState) -> dict:
        logger.info("AutoApplyAgent: Queueing tasks in DB...")
        task_ids = []
        
        for job in state["filtered_jobs"]:
            # Setup new ApplicationTask
            task = ApplicationTask(
                run_id=state["run_id"],
                candidate_id=state["candidate_id"],
                job_title=job["title"],
                company=job["company"],
                apply_url=job["apply_url"],
                platform=detect_platform(job["apply_url"]),
                status="QUEUED",
                match_score=job["match_score"],
                skill_match_score=job["skill_match"],
                approval_mode="always" # default
            )
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            task_ids.append(task.id)
            
            audit_service.log(
                actor="system",
                action="TASK_QUEUED",
                db=self.db,
                task_id=task.id,
                run_id=state["run_id"],
                details={"company": job["company"], "title": job["title"]}
            )
            
        # Update metrics
        metrics = self.db.query(ApplicationMetrics).filter_by(run_id=state["run_id"]).first()
        if metrics:
            metrics.jobs_queued = len(task_ids)
            metrics.jobs_selected = len(state["ranked_jobs"])
            metrics.jobs_skipped = len(state["ranked_jobs"]) - len(state["filtered_jobs"])
            self.db.commit()
            
        return {"task_ids": task_ids}

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        workflow.add_node("load_profile", self._load_profile)
        workflow.add_node("load_resume_builder_data", self._load_resume_builder_data)
        workflow.add_node("load_ranked_jobs", self._load_ranked_jobs)
        workflow.add_node("filter_already_applied", self._filter_already_applied)
        workflow.add_node("filter_auto_apply_rules", self._filter_auto_apply_rules)
        workflow.add_node("create_application_queue", self._create_application_queue)
        
        workflow.set_entry_point("load_profile")
        
        workflow.add_edge("load_profile", "load_resume_builder_data")
        workflow.add_edge("load_resume_builder_data", "load_ranked_jobs")
        workflow.add_edge("load_ranked_jobs", "filter_already_applied")
        workflow.add_edge("filter_already_applied", "filter_auto_apply_rules")
        workflow.add_edge("filter_auto_apply_rules", "create_application_queue")
        workflow.add_edge("create_application_queue", END)
        
        return workflow.compile()

    async def execute_run_flow(self, run_id: int) -> dict:
        initial_state = AgentState(
            run_id=run_id,
            candidate_id=self.candidate_id,
            profile={},
            ranked_jobs=[],
            filtered_jobs=[],
            task_ids=[],
            status="running",
            error=None
        )
        
        # 1. Execute graph to prepare tasks
        app = self._build_graph()
        final_state = await app.ainvoke(initial_state)
        
        task_ids = final_state.get("task_ids", [])
        if not task_ids:
            logger.info("AutoApplyAgent: No jobs queued for submission.")
            run = self.db.query(ApplicationRun).filter_by(id=run_id).first()
            if run:
                run.status = "completed"
                run.completed_at = datetime.utcnow()
                self.db.commit()
            return {"status": "completed", "message": "No jobs met the criteria."}
            
        # 2. Run workers via the parallel queue
        run = self.db.query(ApplicationRun).filter_by(id=run_id).first()
        if run:
            run.status = "running"
            self.db.commit()
            
        logger.info(f"AutoApplyAgent: Launching parallel execution for {len(task_ids)} tasks...")
        
        # We define the task worker execution routine
        async def process_task(task_id: int):
            # Each worker uses a fresh DB session for isolation
            from app.core.database import SessionLocal
            db_session = SessionLocal()
            try:
                await self.execute_single_task(task_id, db_session)
            finally:
                db_session.close()

        await application_queue.run_all(task_ids, process_task)
        
        # 3. Finalize run status
        run = self.db.query(ApplicationRun).filter_by(id=run_id).first()
        if run:
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            self.db.commit()
            
        return {"status": "completed", "tasks_processed": len(task_ids)}

    async def execute_single_task(self, task_id: int, db: Session):
        """Processes a single task end-to-end using anti-fingerprinting automation."""
        task = db.query(ApplicationTask).filter_by(id=task_id).first()
        if not task:
            return
        
        start_time = datetime.utcnow()
        task.status = "APPLYING"
        db.commit()
        
        platform = task.platform or "generic"
        
        # A. Reliability checks
        if not platform_health_service.is_platform_enabled(platform, db):
            task.status = "SKIPPED"
            task.rejection_reason = f"Platform {platform} is currently disabled due to low health."
            db.commit()
            audit_service.log("system", "TASK_SKIPPED", db, task_id=task.id, details={"reason": "platform_disabled"})
            return

        if not platform_rate_limiter.check_and_consume(task.candidate_id, platform, db):
            task.status = "RATE_LIMITED"
            db.commit()
            audit_service.log("system", "RATE_LIMITED", db, task_id=task.id)
            return

        # B. Requirements Validation
        candidate = db.query(Candidate).filter_by(id=task.candidate_id).first()
        profile_data = {
            "location": candidate.location,
            "education": getattr(candidate, "education", ""),
            "experience_years": getattr(candidate, "experience_years", 0),
            "skills": [s.name for s in candidate.skills] if hasattr(candidate, "skills") else [],
            "visa_eligible": getattr(candidate, "visa_eligible", True)
        }
        
        job_data = {
            "title": task.job_title,
            "description": "", # Fetch if needed
            "location": "",
        }
        
        val_res = requirements_validator.validate(profile_data, job_data)
        if not val_res.passed:
            task.status = "SKIPPED"
            task.rejection_reason = f"Requirements block: {', '.join(val_res.blockers)}"
            db.commit()
            audit_service.log("system", "REQUIREMENTS_FAILED", db, task_id=task.id, details={"blockers": val_res.blockers})
            
            # Update metrics
            metrics = db.query(ApplicationMetrics).filter_by(run_id=task.run_id).first()
            if metrics:
                metrics.requirements_failed += 1
                db.commit()
            return
            
        # C. Match Resume & Generate Cover Letter
        resumes = db.query(CandidateResume).filter_by(candidate_id=task.candidate_id).all()
        selected_resume = None
        if resumes:
            # Score resumes and select best version
            scores = resume_match_agent.score_all(task.candidate_id, job_data, db)
            if scores:
                best_score = scores[0]
                selected_resume = db.query(CandidateResume).filter_by(id=best_score.resume_id).first()
                task.selected_resume_id = selected_resume.id
                db.commit()
                
                doc = ApplicationDocument(
                    task_id=task.id,
                    resume_id=selected_resume.id,
                    resume_type=best_score.resume_type,
                    resume_score=best_score.score,
                    selection_reason=best_score.reason
                )
                db.add(doc)
                db.commit()
        
        # D. Generate Cover Letter
        cover_letter_content = cover_letter_generator.generate(profile_data, job_data, task.id, db)
        
        # E. Form Filling via Playwright adapter
        success = False
        error_msg = None
        
        try:
            # Initialize Playwright context
            await fleet_manager.start()
            context, slot = await fleet_manager.acquire_context(task.candidate_id, platform)
            
            if not context:
                raise ValueError("Could not acquire browser context.")
                
            page = await context.new_page()
            await page.goto(task.apply_url)
            
            # Load platform adapter
            adapter = load_adapter(platform)
            task.adapter_version = adapter.adapter_version
            db.commit()
            
            # Handle resume upload
            uploaded = False
            if selected_resume:
                # Mock file retrieval — in production, fetch from MinIO/S3
                import os
                dummy_resume_bytes = b"%PDF-1.4 mock resume file content"
                uploaded = await adapter.upload_resume(page, dummy_resume_bytes, "Resume.pdf")
                if uploaded:
                    audit_service.log(f"adapter:{platform}", "RESUME_UPLOADED", db, task_id=task.id)
            
            # Fill details
            await adapter.fill_personal_details(page, profile_data)
            await adapter.fill_education(page, profile_data)
            await adapter.fill_experience(page, profile_data)
            await adapter.fill_skills(page, profile_data)
            
            # Answer screening
            await adapter.answer_screening(page, [], screening_answer_engine, cover_letter_content)
            
            # CAPTCHA / OTP / human review checks
            verification = await adapter.detect_verification_required(page)
            if verification:
                task.status = "WAITING_FOR_USER"
                db.commit()
                audit_service.log(f"adapter:{platform}", "VERIFICATION_DETECTED", db, task_id=task.id, details={"type": verification})
                await fleet_manager.release_context(context, slot)
                return

            # Submit
            submitted = await adapter.submit(page)
            if submitted:
                conf = await adapter.capture_confirmation(page)
                success = conf.get("submitted", True)
                
            await fleet_manager.release_context(context, slot)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Playwright automation crashed for task {task.id}: {e}")
            
        # F. Post-execution status and health monitoring
        duration = (datetime.utcnow() - start_time).total_seconds()
        platform_health_service.record_attempt(platform, success, db, duration, error=error_msg)
        
        if success:
            task.status = "SUBMITTED"
            db.commit()
            audit_service.log(f"adapter:{platform}", "APPLICATION_SUBMITTED", db, task_id=task.id)
            
            # Add final Application record
            from app.models.models import Application
            app_record = Application(
                candidate_id=task.candidate_id,
                job_id=doc.resume_id if selected_resume else 1, # fallback
                resume_id=selected_resume.id if selected_resume else None,
                status="applied"
            )
            from app.models.models import JobSource
            src = db.query(JobSource).filter_by(source_url=task.apply_url).first()
            if src:
                app_record.job_id = src.job_id
                db.add(app_record)
                db.commit()
        else:
            task.status = "FAILED"
            task.rejection_reason = error_msg or "Failed to complete form submission."
            db.commit()
            audit_service.log(f"adapter:{platform}", "SUBMISSION_FAILED", db, task_id=task.id, details={"error": error_msg})
            
        # Update metrics
        metrics = db.query(ApplicationMetrics).filter_by(run_id=task.run_id).first()
        if metrics:
            if success:
                metrics.applications_submitted += 1
            else:
                metrics.applications_failed += 1
            db.commit()
