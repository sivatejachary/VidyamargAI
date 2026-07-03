"""
VidyaMarg AI — Job Discovery Repository Layer
=============================================
Implements the Repository Pattern for all database operations.
Uses SQLAlchemy Core bulk operations for maximum throughput.
Never perform row-by-row inserts — always use bulk_insert_mappings or
execute with insert().values([...]) for production-scale performance.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import and_, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.job_discovery.domain.models import EnrichedJob, JobLifecycle, Recommendation
from app.job_discovery.infrastructure.database.models import (
    CandidateMatchORM,
    CompanyORM,
    ConnectorHealthORM,
    CrawlHistoryORM,
    JobEventORM,
    JobORM,
    JobSkillORM,
    JobSourceORM,
    RecommendationORM,
)

logger = logging.getLogger("jd.repository")


# ---------------------------------------------------------------------------
# Company Repository
# ---------------------------------------------------------------------------

class CompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_normalized_name(self, normalized_name: str) -> Optional[CompanyORM]:
        stmt = select(CompanyORM).where(CompanyORM.normalized_name == normalized_name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def bulk_upsert_companies(
        self, company_dicts: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Upserts companies by normalized_name. Returns {normalized_name: company_id}.
        """
        mapping: Dict[str, int] = {}
        for cd in company_dicts:
            existing = await self.get_by_normalized_name(cd["normalized_name"])
            if existing:
                mapping[cd["normalized_name"]] = existing.id
            else:
                orm = CompanyORM(**cd)
                self._session.add(orm)
                await self._session.flush()
                mapping[cd["normalized_name"]] = orm.id
        return mapping


# ---------------------------------------------------------------------------
# Job Source Repository
# ---------------------------------------------------------------------------

class JobSourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, name: str, display_name: str, source_type: str) -> int:
        stmt = select(JobSourceORM).where(JobSourceORM.name == name)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing.id
        new_source = JobSourceORM(
            name=name,
            display_name=display_name,
            source_type=source_type,
        )
        self._session.add(new_source)
        await self._session.flush()
        return new_source.id

    async def record_success(self, name: str, jobs_found: int) -> None:
        stmt = (
            update(JobSourceORM)
            .where(JobSourceORM.name == name)
            .values(
                last_success_at=datetime.utcnow(),
                consecutive_failures=0,
                health_score=min(1.0, JobSourceORM.health_score + 0.1),
                total_jobs_discovered=JobSourceORM.total_jobs_discovered + jobs_found,
            )
        )
        await self._session.execute(stmt)

    async def record_failure(self, name: str) -> None:
        stmt = (
            update(JobSourceORM)
            .where(JobSourceORM.name == name)
            .values(
                last_failure_at=datetime.utcnow(),
                consecutive_failures=JobSourceORM.consecutive_failures + 1,
                health_score=func.greatest(0.0, JobSourceORM.health_score - 0.2),
            )
        )
        await self._session.execute(stmt)


# ---------------------------------------------------------------------------
# Job Repository — Core CRUD & Bulk Operations
# ---------------------------------------------------------------------------

