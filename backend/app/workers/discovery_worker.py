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
from app.services.job_connectors.tier1.greenhouse_api import fetch_greenhouse_jobs
from app.services.job_connectors.tier1.lever_api import fetch_lever_jobs
from app.services.job_connectors.tier1.rss_feeds import fetch_rss_jobs
from app.services.job_connectors.tier2.google_discovery import search_google_jobs
from app.core.config import settings
from app.agents.resume_intelligence import ResumeIntelligenceAgent
from app.services.job_connectors.candidate_query_generator import generate_queries
from app.agents.verification import VerificationAgent
from app.services.job_connectors.base import classify_job

logger = logging.getLogger("app.workers.discovery")


import time
import json
from typing import List, Tuple

def update_source_status(db: Session, source_name: str, success: bool, latency: float):
    try:
        from app.models.models import JobSourceTracking
        tracking = db.query(JobSourceTracking).filter(JobSourceTracking.source_name == source_name).first()
        if not tracking:
            tracking = JobSourceTracking(source_name=source_name)
            db.add(tracking)
            
        tracking.last_crawl = datetime.utcnow()
        if success:
            tracking.success_count += 1
            tracking.status = "healthy"
        else:
            tracking.failure_count += 1
            tracking.status = "degraded" if tracking.success_count > 0 else "offline"
            
        # Update running average response time
        total_runs = tracking.success_count + tracking.failure_count
        if total_runs > 1:
            tracking.avg_response_time = (tracking.avg_response_time * (total_runs - 1) + latency) / total_runs
        else:
            tracking.avg_response_time = latency
            
        db.commit()
    except Exception as e:
        logger.error(f"Failed to update JobSourceTracking for {source_name}: {e}")
        db.rollback()

def get_crawler_queries_and_skills(db: Session) -> Tuple[List[str], List[str]]:
    from app.models.models import CandidateProfile, Candidate
    profiles = db.query(CandidateProfile).all()
    queries = set()
    skills = set()
    
    for p in profiles:
        if p.search_strategy:
            try:
                strat = json.loads(p.search_strategy)
                if isinstance(strat, dict):
                    primary = strat.get("primary_roles", [])
                    secondary = strat.get("secondary_roles", [])
                    kws = strat.get("keywords", [])
                    queries.update(primary)
                    queries.update(secondary)
                    skills.update(kws)
            except Exception:
                pass
        if p.generated_roles:
            try:
                roles = json.loads(p.generated_roles)
                if isinstance(roles, list):
                    queries.update(roles)
            except Exception:
                pass
                
    # Also fetch skills from candidates table
    candidates = db.query(Candidate).all()
    for c in candidates:
        if c.skills:
            cand_skills = [s.strip() for s in c.skills.split(",") if s.strip()]
            skills.update(cand_skills)
            
    # Fallback to default tech and non-tech queries to guarantee it works for all professions
    if not queries:
        queries = {
            "Software Engineer", "React Developer", "Python Developer", "Data Scientist",
            "Civil Engineer", "Construction Manager", "Mechanical Engineer", "Project Manager",
            "Product Manager", "Financial Analyst", "Marketing Executive", "HR Generalist"
        }
    if not skills:
        skills = {
            "Python", "JavaScript", "React", "SQL", "AutoCAD", "Site Supervision",
            "Project Management", "Excel", "Marketing", "Recruiting"
        }
        
    return list(queries)[:30], list(skills)[:30]

