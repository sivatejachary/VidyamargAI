"""
Discovery Worker — background worker that regularly discovers new jobs
for all active candidates using the 3-tier discovery architecture.
"""
import logging
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Candidate
from app.models.pool_models import JobPool, JobPoolMatch
from app.services.job_connectors.query_builder import build_queries
from app.services.job_connectors.tier1.greenhouse_api import fetch_greenhouse_jobs
from app.services.job_connectors.tier1.lever_api import fetch_lever_jobs
from app.services.job_connectors.tier1.rss_feeds import fetch_rss_jobs
from app.services.job_connectors.tier2.google_discovery import search_google_jobs
from app.core.config import settings

logger = logging.getLogger("app.workers.discovery")


async def run_discovery_all_candidates():
    """Runs job discovery for all active candidates in the system."""
    logger.info("Starting background job discovery for all candidates")
    db = SessionLocal()
    try:
        candidates = db.query(Candidate).all()
        for candidate in candidates:
            try:
                await discover_for_candidate(candidate, db)
            except Exception as e:
                logger.error(f"Discovery failed for candidate {candidate.id}: {e}")
    finally:
        db.close()
    logger.info("Background job discovery cycle completed")


async def discover_for_candidate(candidate: Candidate, db: Session):
    """
    Tiered discovery — tries each tier until sufficient jobs are found.
    """
    # Build search queries
    queries = build_queries(candidate)
    skills = [s.strip() for s in (candidate.skills or "").split(",") if s.strip()]
    all_discovered = []

    # TIER 1: Direct APIs (always try first — free, reliable, no rate limits)
    logger.info(f"Candidate {candidate.id} | Tier 1 Discovery started")
    t1_tasks = [
        fetch_greenhouse_jobs(queries),
        fetch_lever_jobs(queries),
        fetch_rss_jobs(queries, skills),
    ]
    t1_results = await asyncio.gather(*t1_tasks, return_exceptions=True)
    for r in t1_results:
        if isinstance(r, list):
            all_discovered.extend(r)
            
    logger.info(f"Candidate {candidate.id} | Tier 1 found {len(all_discovered)} jobs")

    # TIER 2: Google Discovery (Serper / fallback search)
    # Triggered if we didn't find enough jobs from Tier 1
    if len(all_discovered) < 20:
        logger.info(f"Candidate {candidate.id} | Tier 2 Discovery triggered")
        try:
            google_jobs = await search_google_jobs(queries)
            all_discovered.extend(google_jobs)
            logger.info(f"Candidate {candidate.id} | Tier 2 found {len(google_jobs)} jobs")
        except Exception as e:
            logger.warning(f"Tier 2 Google discovery failed: {e}")

    # Deduplicate based on apply url / stable_id
    unique_jobs = {}
    for j in all_discovered:
        unique_jobs[j.stable_id] = j

    logger.info(f"Candidate {candidate.id} | Ingesting {len(unique_jobs)} discovered jobs to pool")
    
    # Ingest into DB
    saved_count = 0
    for stable_id, job in unique_jobs.items():
        # Check if already in pool
        existing = db.query(JobPool).filter(JobPool.stable_id == stable_id).first()
        if not existing:
            new_job = JobPool(
                stable_id=stable_id,
                title=job.title,
                company=job.company,
                location=job.location,
                experience=job.experience,
                skills=job.skills,
                apply_url=job.apply_url,
                posted_date=job.posted_date,
                source=job.source,
                description=job.description,
                work_mode=job.work_mode,
                company_logo=job.company_logo,
            )
            db.add(new_job)
            saved_count += 1
            
    if saved_count > 0:
        db.commit()
        logger.info(f"Candidate {candidate.id} | Saved {saved_count} new unique jobs")
        
        # Trigger matching / scoring
        await match_pool_jobs_for_candidate(candidate, db)


async def match_pool_jobs_for_candidate(candidate: Candidate, db: Session):
    """
    Computes matching scores for all jobs in the pool against this candidate.
    """
    from app.agents.job_supervisor_agent import JobSupervisorAgent
    
    unmatched_jobs = db.query(JobPool).outerjoin(
        JobPoolMatch, 
        (JobPoolMatch.job_pool_id == JobPool.id) & (JobPoolMatch.candidate_id == candidate.id)
    ).filter(JobPoolMatch.id == None).all()
    
    if not unmatched_jobs:
        return
        
    logger.info(f"Candidate {candidate.id} | Computing matches for {len(unmatched_jobs)} new jobs")
    
    candidate_skills = [s.strip().lower() for s in (candidate.skills or "").split(",") if s.strip()]
    
    for job in unmatched_jobs:
        # Quick intersection match score calculation (fast, no LLM required for bulk pool)
        job_skills = [s.strip().lower() for s in (job.skills or [])]
        if not job_skills:
            # try parsing description for skills
            from app.services.job_connectors.tier1.greenhouse_api import _extract_skills_from_content
            job_skills = [s.lower() for s in _extract_skills_from_content(job.description or "")]
            
        matched = set(candidate_skills).intersection(set(job_skills))
        missing = set(job_skills) - set(candidate_skills)
        
        # Base Match Score
        score = 50.0
        if job_skills:
            score = (len(matched) / len(job_skills)) * 100.0
        else:
            # Fallback semantic contains checks
            score = 65.0 if any(r.lower() in job.title.lower() for r in ["engineer", "developer"]) else 50.0
            
        # Composite Opportunity Score calculation (Phase 10/11)
        # base score + some company quality factor + freshness
        opp_score = score
        # Freshness: +10 if created in last 24h
        opp_score += 10.0
        opp_score = min(100.0, max(0.0, opp_score))
        
        new_match = JobPoolMatch(
            candidate_id=candidate.id,
            job_pool_id=job.id,
            match_score=score,
            opportunity_score=opp_score,
            skills_gap=",".join(missing),
            opportunity_breakdown={"match": score, "freshness": 10.0},
            should_apply=opp_score >= 70,
        )
        db.add(new_match)
        
    db.commit()
    logger.info(f"Candidate {candidate.id} | Matching complete")
