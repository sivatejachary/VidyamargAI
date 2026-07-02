import uuid
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import CandidateModel, CandidateProfileModel, EventOutboxModel

logger = logging.getLogger("services.candidate_service.app.repository")

class CandidateRepository:
    """
    Async query wrapper for Candidate databases.
    """
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_candidate_by_id(self, candidate_id: str) -> Optional[CandidateModel]:
        """Queries candidate by primary ID key."""
        query = select(CandidateModel).where(CandidateModel.id == candidate_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_profile_by_candidate_id(self, candidate_id: str) -> Optional[CandidateProfileModel]:
        """Queries candidate parsed profiles."""
        query = select(CandidateProfileModel).where(CandidateProfileModel.candidate_id == candidate_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_candidate(self, candidate_id: str, name: str, email: str) -> CandidateModel:
        """Saves a new Candidate account in PostgreSQL."""
        candidate = CandidateModel(id=candidate_id, name=name, email=email)
        self.db.add(candidate)
        await self.db.commit()
        logger.info(f"Candidate account created for ID: '{candidate_id}'")
        return candidate

    async def upsert_profile(
        self,
        candidate_id: str,
        summary: str,
        skills: list,
        experience: list,
        education: list
    ) -> CandidateProfileModel:
        """
        Creates or updates structured profile details, saving to candidate_profiles.
        """
        logger.info(f"Upserting candidate profile details for ID: '{candidate_id}'")
        profile = await self.get_profile_by_candidate_id(candidate_id)

        if profile is None:
            profile = CandidateProfileModel(
                id=str(uuid.uuid4()),
                candidate_id=candidate_id,
                summary=summary,
                skills_graph={"skills": skills},
                experience_graph=experience,
                education_graph=education
            )
            self.db.add(profile)
        else:
            profile.summary = summary
            profile.skills_graph = {"skills": skills}
            profile.experience_graph = experience
            profile.education_graph = education

        await self.db.commit()
        return profile

    async def insert_outbox_event(self, aggregate_type: str, aggregate_id: str, event_type: str, payload: dict):
        """
        Inserts event records directly into candidate_event_outbox inside active transactions.
        """
        event = EventOutboxModel(
            id=str(uuid.uuid4()),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload
        )
        self.db.add(event)
        # Session commit is delegated to service level transactions
        logger.info(f"Event '{event_type}' registered in local Outbox table.")