async def run_discovery_all_candidates():
    """Runs candidate-independent background job discovery, saves jobs to pool, and runs matching for candidates."""
    logger.info("Starting candidate-independent background job discovery cycle")
    db = SessionLocal()
    try:
        # 1. Gather queries and skills from all active profiles/resumes
        queries, skills = get_crawler_queries_and_skills(db)
        
        # 2. Run crawl of all sources offline
        discovered_jobs = await discover_jobs_network_independent(db, queries, skills)
        
        # 3. Save discovered jobs to the database JobPool and vector store
        if discovered_jobs:
            logger.info(f"Saving {len(discovered_jobs)} verified discovered jobs to the database pool")
            saved_count = 0
            new_jobs = []
            for job in discovered_jobs:
                existing = db.query(JobPool).filter(JobPool.stable_id == job.stable_id).first()
                if not existing:
                    classification = classify_job(job.title, job.description or "", job.skills or [])
                    new_job = JobPool(
                        stable_id=job.stable_id,
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
                        domain=classification["domain"],
                        job_type=classification["job_type"],
                        career_level=classification["career_level"],
                        all_sources=getattr(job, "all_sources", [job.source])
                    )
                    db.add(new_job)
                    new_jobs.append(new_job)
                    saved_count += 1
            if saved_count > 0:
                db.commit()
                logger.info(f"Saved {saved_count} new unique jobs to JobPool")
                # Upsert to Qdrant
                from app.services.vector_store import vector_store
                for j in new_jobs:
                    await vector_store.upsert_job(
                        job_id=j.id,
                        title=j.title,
                        company=j.company,
                        description=j.description,
                        skills=j.skills
                    )
                logger.info(f"Upserted {len(new_jobs)} jobs to Qdrant vector store")
                
        # 4. Trigger candidate-specific matching for all candidates
        from app.models.models import Candidate
        candidates = db.query(Candidate).all()
        for candidate in candidates:
            cand_skills = [s.strip() for s in (candidate.skills or "").split(",") if s.strip()]
            try:
                await match_pool_jobs_for_candidate(candidate, db, cand_skills)
            except Exception as e:
                logger.error(f"Matching failed for candidate {candidate.id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in run_discovery_all_candidates background worker: {e}")
    finally:
        db.close()
    logger.info("Background job discovery cycle completed")

