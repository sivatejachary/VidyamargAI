"""
Recommendation Worker — Session-outside-loop fix.

Critical bug fixed:
  Legacy: Each iteration of the `for match_item in matches` loop called
  `with SessionLocal() as db:` — opening and committing a fresh DB session
  for every single candidate. For 50 matches this means 50 transactions.

  Fix: One session wraps the entire loop. All skill-gap records,
  recommendation records, and notifications are flushed in bulk and
  committed once at the end.

Additional improvements:
  - `candidate_id` variable was referenced outside the loop scope in the
    final dispatch call, causing `UnboundLocalError` when matches==[].
    Fixed by tracking processed candidates explicitly.
  - Job record is fetched once before the loop (was queried once per iter).
  - DB session closed before dispatching the event (prevents long-held txns).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from app.core.event_bus import event_bus
from app.core.database import SessionLocal
from app.job_discovery.workers.retry import WorkerRetryHandler
from app.models.job_models import Job, Match, Recommendation, SkillGapAnalysis, AgentNotification
from app.models.models import CandidateProfile
from app.job_discovery.events.dispatcher import JobEventDispatcher

logger = logging.getLogger("app.job_discovery.workers.recommendation.worker")

retry_handler = WorkerRetryHandler(max_retries=3)
dispatcher = JobEventDispatcher()


async def process_recommendations(event: Dict[str, Any]) -> None:
    job_id = event.get("job_id")
    matches: List[Dict[str, Any]] = event.get("matches", [])

    if not job_id:
        raise ValueError("Event missing 'job_id'")
    if not matches:
        logger.info(f"[Recommendation] No matches in event for job_id={job_id}. Skipping.")
        return

    logger.info(
        f"[Recommendation] Processing {len(matches)} candidate(s) for job_id={job_id}"
    )

    processed_candidate_ids: List[int] = []

    with SessionLocal() as db:
        # ── Fetch the job ONCE before the loop ──────────────────────────────
        job_record = db.query(Job).filter(Job.id == job_id).first()
        company_name = job_record.company_name if job_record else "Tech Company"
        job_title = job_record.title if job_record else "Developer"

        # ── Batch-fetch all candidate profiles in one query ──────────────────
        candidate_ids = [m.get("candidate_id") for m in matches if m.get("candidate_id")]
        profiles_list = (
            db.query(CandidateProfile)
            .filter(CandidateProfile.candidate_id.in_(candidate_ids))
            .order_by(CandidateProfile.created_at.desc())
            .all()
        )
        # latest profile per candidate
        profile_map: Dict[int, CandidateProfile] = {}
        for p in profiles_list:
            if p.candidate_id not in profile_map:
                profile_map[p.candidate_id] = p

        # ── Process all matches inside ONE session ───────────────────────────
        for match_item in matches:
            candidate_id = match_item.get("candidate_id")
            overall_score = match_item.get("overall_score", 0.0)
            if not candidate_id:
                continue

            profile = profile_map.get(candidate_id)
            if not profile:
                logger.warning(
                    f"[Recommendation] No profile for candidate_id={candidate_id}. Skipping."
                )
                continue

            current_skills: List[str] = profile.skills or []

            # Aggregate missing skills from active matches
            all_candidate_matches = (
                db.query(Match, Job)
                .join(Job, Match.job_id == Job.id)
                .filter(
                    Match.candidate_id == candidate_id,
                    Match.status == "active",
                    Job.is_active == True,  # noqa: E712
                )
                .limit(20)
                .all()
            )
            skill_freq: Dict[str, int] = {}
            for m, _j in all_candidate_matches:
                for skill in (m.missing_skills or []):
                    skill_freq[skill] = skill_freq.get(skill, 0) + 1

            top_missing = sorted(skill_freq.items(), key=lambda x: x[1], reverse=True)[:15]
            top_missing_skills = [s for s, _ in top_missing]

            # Upsert SkillGapAnalysis
            gap_analysis = (
                db.query(SkillGapAnalysis)
                .filter_by(candidate_id=candidate_id, analysis_type="overall")
                .first()
            )
            if gap_analysis:
                gap_analysis.current_skills = current_skills
                gap_analysis.missing_skills = top_missing_skills
                gap_analysis.skill_scores = {s: max(0, 100 - f * 5) for s, f in top_missing}
                gap_analysis.overall_gap_score = len(top_missing_skills) * 8.0
                gap_analysis.version = (gap_analysis.version or 0) + 1
                gap_analysis.updated_at = datetime.utcnow()
            else:
                db.add(
                    SkillGapAnalysis(
                        candidate_id=candidate_id,
                        analysis_type="overall",
                        current_skills=current_skills,
                        required_skills=list(set(top_missing_skills)),
                        missing_skills=top_missing_skills,
                        skill_scores={s: max(0, 100 - f * 5) for s, f in top_missing},
                        overall_gap_score=len(top_missing_skills) * 8.0,
                    )
                )

            # Upsert Recommendation record
            rec_record = (
                db.query(Recommendation)
                .filter_by(candidate_id=candidate_id, rec_type="job", entity_id=job_id)
                .first()
            )
            if not rec_record:
                db.add(
                    Recommendation(
                        candidate_id=candidate_id,
                        rec_type="job",
                        entity_id=job_id,
                        entity_data={"match_score": overall_score},
                        score=overall_score,
                        reason="Vector similarity matches your skills and profile.",
                        expires_at=datetime.utcnow() + timedelta(days=7),
                    )
                )

            # Create AgentNotification
            db.add(
                AgentNotification(
                    candidate_id=candidate_id,
                    title=f"New Match: {job_title}",
                    content=(
                        f"We found a new match for you at {company_name} "
                        f"with a match score of {overall_score:.0f}%."
                    ),
                    is_read=False,
                )
            )

            processed_candidate_ids.append(candidate_id)

        # Update job lifecycle once
        if job_record:
            job_record.lifecycle_status = "recommended"

        # ── Single commit for the ENTIRE batch ───────────────────────────────
        db.commit()

    logger.info(
        f"[Recommendation] Committed recommendations for {len(processed_candidate_ids)} "
        f"candidate(s), job_id={job_id}."
    )

    # Dispatch AFTER session is closed
    if processed_candidate_ids:
        for cand_id in processed_candidate_ids:
            await dispatcher.publish_recommendation_created(cand_id, matches)


# ─── Stream wiring ────────────────────────────────────────────────────────────

async def handle_job_matched_event(event: Dict[str, Any]) -> None:
    await retry_handler.execute_with_retry(
        stream="jobs.matched.v1",
        event=event,
        handler_func=process_recommendations,
    )


async def start_recommendation_worker() -> None:
    await event_bus.subscribe(
        stream="jobs.matched.v1",
        handler=handle_job_matched_event,
        group_name="recommendation_workers_group",
        consumer_name="recommendation_worker",
    )
    logger.info("[Recommendation] Subscribed to 'jobs.matched.v1'.")
