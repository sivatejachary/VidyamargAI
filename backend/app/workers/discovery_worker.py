"""
Discovery Worker — background worker that regularly discovers new jobs
for all active candidates using the 3-tier discovery architecture.
Refactored for parallel non-blocking execution, Redis caching, priority ranking,
bulk operations, and shortlisted semantic matching.
"""
import logging
import asyncio
import time
import json
import hashlib
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.models import Candidate, CandidateProfile, JobSourceTracking
from app.models.pool_models import JobPool, JobPoolMatch

# Direct API and Search Engine Connectors
from app.services.job_connectors.tier1.greenhouse_api import fetch_greenhouse_jobs
from app.services.job_connectors.tier1.lever_api import fetch_lever_jobs
from app.services.job_connectors.tier1.rss_feeds import fetch_rss_jobs
from app.services.job_connectors.tier2.google_discovery import search_google_jobs
from app.services.job_connectors import (
    ats_sources, linkedin_jobs, naukri, foundit, wellfound, indeed,
    cutshort, hirist, internshala, instahyre, hiring_posts
)
from app.agents.telegram import TelegramCommunityAgent
from app.core.config import settings
from app.agents.verification import VerificationAgent
from app.services.job_connectors.base import classify_job, LiveJob
from app.services.vector_store import vector_store
import app.services.job_cache as job_cache
from app.agents.matching_agent import calculate_match_score_and_reasons
from app.agents.resume_intelligence import CandidateProfileData

logger = logging.getLogger("app.workers.discovery")

# Scheduler Intervals Configuration (in seconds)
SOURCE_CONFIG = {
    "Telegram": 120,                # 2 minutes
    "Greenhouse": 300,              # 5 minutes
    "Lever": 300,                  # 5 minutes
    "Ashby": 300,                  # 5 minutes (Note: Ashby is checked inside ats_sources)
    "RSS Feeds": 300,              # 5 minutes
    "Workday": 900,                # 15 minutes
    "LinkedIn": 900,               # 15 minutes
    "Naukri": 900,                 # 15 minutes
    "Foundit": 900,                # 15 minutes
    "Wellfound": 900,              # 15 minutes
    "Indeed": 900,                 # 15 minutes
    "Cutshort": 900,               # 15 minutes
    "Hirist": 900,                 # 15 minutes
    "Internshala": 900,            # 15 minutes
    "Instahyre": 900,              # 15 minutes
    "LinkedIn Hiring Posts": 300,  # 5 minutes
    "Google Search Fallback": 900   # 15 minutes
}


def safe_loads(val, default=None):
    if not val:
        return default if default is not None else {}
    if isinstance(val, (list, dict)):
        return val
    if isinstance(val, str):
        try:
            res = json.loads(val)
            if isinstance(res, (list, dict)):
                return res
        except Exception:
            pass
    return default if default is not None else {}


def update_source_status(db: Session, source_name: str, success: bool, latency: float):
    try:
        tracking = db.query(JobSourceTracking).filter(JobSourceTracking.source_name == source_name).first()
        if not tracking:
            tracking = JobSourceTracking(
                source_name=source_name,
                success_count=0,
                failure_count=0,
                avg_response_time=0.0,
                status="offline"
            )
            db.add(tracking)
            
        if tracking.success_count is None:
            tracking.success_count = 0
        if tracking.failure_count is None:
            tracking.failure_count = 0
        if tracking.avg_response_time is None:
            tracking.avg_response_time = 0.0
            
        tracking.last_crawl = datetime.utcnow()
        if success:
            tracking.success_count += 1
            tracking.status = "healthy"
        else:
            tracking.failure_count += 1
            tracking.status = "degraded" if tracking.success_count > 0 else "offline"
            
        total_runs = tracking.success_count + tracking.failure_count
        if total_runs > 1:
            tracking.avg_response_time = (tracking.avg_response_time * (total_runs - 1) + latency) / total_runs
        else:
            tracking.avg_response_time = latency
            
        db.commit()
    except Exception as e:
        logger.error(f"Failed to update JobSourceTracking for {source_name}: {e}")
        db.rollback()