async def discover_jobs_network_independent(db: Session, queries: list, skills: list) -> list:
    """Performs candidate-independent searches across multiple platforms and records metrics in JobSourceTracking."""
    all_discovered = []

    # 1. Greenhouse
    start_time = time.time()
    try:
        greenhouse_jobs = await fetch_greenhouse_jobs(queries)
        latency = time.time() - start_time
        update_source_status(db, "Greenhouse", success=True, latency=latency)
        all_discovered.extend(greenhouse_jobs)
    except Exception as e:
        latency = time.time() - start_time
        update_source_status(db, "Greenhouse", success=False, latency=latency)
        logger.error(f"Greenhouse crawler failed: {e}")

    # 2. Lever
    start_time = time.time()
    try:
        lever_jobs = await fetch_lever_jobs(queries)
        latency = time.time() - start_time
        update_source_status(db, "Lever", success=True, latency=latency)
        all_discovered.extend(lever_jobs)
    except Exception as e:
        latency = time.time() - start_time
        update_source_status(db, "Lever", success=False, latency=latency)
        logger.error(f"Lever crawler failed: {e}")

    # 3. Workday and ATS fallback site-searches
    start_time = time.time()
    try:
        from app.services.job_connectors import ats_sources
        ats_jobs = await asyncio.to_thread(ats_sources.fetch, queries)
        latency = time.time() - start_time
        update_source_status(db, "Workday", success=True, latency=latency)
        all_discovered.extend(ats_jobs)
    except Exception as e:
        latency = time.time() - start_time
        update_source_status(db, "Workday", success=False, latency=latency)
        logger.error(f"Workday/ATS crawler failed: {e}")

    # 4. LinkedIn Jobs
    start_time = time.time()
    try:
        from app.services.job_connectors import linkedin_jobs
        linkedin_res = await asyncio.to_thread(linkedin_jobs.fetch, queries)
        latency = time.time() - start_time
        update_source_status(db, "LinkedIn", success=True, latency=latency)
        all_discovered.extend(linkedin_res)
    except Exception as e:
        latency = time.time() - start_time
        update_source_status(db, "LinkedIn", success=False, latency=latency)
        logger.error(f"LinkedIn crawler failed: {e}")

    # 5. Naukri
    start_time = time.time()
    try:
        from app.services.job_connectors import naukri
        naukri_res = await asyncio.to_thread(naukri.fetch, queries)
        latency = time.time() - start_time
        update_source_status(db, "Naukri", success=True, latency=latency)
        all_discovered.extend(naukri_res)
    except Exception as e:
        latency = time.time() - start_time
        update_source_status(db, "Naukri", success=False, latency=latency)
        logger.error(f"Naukri crawler failed: {e}")

    # 6. Telegram
    start_time = time.time()
    try:
        from app.agents.telegram import TelegramCommunityAgent
        tg_agent = TelegramCommunityAgent(db)
        tg_jobs = await tg_agent.async_collect_jobs()
        latency = time.time() - start_time
        update_source_status(db, "Telegram", success=True, latency=latency)
        all_discovered.extend(tg_jobs)
    except Exception as e:
        latency = time.time() - start_time
        update_source_status(db, "Telegram", success=False, latency=latency)
        logger.error(f"Telegram crawler failed: {e}")

    # Other crawlers (Foundit, Wellfound, Indeed, Cutshort, Hirist, Internshala, Instahyre, RSS)
    try:
        from app.services.job_connectors import (
            foundit, wellfound, indeed, cutshort, hirist, internshala, instahyre, hiring_posts
        )
        sync_connectors = [
            ("Foundit", foundit.fetch, (queries,)),
            ("Wellfound", wellfound.fetch, (queries,)),
            ("Indeed", indeed.fetch, (queries,)),
            ("Cutshort", cutshort.fetch, (queries,)),
            ("Hirist", hirist.fetch, (queries,)),
            ("Internshala", internshala.fetch, (queries,)),
            ("Instahyre", instahyre.fetch, (queries,)),
            ("LinkedIn Hiring Posts", hiring_posts.fetch, (skills,)),
        ]
        tasks = [asyncio.to_thread(fn, *args) for name, fn, args in sync_connectors]
        connector_results = await asyncio.gather(*tasks, return_exceptions=True)
        for (name, _, _), r in zip(sync_connectors, connector_results):
            if isinstance(r, list):
                all_discovered.extend(r)
    except Exception as e:
        logger.warning(f"Secondary connectors failed: {e}")

    # Enforce Verification Agent: filters freshness, location (India-only), groups duplicates by priority
    verifier = VerificationAgent(all_discovered)
    verified_jobs = verifier.verify_and_deduplicate()

    return verified_jobs



async def save_and_match_discovered_jobs(candidate_id: int, candidate_skills: list, unique_jobs: list):
    """Ingests discovered jobs and runs matching scores in a fast, isolated session."""
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            logger.warning(f"Candidate {candidate_id} not found when saving jobs")
            return

        logger.info(f"Candidate {candidate_id} | Ingesting {len(unique_jobs)} discovered jobs to pool")
        
        saved_count = 0
        new_jobs = []
        for job in unique_jobs:
            # Check if already in pool
            existing = db.query(JobPool).filter(JobPool.stable_id == job.stable_id).first()
            if not existing:
                classification = classify_job(job.title, job.description or "", job.skills or [])
                new_job = JobPool(
                    stable_id=job.stable_id,
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
                    domain=classification["domain"],
                    job_type=classification["job_type"],
                    career_level=classification["career_level"],
                    all_sources=getattr(job, "all_sources", [job.source])
                )
                db.add(new_job)
                new_jobs.append(new_job)
                saved_count += 1
                
        if saved_count > 0:
            db.commit()
            logger.info(f"Candidate {candidate_id} | Saved {saved_count} new unique jobs")
            
            # Upsert new jobs into Qdrant Vector Store
            try:
                from app.services.vector_store import vector_store
                for j in new_jobs:
                    await vector_store.upsert_job(
                        job_id=j.id,
                        title=j.title,
                        company=j.company,
                        description=j.description,
                        skills=j.skills
                    )
                logger.info(f"Upserted {len(new_jobs)} jobs to Qdrant vector store.")
            except Exception as q_err:
                logger.error(f"Error upserting jobs to Qdrant: {q_err}")
            
        # Trigger matching / scoring inside this active session
        await match_pool_jobs_for_candidate(candidate, db, candidate_skills)

            
    except Exception as e:
        logger.error(f"Error in save_and_match_discovered_jobs for candidate {candidate_id}: {e}")
        db.rollback()
    finally:
        db.close()


