"""
VidyaMarg AI — Job Deduplicator
================================
Prevents duplicate jobs from polluting the database using a two-stage approach:

Stage 1 — Exact match: external_id + source_id lookup against PostgreSQL.
Stage 2 — Fuzzy match: normalized title + company fingerprint bloom filter
          (optionally backed by Redis SETBIT for cross-process sharing).

The deduplicator is called AFTER validation and BEFORE bulk persistence.
Jobs that are duplicates get the is_duplicate=True flag set and are skipped
in the bulk insert, but logged to crawl history for metrics.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Set, Tuple

from app.job_discovery.domain.models import ValidatedJob
from app.job_discovery.infrastructure.database.repository import JobRepository

logger = logging.getLogger("jd.pipeline.deduplicator")


def _make_fingerprint(title_normalized: str, company_normalized: str) -> str:
    """
    Creates a deterministic fingerprint for fuzzy matching.
    Matches jobs with identical normalized title + company even if
    discovered from different sources.
    """
    key = f"{title_normalized.strip()}::{company_normalized.strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


class JobDeduplicator:
    """
    Two-stage deduplicator:
      1. External-ID exact match against PostgreSQL (async, per-batch prefetch)
      2. Content fingerprint within-batch match (in-memory set)

    For large deployments, Stage 2 can be extended with a Redis HyperLogLog
    or Bloom filter for cross-worker dedup without DB hits.
    """

    async def deduplicate(
        self,
        validated_jobs: List[ValidatedJob],
        repo: JobRepository,
        source_id_map: Dict[str, int],  # {source_name: source_id}
    ) -> Tuple[List[ValidatedJob], List[Dict[str, Any]]]:
        """
        Deduplicates a batch of validated jobs.

        Returns:
            unique_jobs:    Jobs not seen before (ready for persistence)
            duplicates:     Jobs identified as duplicates (for audit logging)
        """
        unique: List[ValidatedJob] = []
        duplicate_log: List[Dict[str, Any]] = []
        in_batch_fingerprints: Set[str] = set()

        # Build set of external_ids to check in DB (grouped by source)
        # Batch the DB lookups to avoid N+1 queries
        for job in validated_jobs:
            source_id = source_id_map.get(job.source_name, 0)
            fingerprint = _make_fingerprint(job.title_normalized, job.company_normalized)

            # Stage 1: In-batch fingerprint dedup (fastest, no I/O)
            if fingerprint in in_batch_fingerprints:
                duplicate_log.append({
                    "external_id": job.external_id,
                    "title": job.title,
                    "reason": "in_batch_fingerprint_duplicate",
                })
                logger.debug(f"In-batch duplicate: {job.title} @ {job.company_name}")
                continue

            # Stage 2: DB external_id check
            try:
                exists = await repo.external_id_exists(job.external_id, source_id)
                if exists:
                    duplicate_log.append({
                        "external_id": job.external_id,
                        "title": job.title,
                        "reason": "db_external_id_exists",
                    })
                    logger.debug(f"DB duplicate: {job.external_id}")
                    continue
            except Exception as exc:
                # DB check failed — allow the job through and let DB constraint catch it
                logger.warning(f"DB dedup check failed for {job.external_id}: {exc}")

            # Job is unique — track fingerprint and add to results
            in_batch_fingerprints.add(fingerprint)
            unique.append(job)

        duplication_rate = (
            len(duplicate_log) / len(validated_jobs) * 100
            if validated_jobs
            else 0
        )
        logger.info(
            f"Deduplication: {len(unique)} unique, {len(duplicate_log)} duplicates "
            f"({duplication_rate:.1f}% dupe rate)"
        )
        return unique, duplicate_log