def bulk_insert_or_do_nothing(db: Session, model, mappings: List[dict]):
    """Dialect-specific bulk INSERT statements using ON CONFLICT DO NOTHING to prevent duplicates."""
    if not mappings:
        return
    try:
        dialect_name = db.bind.dialect.name
        if dialect_name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(model).values(mappings).on_conflict_do_nothing(index_elements=['stable_id'])
            db.execute(stmt)
        elif dialect_name == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
            stmt = sqlite_insert(model).values(mappings).on_conflict_do_nothing(index_elements=['stable_id'])
            db.execute(stmt)
        else:
            db.bulk_insert_mappings(model, mappings)
    except Exception as e:
        logger.warning(f"ON CONFLICT bulk insert failed ({e}), falling back to bulk_insert_mappings.")
        db.bulk_insert_mappings(model, mappings)


def generate_crawling_queries(roles: List[str], skills: List[str]) -> List[str]:
    """Backward compatibility fallback wrapper."""
    queries = set()
    for r in roles[:15]:
        queries.add(f'"{r}" India')
        queries.add(f'"{r}" Remote India')
    if len(queries) < 10:
        for s in skills[:10]:
            queries.add(f'"{s} Developer" India')
            queries.add(f'"{s} Engineer" India')
    return list(queries)[:30]


def get_crawler_queries_and_skills(db: Session) -> Tuple[List[str], List[str]]:
    """
    Dynamic Candidate-Driven Query Generation (No hardcoded roles).
    Ranks queries by Priority Score:
    Score = (Active Candidate Count * 5) + (Skills Match Frequency * 3)
    """
    candidates = db.query(Candidate).all()
    role_counts = {}
    skill_counts = {}
    
    for candidate in candidates:
        profile = db.query(CandidateProfile).filter(
            CandidateProfile.candidate_id == candidate.id
        ).order_by(CandidateProfile.created_at.desc()).first()
        
        # 1. Aggregate roles
        roles = []
        if profile and profile.generated_roles:
            roles = safe_loads(profile.generated_roles, [])
        elif profile and profile.current_role:
            roles = [profile.current_role]
            
        for r in roles:
            r_clean = r.strip()
            if r_clean:
                role_counts[r_clean] = role_counts.get(r_clean, 0) + 1
                
        # 2. Aggregate skills
        skills_list = []
        if profile and profile.skills_graph:
            graph = safe_loads(profile.skills_graph)
            skills_list = graph.get("primary_skills", []) + graph.get("secondary_skills", [])
        if not skills_list and profile and profile.parsed_metadata:
            meta = safe_loads(profile.parsed_metadata)
            skills_list = meta.get("skills", [])
        if not skills_list and candidate.skills:
            skills_list = [s.strip() for s in candidate.skills.split(",") if s.strip()]
            
        for s in skills_list:
            s_clean = s.strip()
            if s_clean:
                skill_counts[s_clean] = skill_counts.get(s_clean, 0) + 1

    # 3. Calculate priority scores
    candidate_queries = []
    for role, count in role_counts.items():
        score = count * 5
        candidate_queries.append((role, score))
        
    for skill, count in skill_counts.items():
        score = count * 3
        candidate_queries.append((f"{skill} Developer", score))
        candidate_queries.append((f"{skill} Engineer", score))

    # 4. Sort and deduplicate queries
    candidate_queries.sort(key=lambda x: x[1], reverse=True)
    seen_queries = set()
    ordered_queries = []
    for q_text, _ in candidate_queries:
        q_norm = q_text.lower().strip()
        if q_norm not in seen_queries:
            seen_queries.add(q_norm)
            ordered_queries.append(q_text)
            
    # 5. Format for Google/Serper-friendly search operators
    formatted_queries = []
    for q in ordered_queries:
        formatted_queries.append(f'"{q}" India')
        formatted_queries.append(f'"{q}" Remote India')
        
    # Cap queries to top 15 in this cycle for latency/cost efficiency
    final_queries = formatted_queries[:15]
    
    # Absolute fallback defaults if database is completely empty
    if not final_queries:
        final_queries = [
            '"Software Engineer" India', '"React Developer" India', 
            '"Python Developer" India', '"Data Scientist" India',
            '"Project Manager" India', '"Civil Engineer" India'
        ]
        
    sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
    final_skills = [item[0] for item in sorted_skills[:30]]
    if not final_skills:
        final_skills = ["Python", "JavaScript", "React", "SQL", "Project Management"]
        
    return final_queries, final_skills


