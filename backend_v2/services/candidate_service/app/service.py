import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from .repository import CandidateRepository
from .models import CandidateProfileModel

logger = logging.getLogger("services.candidate_service.app.service")

class CandidateService:
    """
    Service coordinating transactional candidate business workflows.
    """
    def __init__(self, db_session: AsyncSession):
        self.repo = CandidateRepository(db_session)
        self.db = db_session

    async def update_candidate_profile(
        self,
        candidate_id: str,
        profile_data: Dict[str, Any]
    ) -> CandidateProfileModel:
        """
        Transactional update saving candidate profile and writing events to outbox.
        """
        logger.info(f"Service: Initiating profile update transaction for candidate: '{candidate_id}'")
        
        summary = profile_data.get("summary", "")
        skills = profile_data.get("skills", [])
        experience = profile_data.get("experience", [])
        education = profile_data.get("education", [])

        # 1. Update profile in PostgreSQL database
        profile = await self.repo.upsert_profile(
            candidate_id=candidate_id,
            summary=summary,
            skills=skills,
            experience=experience,
            education=education
        )

        # 2. Write event to local outbox in the same transaction
        event_payload = {
            "candidate_id": candidate_id,
            "skills": skills,
            "updated_at": profile.created_at.isoformat()
        }
        await self.repo.insert_outbox_event(
            aggregate_type="candidate",
            aggregate_id=candidate_id,
            event_type="candidate:profile_updated",
            payload=event_payload
        )

        # 3. Commit both actions transactionally
        await self.db.commit()
        logger.info(f"Transaction successful. Candidate '{candidate_id}' profile updated and event logged in outbox.")
        return profile
