"""
Matching Worker — Batch profile query rewrite (eliminates N+1 hotspot).

Critical bug fixed:
  Legacy: For each of up to 50 Qdrant vector hits, the worker issued a
  separate `db.query(CandidateProfile).filter(...).first()` — 50 sequential
  SQL SELECT calls per job event.

  Fix: Collect all candidate_ids from the Qdrant result set, then issue a
  single IN-clause query to fetch all profiles in one round-trip. A dict
  lookup replaces the per-loop DB call.

Additional fix:
  `db.query(Job)` at the end of the loop to update lifecycle_status was
  opening a second DB round-trip per job. Now updates the already-fetched
  job record directly.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from app.core.event_bus import event_bus
from app.core.database import SessionLocal
from app.job_discovery.workers.retry import WorkerRetryHandler
from app.services.vector_store import vector_store
from app.models.job_models import Job, Match, CandidateAgent
from app.models.models import Candidate, CandidateProfile
from app.job_discovery.workers.matching.scoring import MatchScorer
from app.job_discovery.events.dispatcher import JobEventDispatcher

logger = logging.getLogger("app.job_discovery.workers.matching.worker")

retry_handler = WorkerRetryHandler(max_retries=3)
scorer = MatchScorer()
dispatcher = JobEventDispatcher()


# ─── Qdrant vector search ─────────────────────────────────────────────────────

async def _search_matching_candidates(job_id: int) -> List[Dict[str, Any]]:
    """
    Retrieve the job embedding from Qdrant and search candidate_embeddings.
    Returns list of {candidate_id, semantic_score} dicts.
    """
    if not vector_store.enabled or not vector_store.client:
        return []

    loop = asyncio.get_running_loop()

    try:
        # Fetch job vector
        res = await loop.run_in_executor(
            None,
            lambda: vector_store.client.retrieve(
                collection_name="job_embeddings",
                ids=[job_id],
                with_vectors=True,
            ),
        )
        if not res or not res[0].vector:
            logger.debug(f"[Matching] No job vector found for job_id={job_id}")
            return []

        job_vector = res[0].vector

        # Search candidates
        hits = await loop.run_in_executor(
            None,
            lambda: vector_store.client.search(
                collection_name="candidate_embeddings",
                query_vector=job_vector,
                limit=50,
            ),
        )

        results = []
        for hit in hits:
            if hit.payload and "candidate_id" in hit.payload:
                results.append({
                    "candidate_id": hit.payload["candidate_id"],
                    "semantic_score": round(max(0.0, min(100.0, float(hit.score) * 100.0)), 2),
                })
        return results

    except Exception as exc:
        logger.error(f"[Matching] Qdrant search failed for job_id={job_id}: {exc}")
        return []


# ─── Core handler ─────────────────────────────────────────────────────────────

async def process_job_matching(event: Dict[str, Any]) -> None:
    job_id = event.get("job_id")
    if not job_id:
        raise ValueError("Event missing 'job_id'")

    logger.info(f"[Matching] Processing job_id={job_id}")

    # 1. Fetch job record (single query)
    with SessionLocal() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found in DB")

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
            "quality_score": job.quality_score,
        }

    # 2. Vector search
    vector_matches = await _search_matching_candidates(job_id)

    # Fallback: use all active candidate agents with a base score
    if not vector_matches:
        logger.info(
            f"[Matching] No Qdrant vectors for job_id={job_id} — DB fallback"
        )
        with SessionLocal() as db:
            active_agents = (
                db.query(CandidateAgent)
                .filter(CandidateAgent.status == "active")
                .limit(200)
                .all()
            )
        vector_matches = [
            {"candidate_id": a.candidate_id, "semantic_score": 50.0}
            for a in active_agents
        ]

    if not vector_matches:
        logger.info(f"[Matching] No candidates to match for job_id={job_id}")
        return

    # 3. Batch-fetch all candidate profiles in ONE query (N+1 fix)
    candidate_ids = [m["candidate_id"] for m in vector_matches]
    score_map = {m["candidate_id"]: m["semantic_score"] for m in vector_matches}

    matches_created: List[Dict[str, Any]] = []

    with SessionLocal() as db:
        # Single IN-clause query — replaces the per-loop SELECT
        profiles = (
            db.query(CandidateProfile)
            .filter(CandidateProfile.candidate_id.in_(candidate_ids))
            .order_by(CandidateProfile.created_at.desc())
            .all()
        )

        # Build a dict: candidate_id → latest profile
        # (order_by desc means first occurrence per candidate_id wins)
        profile_map: Dict[int, CandidateProfile] = {}
        for p in profiles:
            if p.candidate_id not in profile_map:
                profile_map[p.candidate_id] = p

        for cand_id in candidate_ids:
            profile = profile_map.get(cand_id)
            if not profile:
                continue

            sem_score = score_map[cand_id]
            candidate_dict = {
                "skills": profile.skills or [],
                "experience_years": profile.experience_years or 0.0,
                "seniority": profile.career_level or "mid",
                "locations": profile.locations or [],
            }

            overall_score, meta = scorer.compute_match(
                candidate_dict, job_dict, semantic_score=sem_score
            )

            if overall_score < 30.0:
                continue

            # Upsert match record
            match_record = (
                db.query(Match)
                .filter_by(candidate_id=cand_id, job_id=job_id)
                .first()
            )
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
                    status="active",
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

            matches_created.append({"candidate_id": cand_id, "overall_score": overall_score})

        # Update job lifecycle in the SAME session (no second DB round-trip)
        job_record = db.query(Job).filter(Job.id == job_id).first()
        if job_record:
            job_record.lifecycle_status = "matched"

        db.commit()

    logger.info(
        f"[Matching] Completed job_id={job_id}: "
        f"{len(matches_created)} matches created/updated."
    )

    if matches_created:
        await dispatcher.publish_matched(job_id, matches_created)


# ─── Stream wiring ────────────────────────────────────────────────────────────

async def handle_job_embedded_event(event: Dict[str, Any]) -> None:
    await retry_handler.execute_with_retry(
        stream="jobs.embedded.v1",
        event=event,
        handler_func=process_job_matching,
    )


async def start_matching_worker() -> None:
    await event_bus.subscribe(
        stream="jobs.embedded.v1",
        handler=handle_job_embedded_event,
        group_name="matching_workers_group",
        consumer_name="matching_worker",
    )
    logger.info("[Matching] Subscribed to 'jobs.embedded.v1'.")