async def get_due_sources(db: Session) -> List[str]:
    """Check db source tracking to see which crawlers are due for scheduled run."""
    due = []
    now = datetime.utcnow()
    trackings = {t.source_name: t for t in db.query(JobSourceTracking).all()}
    
    for source, interval in SOURCE_CONFIG.items():
        tracking = trackings.get(source)
        if not tracking:
            due.append(source)
        else:
            elapsed = (now - tracking.last_crawl).total_seconds()
            if elapsed >= interval:
                due.append(source)
    return due


async def run_discovery_all_candidates():
    """Main crawler entry point. Orchestrates parallel source crawling, inserts jobs in bulk, and schedules matching."""
    logger.info("Starting candidate-independent background job discovery cycle")
    db = SessionLocal()
    try:
        # 1. Dynamic aggregate query construction
        queries, skills = get_crawler_queries_and_skills(db)
        
        # 2. Parallel scheduled source crawling
        discovered_jobs = await discover_jobs_network_independent(db, queries, skills, force_run=False)
        
        if discovered_jobs:
            logger.info(f"Deduplicating {len(discovered_jobs)} discovered jobs against db")
            
            # Preload existing stable_ids once to prevent O(N) database queries
            existing_ids = {row[0] for row in db.query(JobPool.stable_id).all()}
            added_stable_ids = set()
            
            jobs_data = []
            for job in discovered_jobs:
                if job.stable_id not in existing_ids and job.stable_id not in added_stable_ids:
                    added_stable_ids.add(job.stable_id)
                    classification = classify_job(job.title, job.description or "", job.skills or [])
                    jobs_data.append({
                        "stable_id": job.stable_id,
                        "title": job.title,
                        "company": job.company,
                        "location": job.location,
                        "experience": job.experience,
                        "skills": job.skills,
                        "apply_url": job.apply_url,
                        "posted_date": job.posted_date,
                        "source": job.source,
                        "description": job.description,
                        "work_mode": job.work_mode,
                        "company_logo": job.company_logo,
                        "domain": classification["domain"],
                        "job_type": classification["job_type"],
                        "career_level": classification["career_level"],
                        "all_sources": getattr(job, "all_sources", [job.source])
                    })
                    
            if jobs_data:
                # Bulk DB insert with dialect-specific duplicate bypass
                bulk_insert_or_do_nothing(db, JobPool, jobs_data)
                db.commit()
                logger.info(f"Bulk inserted {len(jobs_data)} new unique jobs into jobs_pool")
                
                # Retrieve matching IDs in a single bulk query for Qdrant indexing
                newly_inserted_stable_ids = [j["stable_id"] for j in jobs_data]
                new_jobs = db.query(JobPool).filter(JobPool.stable_id.in_(newly_inserted_stable_ids)).all()
                
                # Upsert to Qdrant
                try:
                    for j in new_jobs:
                        await vector_store.upsert_job(
                            job_id=j.id,
                            title=j.title,
                            company=j.company,
                            description=j.description,
                            skills=j.skills
                        )
                    logger.info(f"Upserted {len(new_jobs)} jobs to Qdrant vector store")
                except Exception as q_err:
                    logger.error(f"Failed to upsert jobs to Qdrant: {q_err}")
                
                # Non-blocking Worker Split: trigger matching pipeline in a background task
                new_job_ids = [j.id for j in new_jobs]
                asyncio.create_task(run_matching_pipeline_for_jobs(new_job_ids))
                
    except Exception as e:
        logger.error(f"Error in run_discovery_all_candidates background worker: {e}")
    finally:
        db.close()
    logger.info("Background job discovery cycle completed")


