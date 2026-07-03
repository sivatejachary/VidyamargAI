"""
VidyaMarg AI — Job Validator
==============================
Enforces structural quality gates on NormalizedJob entities.
Jobs that fail validation are rejected with a reason logged to the
crawl history for auditing.

Quality rules enforced:
  1. Title must be between MIN_TITLE_LENGTH and MAX_TITLE_LENGTH chars
  2. Company name must not be a known spam placeholder
  3. Apply URL must be a valid HTTP/S URL if present
  4. Description should have minimum content length
  5. Spam score heuristics (all-caps, excessive symbols, suspicious patterns)
  6. Duplicate external_id within same batch (intra-batch dedup)
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Set, Tuple

from app.job_discovery import config as cfg
from app.job_discovery.domain.models import NormalizedJob, ValidatedJob
from app.job_discovery.domain.exceptions import ValidationError

logger = logging.getLogger("jd.pipeline.validator")

# ---------------------------------------------------------------------------
# Known spam/placeholder patterns
# ---------------------------------------------------------------------------

_SPAM_COMPANY_NAMES: Set[str] = {
    "company", "tech company", "hiring", "unknown company", "n/a", "na",
    "test", "demo", "example", "placeholder", "firm", "organization",
}

_SPAM_TITLE_PATTERNS = [
    re.compile(r"^[A-Z\s!@#$%^&*()\-_+=|]{10,}$"),  # ALL CAPS with symbols
    re.compile(r"click here", re.IGNORECASE),
    re.compile(r"apply now", re.IGNORECASE),
    re.compile(r"^\d+$"),  # Title is only numbers
    re.compile(r"[*]{3,}"),  # Excessive asterisks
]

_URL_PATTERN = re.compile(
    r"^https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)


class JobValidator:
    """
    Validates NormalizedJob entities against a set of quality rules.
    Returns a ValidatedJob with trust/quality/spam scores applied.
    """

    def validate(self, job: NormalizedJob) -> Tuple[ValidatedJob, List[str]]:
        """
        Validates a single NormalizedJob.
        Returns (ValidatedJob, list_of_errors).
        If list_of_errors is non-empty, the job should be rejected.
        """
        errors: List[str] = []

        # Rule 1: Title length
        title_len = len(job.title)
        if title_len < cfg.MIN_TITLE_LENGTH:
            errors.append(f"Title too short: {title_len} chars")
        if title_len > cfg.MAX_TITLE_LENGTH:
            errors.append(f"Title too long: {title_len} chars")

        # Rule 2: Company name
        company_lower = job.company_name.lower().strip()
        if company_lower in _SPAM_COMPANY_NAMES:
            errors.append(f"Spam company placeholder: '{job.company_name}'")

        # Rule 3: Apply URL format
        if job.apply_url and not _URL_PATTERN.match(job.apply_url):
            errors.append(f"Invalid apply_url: '{job.apply_url[:80]}'")

        # Rule 4: Description length
        if len(job.description) < cfg.MIN_DESCRIPTION_LENGTH:
            errors.append(f"Description too short: {len(job.description)} chars")

        # Rule 5: Spam patterns in title
        spam_score = 0.0
        for pattern in _SPAM_TITLE_PATTERNS:
            if pattern.search(job.title):
                spam_score += 0.3
                errors.append(f"Spam pattern detected in title")
                break

        # Rule 6: No skills at all + no description = low quality
        if not job.required_skills and not job.preferred_skills and not job.description:
            spam_score += 0.2

        # Compute quality and trust scores
        quality_score = self._compute_quality_score(job, errors)
        trust_score = self._compute_trust_score(job)

        spam_score = min(spam_score, 1.0)

        is_valid = len(errors) == 0 and spam_score < cfg.MAX_SPAM_SCORE

        validated = ValidatedJob(
            **{k: v for k, v in vars(job).items()},
            trust_score=trust_score,
            quality_score=quality_score,
            spam_score=spam_score,
            validation_errors=errors,
            is_valid=is_valid,
        )
        return validated, errors

    def validate_batch(
        self, jobs: List[NormalizedJob]
    ) -> Tuple[List[ValidatedJob], List[Dict[str, Any]]]:
        """
        Validates a batch of jobs.
        Returns (valid_jobs, rejected_jobs_with_reasons).
        Also performs intra-batch deduplication by external_id.
        """
        valid: List[ValidatedJob] = []
        rejected: List[Dict[str, Any]] = []
        seen_external_ids: Set[str] = set()

        for job in jobs:
            # Intra-batch duplicate check
            if job.external_id in seen_external_ids:
                rejected.append({
                    "external_id": job.external_id,
                    "title": job.title,
                    "reason": "intra_batch_duplicate",
                })
                continue
            seen_external_ids.add(job.external_id)

            validated, errors = self.validate(job)
            if validated.is_valid:
                valid.append(validated)
            else:
                rejected.append({
                    "external_id": job.external_id,
                    "title": job.title,
                    "errors": errors,
                    "reason": "validation_failed",
                })

        logger.info(
            f"Validation: {len(valid)} valid, {len(rejected)} rejected "
            f"from {len(jobs)} jobs"
        )
        return valid, rejected

    # ------------------------------------------------------------------
    # Score computation
    # ------------------------------------------------------------------

    def _compute_quality_score(
        self, job: NormalizedJob, errors: List[str]
    ) -> float:
        """
        Computes a 0.0–1.0 quality score based on field completeness.
        """
        score = 0.0
        weights = {
            "has_description": 0.25,
            "has_skills": 0.20,
            "has_apply_url": 0.15,
            "has_salary": 0.15,
            "has_location": 0.10,
            "has_company": 0.10,
            "has_experience": 0.05,
        }

        if len(job.description) >= 100:
            score += weights["has_description"]
        if job.required_skills or job.preferred_skills:
            score += weights["has_skills"]
        if job.apply_url:
            score += weights["has_apply_url"]
        if job.salary_min or job.salary_max:
            score += weights["has_salary"]
        if job.city or job.location:
            score += weights["has_location"]
        if job.company_name and job.company_name not in _SPAM_COMPANY_NAMES:
            score += weights["has_company"]
        if job.experience_min_years is not None:
            score += weights["has_experience"]

        # Penalize for each validation error
        score -= len(errors) * 0.05
        return round(max(0.0, min(1.0, score)), 3)

    def _compute_trust_score(self, job: NormalizedJob) -> float:
        """
        Computes a 0.0–1.0 trust score for the company/posting legitimacy.
        Higher-tier sources and known company domains score higher.
        """
        base = 0.5
        trusted_sources = {
            "greenhouse": 0.95,
            "lever": 0.93,
            "linkedin": 0.85,
            "indeed": 0.80,
            "remoteok": 0.75,
            "wellfound": 0.78,
            "telegram": 0.55,
        }
        trust = trusted_sources.get(job.source_name, base)

        # Bonus if job has a valid apply URL
        if job.apply_url and _URL_PATTERN.match(job.apply_url):
            trust = min(1.0, trust + 0.05)

        return round(trust, 3)