class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def external_id_exists(self, external_id: str, source_id: int) -> bool:
        """Fast existence check for deduplication."""
        stmt = select(JobORM.id).where(
            and_(JobORM.external_id == external_id, JobORM.source_id == source_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def bulk_insert_jobs(
        self, job_mappings: List[Dict[str, Any]]
    ) -> List[int]:
        """
        High-throughput bulk insert using SQLAlchemy Core.
        Returns list of inserted job IDs.
        """
        if not job_mappings:
            return []

        # Use Core INSERT for maximum throughput
        result = await self._session.execute(
            insert(JobORM).returning(JobORM.id),
            job_mappings,
        )
        ids = [row[0] for row in result.fetchall()]
        logger.info(f"Bulk inserted {len(ids)} jobs into PostgreSQL")
        return ids

    async def bulk_insert_skills(self, skill_mappings: List[Dict[str, Any]]) -> None:
        """Bulk inserts job skills normalized bridge records."""
        if not skill_mappings:
            return
        await self._session.execute(insert(JobSkillORM), skill_mappings)

    async def update_lifecycle(
        self, job_ids: List[int], status: JobLifecycle
    ) -> None:
        stmt = (
            update(JobORM)
            .where(JobORM.id.in_(job_ids))
            .values(lifecycle_status=status.value, updated_at=datetime.utcnow())
        )
        await self._session.execute(stmt)

    async def mark_embedded(self, job_id: int, vector_id: str) -> None:
        stmt = (
            update(JobORM)
            .where(JobORM.id == job_id)
            .values(
                embedding_id=vector_id,
                lifecycle_status=JobLifecycle.EMBEDDED.value,
                qdrant_sync_pending=False,
                updated_at=datetime.utcnow(),
            )
        )
        await self._session.execute(stmt)

    async def get_pending_embeddings(self, limit: int = 500) -> List[JobORM]:
        """Fetches jobs that need Qdrant embedding (qdrant_sync_pending or newly persisted)."""
        stmt = (
            select(JobORM)
            .where(
                and_(
                    JobORM.is_active == True,
                    JobORM.lifecycle_status.in_(
                        [JobLifecycle.PERSISTED.value, JobLifecycle.ENRICHED.value]
                    ),
                )
            )
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_expired_jobs(self, days: int = 60) -> List[int]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = select(JobORM.id).where(
            and_(JobORM.is_active == True, JobORM.created_at < cutoff)
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.fetchall()]

    async def archive_jobs(self, job_ids: List[int]) -> int:
        stmt = (
            update(JobORM)
            .where(JobORM.id.in_(job_ids))
            .values(
                is_active=False,
                lifecycle_status=JobLifecycle.ARCHIVED.value,
                updated_at=datetime.utcnow(),
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def get_active_jobs(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[JobORM]:
        stmt = select(JobORM).where(JobORM.is_active == True)
        if filters:
            if filters.get("country"):
                stmt = stmt.where(JobORM.country == filters["country"])
            if filters.get("is_remote"):
                stmt = stmt.where(JobORM.is_remote == True)
            if filters.get("role_category"):
                stmt = stmt.where(JobORM.role_category == filters["role_category"])
            if filters.get("seniority"):
                stmt = stmt.where(JobORM.seniority == filters["seniority"])
            if filters.get("salary_min"):
                stmt = stmt.where(JobORM.salary_min >= filters["salary_min"])
        stmt = stmt.order_by(JobORM.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, job_id: int) -> Optional[JobORM]:
        stmt = select(JobORM).where(JobORM.id == job_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Match Repository
# ---------------------------------------------------------------------------

class MatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_insert_matches(
        self, match_mappings: List[Dict[str, Any]]
    ) -> List[int]:
        if not match_mappings:
            return []
        result = await self._session.execute(
            insert(CandidateMatchORM).returning(CandidateMatchORM.id),
            match_mappings,
        )
        return [row[0] for row in result.fetchall()]

    async def get_top_matches(
        self, candidate_id: int, limit: int = 20
    ) -> List[CandidateMatchORM]:
        stmt = (
            select(CandidateMatchORM)
            .where(
                and_(
                    CandidateMatchORM.candidate_id == candidate_id,
                    CandidateMatchORM.status == "new",
                )
            )
            .order_by(CandidateMatchORM.overall_score.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Recommendation Repository
# ---------------------------------------------------------------------------

class RecommendationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_insert(
        self, rec_mappings: List[Dict[str, Any]]
    ) -> List[int]:
        if not rec_mappings:
            return []
        result = await self._session.execute(
            insert(RecommendationORM).returning(RecommendationORM.id),
            rec_mappings,
        )
        return [row[0] for row in result.fetchall()]

    async def get_unseen(self, candidate_id: int, limit: int = 50) -> List[RecommendationORM]:
        stmt = (
            select(RecommendationORM)
            .where(
                and_(
                    RecommendationORM.candidate_id == candidate_id,
                    RecommendationORM.is_seen == False,
                )
            )
            .order_by(RecommendationORM.score.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Crawl History Repository
# ---------------------------------------------------------------------------

class CrawlHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start_run(
        self, run_id: str, source_name: str
    ) -> CrawlHistoryORM:
        record = CrawlHistoryORM(
            run_id=run_id,
            source_name=source_name,
            status="running",
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def complete_run(
        self,
        run_id: str,
        source_name: str,
        status: str,
        jobs_found: int,
        jobs_saved: int,
        jobs_deduplicated: int,
        jobs_rejected: int,
        execution_ms: int,
        error_message: Optional[str] = None,
    ) -> None:
        stmt = (
            update(CrawlHistoryORM)
            .where(
                and_(
                    CrawlHistoryORM.run_id == run_id,
                    CrawlHistoryORM.source_name == source_name,
                )
            )
            .values(
                status=status,
                jobs_found=jobs_found,
                jobs_saved=jobs_saved,
                jobs_deduplicated=jobs_deduplicated,
                jobs_rejected=jobs_rejected,
                execution_ms=execution_ms,
                error_message=error_message,
                completed_at=datetime.utcnow(),
            )
        )
        await self._session.execute(stmt)


# ---------------------------------------------------------------------------
# Event Audit Log Repository
# ---------------------------------------------------------------------------

class JobEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event_dict: Dict[str, Any]) -> None:
        record = JobEventORM(
            event_type=event_dict["event_type"],
            event_id=event_dict["event_id"],
            version=event_dict.get("version", 1),
            correlation_id=event_dict.get("correlation_id"),
            trace_id=event_dict.get("trace_id"),
            producer=event_dict["producer"],
            payload=event_dict.get("payload", {}),
        )
        self._session.add(record)
        await self._session.flush()