async def discover_jobs_network_independent(db: Session, queries: list, skills: list, force_run: bool = False) -> list:
    """Orchestrates all source crawlers concurrently bounded by a Semaphore concurrency pool."""
    all_discovered = []
    
    # 1. Determine scheduled due sources
    due_sources = SOURCE_CONFIG.keys() if force_run else await get_due_sources(db)
    if not due_sources:
        logger.info("No crawler sources are due for execution in this cycle.")
        return []
        
    logger.info(f"Executing due sources concurrently: {list(due_sources)}")
    
    # 2. Controlled Concurrency Layer (bounded worker pool)
    concurrency_limit = getattr(settings, "CONCURRENT_SEARCH_WORKERS", 30)
    sem = asyncio.Semaphore(concurrency_limit)
    
    async def sem_run(source_name: str, crawl_fn, args, is_async: bool):
        async with sem:
            # Check Redis search results cache
            cache_key = f"{source_name}:{hashlib.md5(str(args).encode()).hexdigest()}"
            try:
                cached_data = await job_cache.get_search_results(source_name, cache_key)
                if cached_data is not None:
                    logger.debug(f"Redis cache hit for crawler '{source_name}'. Bypassing request.")
                    jobs = [LiveJob(**j) for j in cached_data]
                    return jobs, source_name, True, 0.0
            except Exception as ce:
                logger.warning(f"Failed to fetch Redis search cache for {source_name}: {ce}")
            
            # Fetch / Execute crawling
            start_time = time.time()
            try:
                logger.info(f"Running crawler: {source_name}")
                if is_async:
                    res = await crawl_fn(*args)
                else:
                    res = await asyncio.to_thread(crawl_fn, *args)
                latency = time.time() - start_time
                logger.info(f"Crawler '{source_name}' completed. Fetched {len(res) if res else 0} jobs in {latency:.2f}s")
                
                # Write to Redis search results cache (TTL: 1 hour)
                if res:
                    try:
                        serializable = [
                            {
                                "title": j.title,
                                "company": j.company,
                                "location": j.location,
                                "experience": j.experience,
                                "skills": j.skills,
                                "apply_url": j.apply_url,
                                "posted_date": j.posted_date,
                                "source": j.source,
                                "description": j.description,
                                "work_mode": j.work_mode,
                                "company_logo": j.company_logo
                            }
                            for j in res
                        ]
                        await job_cache.set_search_results(source_name, cache_key, serializable)
                    except Exception as cse:
                        logger.warning(f"Failed to cache search results in Redis for {source_name}: {cse}")
                        
                return res, source_name, True, latency
            except Exception as e:
                latency = time.time() - start_time
                logger.error(f"Crawler '{source_name}' failed: {e}")
                return [], source_name, False, latency

    # 3. Assemble async tasks
    tasks = []
    
    if "Greenhouse" in due_sources:
        tasks.append(sem_run("Greenhouse", fetch_greenhouse_jobs, (queries,), is_async=True))
    if "Lever" in due_sources:
        tasks.append(sem_run("Lever", fetch_lever_jobs, (queries,), is_async=True))
    if "Workday" in due_sources or "Ashby" in due_sources:
        tasks.append(sem_run("Workday", ats_sources.fetch, (queries,), is_async=False))
    if "LinkedIn" in due_sources:
        tasks.append(sem_run("LinkedIn", linkedin_jobs.fetch, (queries,), is_async=False))
    if "Naukri" in due_sources:
        tasks.append(sem_run("Naukri", naukri.fetch, (queries,), is_async=False))
    if "Telegram" in due_sources:
        tg_agent = TelegramCommunityAgent(db)
        tasks.append(sem_run("Telegram", tg_agent.async_collect_jobs, (), is_async=True))
    if "Foundit" in due_sources:
        tasks.append(sem_run("Foundit", foundit.fetch, (queries,), is_async=False))
    if "Wellfound" in due_sources:
        tasks.append(sem_run("Wellfound", wellfound.fetch, (queries,), is_async=False))
    if "Indeed" in due_sources:
        tasks.append(sem_run("Indeed", indeed.fetch, (queries,), is_async=False))
    if "Cutshort" in due_sources:
        tasks.append(sem_run("Cutshort", cutshort.fetch, (queries,), is_async=False))
    if "Hirist" in due_sources:
        tasks.append(sem_run("Hirist", hirist.fetch, (queries,), is_async=False))
    if "Internshala" in due_sources:
        tasks.append(sem_run("Internshala", internshala.fetch, (queries,), is_async=False))
    if "Instahyre" in due_sources:
        tasks.append(sem_run("Instahyre", instahyre.fetch, (queries,), is_async=False))
    if "LinkedIn Hiring Posts" in due_sources:
        tasks.append(sem_run("LinkedIn Hiring Posts", hiring_posts.fetch, (skills,), is_async=False))
    if "RSS Feeds" in due_sources:
        tasks.append(sem_run("RSS Feeds", fetch_rss_jobs, (queries, skills), is_async=True))
    if "Google Search Fallback" in due_sources:
        tasks.append(sem_run("Google Search Fallback", search_google_jobs, (queries,), is_async=True))

    # 4. Gather crawler executions
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for r in results:
        if isinstance(r, tuple):
            jobs, name, success, latency = r
            all_discovered.extend(jobs)
            # Update metric status sequentially on main thread (thread-safe for sessions)
            update_source_status(db, name, success, latency)
        elif isinstance(r, Exception):
            logger.error(f"Concurrency gather returned exception: {r}")

    # 5. Apply verifier deduplication
    verifier = VerificationAgent(all_discovered)
    verified_jobs = verifier.verify_and_deduplicate()
    
    return verified_jobs


