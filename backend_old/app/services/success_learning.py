"""
Success Learning Loop — analyses job application outcomes to self-calibrate
matching thresholds, prioritize resume versions, and updates soft blacklisted/preferred companies.
"""
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.memory_models import ApplicationHistory, CandidatePreferences
from app.models.models import Candidate, CandidateResume

logger = logging.getLogger("app.success_learning")


class SuccessLearningLoop:
    """Closes the feedback loop between job application outcomes and match agent parameters."""

    def process_new_outcome(self, candidate_id: int, db: Session) -> None:
        """
        Called when a new application outcome is recorded.
        Recalculates match parameters from the candidate's outcomes.
        """
        # Fetch last 200 events in history
        history = db.query(ApplicationHistory).filter(
            ApplicationHistory.candidate_id == candidate_id
        ).order_by(ApplicationHistory.created_at.desc()).limit(200).all()

        if len(history) < 5:
            logger.info(f"Not enough outcomes for candidate {candidate_id} (found {len(history)}/5). Skipping learning loop.")
            return

        # Filter by interview outcome signals
        interviews = [h for h in history if "interview" in h.event_type]
        rejections = [h for h in history if "rejected" in h.event_type]
        responses = [h for h in history if h.event_type in ("interview_passed", "interview_rejected")]

        # 1. Update Match Score Threshold
        # If we see that the user only gets interviews at 80%+, we can raise the filter threshold to save tokens and time.
        # If they get interviews at 65%+, we can lower it.
        if interviews:
            interview_scores = [h.match_score for h in interviews if h.match_score is not None]
            if interview_scores:
                avg_interview_score = sum(interview_scores) / len(interview_scores)
                # Set threshold to avg_interview_score - 10 (floor of 60%, ceiling of 85%)
                new_threshold = max(60.0, min(85.0, avg_interview_score - 10.0))
                self._update_candidate_match_threshold(candidate_id, new_threshold, db)
                logger.info(f"Calibrated matching threshold to {new_threshold}% based on interviews.")

        # 2. Analyze Resume Performance
        # Find which resume has the highest interview rate
        resume_stats = {}
        for h in history:
            if not h.resume_id:
                continue
            rid = h.resume_id
            if rid not in resume_stats:
                resume_stats[rid] = {"apps": 0, "interviews": 0}
            resume_stats[rid]["apps"] += 1
            if "interview" in h.event_type:
                resume_stats[rid]["interviews"] += 1

        best_resume_id = None
        best_rate = -1.0
        for rid, stats in resume_stats.items():
            if stats["apps"] >= 3:  # Minimum sample size
                rate = stats["interviews"] / stats["apps"]
                if rate > best_rate:
                    best_rate = rate
                    best_resume_id = rid

        if best_resume_id:
            self._update_primary_resume(candidate_id, best_resume_id, db)
            logger.info(f"Determined best performing resume ID: {best_resume_id} (Rate: {best_rate*100:.1f}%)")

        # 3. Analyze Company Rejection Soft-Blacklisting
        # If a candidate dismisses/rejects a company 3 times, soft-blacklist it
        company_rejects = {}
        for h in history:
            if h.event_type == "job_rejected":
                company_rejects[h.company] = company_rejects.get(h.company, 0) + 1

        for company, count in company_rejects.items():
            if count >= 3:
                self._blacklist_company(candidate_id, company, db)

        db.commit()

    def _update_candidate_match_threshold(self, candidate_id: int, threshold: float, db: Session):
        """Updates the matching score filter threshold in preferences."""
        cand = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if cand:
            # We store the match threshold directly in candidate table or preferences metadata
            if not hasattr(cand, "match_threshold"):
                # Dynamically set threshold in user preferences
                pass
            # Let's save in user_preferences or metadata if exists
            # We can log this parameter to candidate profile metadata
            meta = cand.career_roadmap or {}
            if isinstance(meta, dict):
                meta["calibrated_threshold"] = threshold
                cand.career_roadmap = meta
                db.commit()

    def _update_primary_resume(self, candidate_id: int, resume_id: int, db: Session):
        """Sets the best performing resume as the primary active resume for auto-apply."""
        # Query CandidateResume and mark as primary/active
        # Check if the CandidateResume model supports active status
        resumes = db.query(CandidateResume).filter(CandidateResume.candidate_id == candidate_id).all()
        for r in resumes:
            # If the resume model has is_primary, update it
            if hasattr(r, "is_primary"):
                r.is_primary = (r.id == resume_id)
        db.commit()

    def _blacklist_company(self, candidate_id: int, company: str, db: Session):
        """Adds a company to the soft-blacklist in candidate preferences."""
        prefs = db.query(CandidatePreferences).filter(
            CandidatePreferences.candidate_id == candidate_id
        ).first()

        if not prefs:
            prefs = CandidatePreferences(candidate_id=candidate_id)
            db.add(prefs)

        blacklisted = prefs.rejected_companies or []
        if company not in blacklisted:
            blacklisted.append(company)
            prefs.rejected_companies = blacklisted
            logger.info(f"Soft-blacklisted company '{company}' for candidate {candidate_id}")
            db.commit()


success_learning = SuccessLearningLoop()
