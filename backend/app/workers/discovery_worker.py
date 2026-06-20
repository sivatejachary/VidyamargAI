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


async def run_discovery_all_candidates():
    """Runs job discovery for all active candidates in the system."""
    logger.info("Starting background job discovery for all candidates")
    db = SessionLocal()
    candidates_info = []
    try:
        candidates = db.query(Candidate).all()
        for candidate in candidates:
            # Load candidate profile
            resume_agent = ResumeIntelligenceAgent(db, candidate.id)
            profile = resume_agent.extract_profile()
            
            # Generate target India-focused queries
            queries = generate_queries(profile.domain, profile.preferred_roles)
            skills = [s.strip() for s in (candidate.skills or "").split(",") if s.strip()]
            
            candidates_info.append({
                "id": candidate.id,
                "queries": queries,
                "skills": skills,
            })
    except Exception as e:
        logger.error(f"Error querying candidates: {e}")
    finally:
        db.close()

    for info in candidates_info:
        try:
            # Execute external crawls offline, without holding any DB connection active
            discovered_jobs = await discover_jobs_network(info["id"], info["queries"], info["skills"])
            
            # Ingest and match results in a fresh, quick DB session
            if discovered_jobs:
                await save_and_match_discovered_jobs(info["id"], info["skills"], discovered_jobs)
        except Exception as e:
            logger.error(f"Discovery failed for candidate {info['id']}: {e}")
            
    logger.info("Background job discovery cycle completed")


async def discover_jobs_network(candidate_id: int, queries: list, skills: list) -> list:
    """Performs Tier 1 and Tier 2 searches over the network without DB dependencies."""
    all_discovered = []

    # TIER 1: Direct APIs (always try first — free, reliable, no rate limits)
    logger.info(f"Candidate {candidate_id} | Tier 1 Discovery started")
    t1_tasks = [
        fetch_greenhouse_jobs(queries),
        fetch_lever_jobs(queries),
        fetch_rss_jobs(queries, skills),
    ]
    t1_results = await asyncio.gather(*t1_tasks, return_exceptions=True)
    for r in t1_results:
        if isinstance(r, list):
            all_discovered.extend(r)
            
    logger.info(f"Candidate {candidate_id} | Tier 1 found {len(all_discovered)} jobs")

    # TIER 1.5: Site-Specific Search Connectors (Naukri, Foundit, Wellfound, etc. in parallel thread pool)
    logger.info(f"Candidate {candidate_id} | Site-Specific Search Connectors started")
    from app.services.job_connectors import (
        naukri, foundit, wellfound, indeed, cutshort, hirist, internshala, instahyre, linkedin_jobs, hiring_posts
    )
    
    sync_connectors = [
        ("Naukri", naukri.fetch, (queries,)),
        ("Foundit", foundit.fetch, (queries,)),
        ("Wellfound", wellfound.fetch, (queries,)),
        ("Indeed", indeed.fetch, (queries,)),
        ("Cutshort", cutshort.fetch, (queries,)),
        ("Hirist", hirist.fetch, (queries,)),
        ("Internshala", internshala.fetch, (queries,)),
        ("Instahyre", instahyre.fetch, (queries,)),
        ("LinkedIn Jobs", linkedin_jobs.fetch, (queries,)),
        ("LinkedIn Hiring Posts", hiring_posts.fetch, (skills,)),
    ]
    
    tasks = [asyncio.to_thread(fn, *args) for name, fn, args in sync_connectors]
    connector_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for (name, _, _), r in zip(sync_connectors, connector_results):
        if isinstance(r, Exception):
            logger.error(f"Connector {name} failed: {r}")
        elif isinstance(r, list):
            logger.info(f"Connector {name} found {len(r)} jobs")
            all_discovered.extend(r)

    # TIER 2: Google Discovery (Serper / fallback search)
    if len(all_discovered) < 20:
        logger.info(f"Candidate {candidate_id} | Tier 2 Discovery triggered")
        try:
            google_jobs = await search_google_jobs(queries)
            all_discovered.extend(google_jobs)
            logger.info(f"Candidate {candidate_id} | Tier 2 found {len(google_jobs)} jobs")
        except Exception as e:
            logger.warning(f"Tier 2 Google discovery failed: {e}")

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
    resume_text = f"Roles: {', '.join(profile.preferred_roles or [])}\nDomain: {profile.domain or ''}\nSkills: {', '.join(profile.skills or [])}\nExperience: {profile.total_experience_years or 0} years"
    
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