async def save_and_match_discovered_jobs(candidate_id: int, candidate_skills: list, unique_jobs: list):
    """Saves discovered jobs and schedules matching. Maintained for backward compatibility."""
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            logger.warning(f"Candidate {candidate_id} not found when saving jobs")
            return

        logger.info(f"Candidate {candidate_id} | Ingesting {len(unique_jobs)} discovered jobs to pool")
        
        existing_ids = {row[0] for row in db.query(JobPool.stable_id).all()}
        added_stable_ids = set()
        
        jobs_data = []
        for job in unique_jobs:
            if job.stable_id not in existing_ids and job.stable_id not in added_stable_ids:
                added_stable_ids.add(job.stable_id)
                classification = classify_job(job.title, job.description or "", job.skills or [])
                jobs_data.append({
                    "stable_id": job.stable_id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "experience": job.experience,
                    "skills": job.skills,
                    "apply_url": job.apply_url,
                    "posted_date": job.posted_date,
                    "source": job.source,
                    "description": job.description,
                    "work_mode": job.work_mode,
                    "company_logo": job.company_logo,
                    "domain": classification["domain"],
                    "job_type": classification["job_type"],
                    "career_level": classification["career_level"],
                    "all_sources": getattr(job, "all_sources", [job.source])
                })
                
        if jobs_data:
            bulk_insert_or_do_nothing(db, JobPool, jobs_data)
            db.commit()
            logger.info(f"Saved {len(jobs_data)} new unique jobs")
            
            newly_inserted_stable_ids = [j["stable_id"] for j in jobs_data]
            new_jobs = db.query(JobPool).filter(JobPool.stable_id.in_(newly_inserted_stable_ids)).all()
            
            try:
                for j in new_jobs:
                    await vector_store.upsert_job(
                        job_id=j.id,
                        title=j.title,
                        company=j.company,
                        description=j.description,
                        skills=j.skills
                    )
            except Exception as q_err:
                logger.error(f"Error upserting jobs to Qdrant: {q_err}")
                
            new_job_ids = [j.id for j in new_jobs]
            asyncio.create_task(run_matching_pipeline_for_jobs(new_job_ids))
        else:
            # Trigger matching even if no new jobs added
            await match_pool_jobs_for_candidate(candidate, db, candidate_skills)
            
    except Exception as e:
        logger.error(f"Error in save_and_match_discovered_jobs for candidate {candidate_id}: {e}")
        db.rollback()
    finally:
        db.close()


