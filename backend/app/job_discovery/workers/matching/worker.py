import logging
import asyncio
from typing import List, Dict, Any

from app.core.event_bus import event_bus
from app.job_discovery.workers.retry import WorkerRetryHandler
from app.services.vector_store import vector_store
from app.core.database import SessionLocal
from app.models.job_models import Job, Match, CandidateAgent
from app.models.models import Candidate, CandidateProfile
from app.job_discovery.workers.matching.scoring import MatchScorer
from app.job_discovery.events.dispatcher import JobEventDispatcher

logger = logging.getLogger("app.job_discovery.workers.matching.worker")

retry_handler = WorkerRetryHandler(max_retries=3)
scorer = MatchScorer()
dispatcher = JobEventDispatcher()

async def search_matching_candidates(job_id: int) -> List[Dict[str, Any]]:
    """Retrieves the job vector from Qdrant and searches candidate_embeddings."""
    if not vector_store.enabled or not vector_store.client:
        return []
        
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        
        # 1. Fetch job vector
        def _get_vector():
            return vector_store.client.retrieve(
                collection_name="job_embeddings",
                ids=[job_id],
                with_vectors=True
            )
        res = await loop.run_in_executor(None, _get_vector)
        if not res or not res[0].vector:
            return []
        job_vector = res[0].vector
        
        # 2. Search candidate_embeddings
        def _search_candidates():
            return vector_store.client.search(
                collection_name="candidate_embeddings",
                query_vector=job_vector,
                limit=50
            )
        hits = await loop.run_in_executor(None, _search_candidates)
        
        results = []
        for hit in hits:
            if hit.payload and "candidate_id" in hit.payload:
                cid = hit.payload["candidate_id"]
                score_pct = max(0.0, min(100.0, float(hit.score) * 100.0))
                results.append({
                    "candidate_id": cid,
                    "semantic_score": round(score_pct, 2)
                })
        return results
    except Exception as e:
        logger.error(f"Failed to search matching candidates in Qdrant: {e}")
        return []

async def process_job_matching(event: dict):
    """
    Subscribed callback to process vector matches for a newly embedded job.
    """
    job_id = event.get("job_id")
    if not job_id:
        raise ValueError("Event is missing 'job_id'")

    logger.info(f"[Matching Worker] Matching Job ID {job_id} against active candidates...")

    # 1. Fetch job record
    with SessionLocal() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job ID {job_id} not found in database")
            
        job_dict = {
            "title": job.title,
            "company_name": job.company_name,
            "description": job.description or "",
            "required_skills": job.required_skills or [],
            "preferred_skills": job.preferred_skills or [],
            "experience_min_years": job.experience_min_years,
            "experience_max_years": job.experience_max_years,
            "seniority": job.seniority,
            "location": job.location,
            "country": job.country,
            "is_remote": job.is_remote,
            "quality_score": job.quality_score
        }

    # 2. Find matching candidates from Qdrant vector search
    vector_matches = await search_matching_candidates(job_id)
    if not vector_matches:
        logger.info(f"[Matching Worker] No candidates matched job ID {job_id} in vector space. Running database fallback.")
        # Fallback: Query all active candidates in Postgres and compute matches
        with SessionLocal() as db:
            active_agents = db.query(CandidateAgent).filter(CandidateAgent.status == "active").all()
            vector_matches = [{"candidate_id": a.candidate_id, "semantic_score": 50.0} for a in active_agents]

    matches_created = []

    # 3. Compute matching scores and save
    with SessionLocal() as db:
        for match_info in vector_matches:
            cand_id = match_info["candidate_id"]
            sem_score = match_info["semantic_score"]
            
            # Fetch candidate profile details
            profile = db.query(CandidateProfile).filter(CandidateProfile.candidate_id == cand_id).order_by(CandidateProfile.created_at.desc()).first()
            if not profile:
                continue
                
            candidate_dict = {
                "skills": profile.skills or [],
                "experience_years": profile.experience_years or 0.0,
                "seniority": profile.career_level or "mid",
                "locations": profile.locations or []
            }
            
            overall_score, meta = scorer.compute_match(candidate_dict, job_dict, semantic_score=sem_score)
            
            if overall_score >= 30.0:
                # Upsert match record in PostgreSQL
                match_record = db.query(Match).filter_by(candidate_id=cand_id, job_id=job_id).first()
                if not match_record:
                    match_record = Match(
                        candidate_id=cand_id,
                        job_id=job_id,
                        overall_score=overall_score,
                        skill_score=meta["skill_score"],
                        experience_score=meta["experience_score"],
                        location_score=meta["location_score"],
                        career_growth_score=meta["career_growth_score"],
                        missing_skills=meta["missing_skills"],
                        skill_gap_severity=meta["skill_gap_severity"],
                        match_reasons=meta["match_reasons"],
                        status="active"
                    )
                    db.add(match_record)
                else:
                    match_record.overall_score = overall_score
                    match_record.skill_score = meta["skill_score"]
                    match_record.experience_score = meta["experience_score"]
                    match_record.location_score = meta["location_score"]
                    match_record.career_growth_score = meta["career_growth_score"]
                    match_record.missing_skills = meta["missing_skills"]
                    match_record.skill_gap_severity = meta["skill_gap_severity"]
                    match_record.match_reasons = meta["match_reasons"]
                
                db.flush()
                matches_created.append({
                    "candidate_id": cand_id,
                    "overall_score": overall_score
                })

        # Update job lifecycle status to matched
        job_record = db.query(Job).filter(Job.id == job_id).first()
        if job_record:
            job_record.lifecycle_status = "matched"
            
        db.commit()

    # 4. Dispatch jobs.matched.v1 event
    if matches_created:
        await dispatcher.publish_matched(job_id, matches_created)
        
    logger.info(f"[Matching Worker] Completed matching for job ID {job_id}. Found {len(matches_created)} candidate matches.")

async def handle_job_embedded_event(event: dict):
    await retry_handler.execute_with_retry(
        stream="jobs.embedded.v1",
        event=event,
        handler_func=process_job_matching
    )

async def start_matching_worker():
    await event_bus.subscribe(
        stream="jobs.embedded.v1",
        handler=handle_job_embedded_event,
        consumer_name="matching_worker"
    )
    logger.info("[Matching Worker] Registered subscriber for 'jobs.embedded.v1'.")