async def match_pool_jobs_for_candidate(candidate: Candidate, db: Session, candidate_skills: list):
    """
    Computes matching scores for all jobs in the pool against this candidate,
    using Qdrant semantic search if enabled, otherwise falling back to a full DB scan.
    """
    # Load candidate profile
    resume_agent = ResumeIntelligenceAgent(db, candidate.id)
    profile = resume_agent.extract_profile()
    
    # Construct query string representing candidate's profile
    resume_text = f"Roles: {', '.join(profile.preferred_roles or [])}\nDomain: {profile.domain or ''}\nSkills: {', '.join(profile.skills or [])}\nExperience: {profile.experience_years or 0} years"
    
    # Attempt Qdrant semantic search
    from app.services.vector_store import vector_store
    semantic_job_ids = []
    if vector_store.enabled:
        try:
            semantic_job_ids = await vector_store.search_jobs(resume_text, limit=50)
            logger.info(f"Qdrant returned {len(semantic_job_ids)} candidate jobs for candidate {candidate.id}")
        except Exception as q_err:
            logger.warning(f"Qdrant search failed: {q_err}. Falling back to database scan.")

    if semantic_job_ids:
        # Fetch only the semantically matched jobs that haven't been scored yet
        unmatched_jobs = db.query(JobPool).filter(
            JobPool.id.in_(semantic_job_ids)
        ).outerjoin(
            JobPoolMatch, 
            (JobPoolMatch.job_pool_id == JobPool.id) & (JobPoolMatch.candidate_id == candidate.id)
        ).filter(JobPoolMatch.id == None).all()
        
        # Keep the exact Qdrant relevance ordering
        job_map = {j.id: j for j in unmatched_jobs}
        unmatched_jobs = [job_map[jid] for jid in semantic_job_ids if jid in job_map]
    else:
        # Fallback: scan database for any job without a match score for this candidate
        unmatched_jobs = db.query(JobPool).outerjoin(
            JobPoolMatch, 
            (JobPoolMatch.job_pool_id == JobPool.id) & (JobPoolMatch.candidate_id == candidate.id)
        ).filter(JobPoolMatch.id == None).all()
    
    if not unmatched_jobs:
        return
        
    logger.info(f"Candidate {candidate.id} | Computing matches for {len(unmatched_jobs)} jobs")

    
    from app.agents.matching_agent import calculate_match_score_and_reasons
    
    for job in unmatched_jobs:
        res = calculate_match_score_and_reasons(
            profile=profile,
            job_title=job.title,
            job_description=job.description,
            job_skills_list=job.skills or [],
            job_experience_str=job.experience
        )
        score = res["match_score"]
        
        # Opportunity score is equal to match score for direct simplicity
        opp_score = score
        
        new_match = JobPoolMatch(
            candidate_id=candidate.id,
            job_pool_id=job.id,
            match_score=score,
            opportunity_score=opp_score,
            skills_gap=",".join(res["missing_skills"]),
            reasons_json=res["reasons"],
            should_apply=opp_score >= 70.0,
        )
        db.add(new_match)
        
    db.commit()
    logger.info(f"Candidate {candidate.id} | Matching complete")
    
    # Invalidate cached jobs pool and skill gap for the candidate
    try:
        import app.services.job_cache as job_cache
        await job_cache.invalidate_jobs_pool(candidate.id)
        await job_cache.invalidate_skill_gap(candidate.id)
    except Exception as e:
        logger.warning(f"Failed to invalidate cache after matching: {e}")