def check_rules_match(profile: Any, job: JobPool) -> bool:
    """Rule-Based Filter: Checks Domain, Location, Work Mode, and Experience criteria in-memory (<1ms)."""
    # 1. Domain match
    profile_domain = getattr(profile, "domain", "Other")
    job_domain = getattr(job, "domain", "Other")
    if profile_domain and job_domain and profile_domain != "Other" and job_domain != "Other":
        if profile_domain.lower() != job_domain.lower():
            return False
            
    # 2. Location & Work mode
    job_work_mode = getattr(job, "work_mode", "On-site")
    if job_work_mode != "Remote":
        job_loc = (getattr(job, "location", "") or "").lower()
        candidate_locs = [loc.lower() for loc in (getattr(profile, "locations", []) or []) if loc]
        if candidate_locs and not any(loc in job_loc for loc in candidate_locs):
            return False
            
    # 3. Experience level match
    experience_years = getattr(profile, "experience_years", 0.0) or 0.0
    job_exp_str = (getattr(job, "experience", "") or "").lower()
    
    if "fresher" in job_exp_str or "0-1" in job_exp_str:
        if experience_years > 3.0:
            return False
    elif "5+" in job_exp_str or "senior" in job_exp_str:
        if experience_years < 4.0:
            return False
    elif "3-5" in job_exp_str:
        if experience_years < 2.0 or experience_years > 7.0:
            return False
            
    return True


async def run_matching_pipeline_for_jobs(new_job_ids: List[int]):
    """Background Match Worker: Processes candidate matching for new crawler discoveries."""
    logger.info(f"Triggering background matching worker for {len(new_job_ids)} new jobs")
    db = SessionLocal()
    try:
        candidates = db.query(Candidate).all()
        for candidate in candidates:
            profile_rec = db.query(CandidateProfile).filter(
                CandidateProfile.candidate_id == candidate.id
            ).order_by(CandidateProfile.created_at.desc()).first()
            
            cand_skills = []
            if profile_rec and profile_rec.parsed_metadata:
                try:
                    meta = safe_loads(profile_rec.parsed_metadata)
                    cand_skills = meta.get("skills", [])
                except Exception:
                    pass
            if not cand_skills and candidate.skills:
                cand_skills = [s.strip() for s in candidate.skills.split(",") if s.strip()]
                
            try:
                await match_pool_jobs_for_candidate(candidate, db, cand_skills, new_job_ids)
            except Exception as e:
                logger.error(f"Background matching failed for candidate {candidate.id}: {e}")
    except Exception as e:
        logger.error(f"Error in background matching pipeline: {e}")
    finally:
        db.close()


