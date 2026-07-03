import logging
from datetime import datetime, timedelta
from app.core.event_bus import event_bus
from app.job_discovery.workers.retry import WorkerRetryHandler
from app.core.database import SessionLocal
from app.models.job_models import Job, Match, Recommendation, SkillGapAnalysis, AgentNotification
from app.models.models import CandidateProfile
from app.job_discovery.events.dispatcher import JobEventDispatcher

logger = logging.getLogger("app.job_discovery.workers.recommendation.worker")

retry_handler = WorkerRetryHandler(max_retries=3)
dispatcher = JobEventDispatcher()

async def process_recommendations(event: dict):
    """
    Callback function that runs skill gap analysis and generates recommendation profiles.
    """
    job_id = event.get("job_id")
    matches = event.get("matches", [])
    if not job_id:
        raise ValueError("Event is missing 'job_id'")
        
    logger.info(f"[Recommendation Worker] Processing recommendations for job ID {job_id}...")

    # We will process recommendations for each matched candidate
    for match_item in matches:
        candidate_id = match_item.get("candidate_id")
        overall_score = match_item.get("overall_score")
        if not candidate_id:
            continue

        with SessionLocal() as db:
            # 1. Fetch Candidate Profile details
            profile = db.query(CandidateProfile).filter(CandidateProfile.candidate_id == candidate_id).order_by(CandidateProfile.created_at.desc()).first()
            if not profile:
                logger.warning(f"Profile not found for candidate ID {candidate_id}")
                continue

            current_skills = profile.skills or []

            # 2. Get active matches for this candidate to run aggregate skill gap analysis
            all_candidate_matches = (
                db.query(Match, Job)
                .join(Job, Match.job_id == Job.id)
                .filter(Match.candidate_id == candidate_id, Match.status == "active", Job.is_active == True)
                .limit(20)
                .all()
            )

            # Aggregate missing skills
            skill_freq = {}
            for m, j in all_candidate_matches:
                for skill in (m.missing_skills or []):
                    skill_freq[skill] = skill_freq.get(skill, 0) + 1

            top_missing = sorted(skill_freq.items(), key=lambda x: x[1], reverse=True)[:15]
            top_missing_skills = [s for s, _ in top_missing]

            # 3. Create or update SkillGapAnalysis
            gap_analysis = db.query(SkillGapAnalysis).filter_by(candidate_id=candidate_id, analysis_type="overall").first()
            if gap_analysis:
                gap_analysis.current_skills = current_skills
                gap_analysis.missing_skills = top_missing_skills
                gap_analysis.skill_scores = {s: (100 - f * 5) for s, f in top_missing}
                gap_analysis.overall_gap_score = len(top_missing_skills) * 8.0
                gap_analysis.version = (gap_analysis.version or 0) + 1
                gap_analysis.updated_at = datetime.utcnow()
            else:
                gap_analysis = SkillGapAnalysis(
                    candidate_id=candidate_id,
                    analysis_type="overall",
                    current_skills=current_skills,
                    required_skills=list(set(top_missing_skills)),
                    missing_skills=top_missing_skills,
                    skill_scores={s: (100 - f * 5) for s, f in top_missing},
                    overall_gap_score=len(top_missing_skills) * 8.0
                )
                db.add(gap_analysis)

            # 4. Generate Recommendation record for this job
            rec_record = db.query(Recommendation).filter_by(candidate_id=candidate_id, rec_type="job", entity_id=job_id).first()
            if not rec_record:
                rec_record = Recommendation(
                    candidate_id=candidate_id,
                    rec_type="job",
                    entity_id=job_id,
                    entity_data={
                        "match_score": overall_score,
                    },
                    score=overall_score,
                    reason=f"Vector similarity matches your skills and profile.",
                    expires_at=datetime.utcnow() + timedelta(days=7)
                )
                db.add(rec_record)

            # 5. Create AgentNotification record
            job_record = db.query(Job).filter(Job.id == job_id).first()
            company_name = job_record.company_name if job_record else "Tech Company"
            job_title = job_record.title if job_record else "Developer"
            
            notification = AgentNotification(
                candidate_id=candidate_id,
                title=f"New High-Score Match: {job_title}",
                content=f"We discovered a new match for you at {company_name} with an overall match score of {overall_score}%.",
                is_read=False
            )
            db.add(notification)

            # 6. Update job status to recommended
            if job_record:
                job_record.lifecycle_status = "recommended"

            db.commit()

    # 7. Dispatch recommendations.created.v1 event
    await dispatcher.publish_recommendation_created(candidate_id, matches)
    logger.info(f"[Recommendation Worker] Recommendations created successfully for job ID {job_id}.")

async def handle_job_matched_event(event: dict):
    await retry_handler.execute_with_retry(
        stream="jobs.matched.v1",
        event=event,
        handler_func=process_recommendations
    )

async def start_recommendation_worker():
    await event_bus.subscribe(
        stream="jobs.matched.v1",
        handler=handle_job_matched_event,
        consumer_name="recommendation_worker"
    )
    logger.info("[Recommendation Worker] Registered subscriber for 'jobs.matched.v1'.")