async def match_pool_jobs_for_candidate(candidate: Candidate, db: Session, candidate_skills: list, new_job_ids: List[int] = None):
    """
    Computes matching scores.
    Qdrant Optimization / Heuristic:
    1. Primary: Top 20 semantic jobs from Qdrant.
    2. Secondary: Top 20 matching domain jobs.
    3. Tertiary: Top 10 newest jobs.
    4. Merge + deduplicate into max 50 jobs shortlist.
    5. Filter shortlist by Domain, Exp, Location, and Work Mode (Rule-Based Filter).
    6. Send only top 15 remaining jobs to LLM Scoring.
    7. Bulk save match scores.
    """
    profile_rec = db.query(CandidateProfile).filter(
        CandidateProfile.candidate_id == candidate.id
    ).order_by(CandidateProfile.created_at.desc()).first()
    
    if profile_rec:
        try:
            preferred_roles = safe_loads(profile_rec.generated_roles, []) if profile_rec.generated_roles else []
        except Exception:
            preferred_roles = []
            
        try:
            graph = safe_loads(profile_rec.skills_graph) if profile_rec.skills_graph else {}
            skills = graph.get("primary_skills", []) + graph.get("secondary_skills", [])
        except Exception:
            skills = []
            
        if not skills and profile_rec.parsed_metadata:
            try:
                meta = safe_loads(profile_rec.parsed_metadata)
                skills = meta.get("skills", [])
            except Exception:
                pass
                
        if not skills:
            skills = candidate_skills
            
        profile = CandidateProfileData(
            skills=skills,
            experience_years=profile_rec.experience_years or 0.0,
            education=candidate.education or "",
            projects=candidate.projects or "[]",
            certifications=[s.strip() for s in (candidate.certifications or "").split(",") if s.strip()],
            summary=candidate.summary or "",
            domain=profile_rec.specialization or profile_rec.industry or "Software Engineering",
            preferred_roles=preferred_roles,
            locations=[candidate.address] if candidate.address else []
        )
    else:
        profile = CandidateProfileData(
            skills=candidate_skills if candidate_skills else ["Python", "JavaScript", "React", "SQL"],
            experience_years=0.0,
            education=candidate.education or "",
            projects=candidate.projects or "[]",
            certifications=[s.strip() for s in (candidate.certifications or "").split(",") if s.strip()],
            summary=candidate.summary or "",
            domain="Software Engineering",
            preferred_roles=[],
            locations=[candidate.address] if candidate.address else []
        )
        
    roles = profile.preferred_roles or []
    if isinstance(roles, str):
        roles = [r.strip() for r in roles.split(",") if r.strip()]
    roles_text = ", ".join(roles)

    skills = profile.skills or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    skills_text = ", ".join(skills)

    resume_text = f"Roles: {roles_text}\nDomain: {profile.domain or ''}\nSkills: {skills_text}\nExperience: {profile.experience_years or 0} years"
    
    # --- Multi-Stage Shortlist Retrieval (Target: 50 Jobs Max) ---
    semantic_job_ids = []
    if vector_store.enabled:
        try:
            semantic_job_ids = await vector_store.search_jobs(resume_text, limit=20)
        except Exception as q_err:
            logger.warning(f"Qdrant retrieval failed: {q_err}")

    # Fetch Top 20 domain-matched jobs from DB
    domain_jobs = db.query(JobPool).filter(
        JobPool.domain == profile.domain
    ).order_by(JobPool.id.desc()).limit(20).all()
    domain_job_ids = [j.id for j in domain_jobs]

    # Fetch Top 10 newest jobs from DB
    newest_jobs = db.query(JobPool).order_by(JobPool.id.desc()).limit(10).all()
    newest_job_ids = [j.id for j in newest_jobs]

    # Merge and deduplicate
    shortlist_ids = []
    seen_ids = set()
    for jid in semantic_job_ids + domain_job_ids + newest_job_ids:
        if jid not in seen_ids:
            seen_ids.add(jid)
            shortlist_ids.append(jid)
    shortlist_ids = shortlist_ids[:50]
    
    # Incremental match optimization: filter by new crawler discoveries if specified
    if new_job_ids is not None:
        new_ids_set = set(new_job_ids)
        shortlist_ids = [jid for jid in shortlist_ids if jid in new_ids_set]
        
    if not shortlist_ids:
        return

    # Check already scored matches to prevent duplicate LLM processing
    already_matched = {
        row[0] for row in db.query(JobPoolMatch.job_pool_id).filter(
            JobPoolMatch.candidate_id == candidate.id
        ).all()
    }
    unmatched_shortlist_ids = [jid for jid in shortlist_ids if jid not in already_matched]
    
    if not unmatched_shortlist_ids:
        return
        
    # Fetch job records in bulk
    unmatched_jobs = db.query(JobPool).filter(JobPool.id.in_(unmatched_shortlist_ids)).all()
    job_map = {j.id: j for j in unmatched_jobs}
    unmatched_jobs = [job_map[jid] for jid in unmatched_shortlist_ids if jid in job_map]
    
    # --- Rule-Based Shortlisting (Target: 15 Jobs Max) ---
    rule_matched_jobs = [job for job in unmatched_jobs if check_rules_match(profile, job)]
    rule_matched_jobs = rule_matched_jobs[:15]
    
    if not rule_matched_jobs:
        return

    logger.info(f"Candidate {candidate.id} | LLM scoring for {len(rule_matched_jobs)} shortlisted jobs (out of {len(unmatched_jobs)})")
    
    matches = []
    for job in rule_matched_jobs:
        res = calculate_match_score_and_reasons(
            profile=profile,
            job_title=job.title,
            job_description=job.description,
            job_skills_list=job.skills or [],
            job_experience_str=job.experience
        )
        score = res["match_score"]
        opp_score = score
        
        matches.append({
            "candidate_id": candidate.id,
            "job_pool_id": job.id,
            "match_score": score,
            "opportunity_score": opp_score,
            "skills_gap": ",".join(res["missing_skills"]),
            "reasons_json": res["reasons"],
            "should_apply": opp_score >= 70.0,
            "created_at": datetime.utcnow()
        })
        
    if matches:
        db.bulk_insert_mappings(JobPoolMatch, matches)
        db.commit()
        logger.info(f"Candidate {candidate.id} | Bulk saved {len(matches)} matches.")
        
        # Invalidate jobs pool and skill gap cache
        try:
            await job_cache.invalidate_jobs_pool(candidate.id)
            await job_cache.invalidate_skill_gap(candidate.id)
        except Exception as e:
            logger.warning(f"Failed to invalidate cache after matching: {e}")


async def run_discovery_for_candidate(candidate_id: int):
    """Targeted crawler run specifically triggered right after resume parsing."""
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            logger.error(f"Candidate {candidate_id} not found for targeted discovery")
            return
            
        profile = db.query(CandidateProfile).filter(
            CandidateProfile.candidate_id == candidate_id
        ).order_by(CandidateProfile.created_at.desc()).first()
        
        queries = set()
        skills = set()
        
        if profile:
            roles = []
            if profile.generated_roles:
                try:
                    roles = safe_loads(profile.generated_roles, [])
                except Exception:
                    pass
            if roles:
                queries.update(roles)
            elif profile.current_role:
                queries.add(profile.current_role)
                
            cand_skills = []
            if profile.skills_graph:
                try:
                    graph = safe_loads(profile.skills_graph)
                    cand_skills = graph.get("primary_skills", []) + graph.get("secondary_skills", [])
                except Exception:
                    pass
            if not cand_skills and profile.parsed_metadata:
                try:
                    meta = safe_loads(profile.parsed_metadata)
                    cand_skills = meta.get("skills", [])
                except Exception:
                    pass
            if cand_skills:
                skills.update(cand_skills)
            elif candidate.skills:
                skills.update([s.strip() for s in candidate.skills.split(",") if s.strip()])
        else:
            if candidate.skills:
                skills.update([s.strip() for s in candidate.skills.split(",") if s.strip()])
                
        # Generate dynamic queries
        generated_queries = generate_crawling_queries(list(queries), list(skills))
        
        discovered_jobs = []
        if generated_queries:
            # Force crawl immediately bypassing scheduled source status
            discovered_jobs = await discover_jobs_network_independent(db, generated_queries, list(skills)[:30], force_run=True)
            
        candidate_skills_list = list(skills)
        await save_and_match_discovered_jobs(candidate_id, candidate_skills_list, discovered_jobs)
        
    except Exception as e:
        logger.error(f"Targeted discovery failed for candidate {candidate_id}: {e}")
    finally:
        db.close()

