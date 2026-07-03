"""
VidyaMarg AI — Job Normalizer
==============================
Converts raw job payloads from any connector into a canonical NormalizedJob.
Handles salary parsing, skill deduplication, location normalization,
seniority detection, and work mode classification.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.job_discovery.domain.models import (
    EmploymentType,
    NormalizedJob,
    RawJob,
    Seniority,
    WorkMode,
)

logger = logging.getLogger("jd.pipeline.normalizer")

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_SALARY_RANGE_RE = re.compile(
    r"(?:rs\.?|inr|usd|\$|₹)?\s*(\d[\d,\.]+)\s*(?:to|-|–)\s*(?:rs\.?|inr|usd|\$|₹)?\s*(\d[\d,\.]+)",
    re.IGNORECASE,
)
_SALARY_LPA_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:–|-|to)\s*(\d+(?:\.\d+)?)\s*lpa",
    re.IGNORECASE,
)
_SALARY_SINGLE_RE = re.compile(
    r"(?:rs\.?|inr|usd|\$|₹)\s*(\d[\d,\.]+)",
    re.IGNORECASE,
)

_SENIORITY_MAP = {
    Seniority.INTERN: ["intern", "internship", "trainee", "fresher", "0-1 year"],
    Seniority.JUNIOR: ["junior", "associate", "entry", "0-2 year", "1-2 year"],
    Seniority.MID: ["mid", "intermediate", "2-4 year", "2-5 year", "3-5 year"],
    Seniority.SENIOR: ["senior", "sr.", "4+ year", "5+ year", "5-8 year", "lead"],
    Seniority.LEAD: ["tech lead", "team lead", "principal"],
    Seniority.DIRECTOR: ["director", "vp", "head of"],
    Seniority.CXO: ["cto", "ceo", "coo", "cxo", "chief"],
}

_ROLE_CATEGORY_MAP = {
    "engineering": [
        "software engineer", "backend", "frontend", "full stack", "devops",
        "platform", "sre", "data engineer", "ml engineer", "ai engineer",
    ],
    "design": ["designer", "ui/ux", "product design", "ux researcher"],
    "product": ["product manager", "product owner", "pm", "product lead"],
    "data": ["data scientist", "data analyst", "analytics", "business intelligence"],
    "marketing": ["marketing", "growth", "seo", "content", "brand"],
    "sales": ["sales", "account executive", "business development", "bdr", "sdr"],
    "finance": ["finance", "accountant", "cfo", "financial analyst"],
    "hr": ["recruiter", "hr", "talent acquisition", "people operations"],
    "operations": ["operations", "project manager", "program manager", "scrum"],
}

_REMOTE_KEYWORDS = {"remote", "work from home", "wfh", "anywhere", "distributed", "globally"}
_HYBRID_KEYWORDS = {"hybrid", "partially remote", "flexible"}


class JobNormalizer:
    """
    Normalizes raw job dicts into canonical NormalizedJob domain objects.
    Applies heuristics for fields that are often absent or ambiguous.
    """

    def normalize(self, raw: RawJob) -> Optional[NormalizedJob]:
        """
        Main normalization entry point.
        Returns None if the job cannot be meaningfully normalized.
        """
        try:
            title = self._clean_text(raw.title)
            if not title or len(title) < 3:
                logger.debug(f"Dropped job with empty title: {raw.external_id}")
                return None

            company = self._clean_text(raw.company_name)
            if not company:
                company = "Unknown Company"

            description = raw.description or ""
            title_lower = title.lower()
            desc_lower = description.lower()

            # Detect work mode
            work_mode, is_remote, is_hybrid = self._detect_work_mode(
                raw.location, title_lower, desc_lower, raw.is_remote
            )

            # Normalize location
            country, city, state = self._parse_location(raw.location, raw.country)

            # Parse salary
            salary_min, salary_max, currency = self._parse_salary(
                raw.salary_raw, raw.salary_min, raw.salary_max, raw.salary_currency
            )

            # Detect seniority
            seniority = self._detect_seniority(title_lower, desc_lower)

            # Detect role category
            role_category = self._detect_role_category(title_lower)

            # Clean skills
            required_skills = list(dict.fromkeys(
                [s.strip().lower() for s in raw.required_skills if s and len(s.strip()) > 1]
            ))[:30]
            preferred_skills = list(dict.fromkeys(
                [s.strip().lower() for s in raw.preferred_skills if s and len(s.strip()) > 1]
            ))[:20]

            return NormalizedJob(
                external_id=raw.external_id,
                source_name=raw.source_name,
                title=title,
                title_normalized=title_lower.strip(),
                company_name=company,
                company_normalized=self._normalize_company(company),
                description=description,
                apply_url=raw.apply_url or "",
                job_url=raw.job_url or raw.apply_url or "",
                location=raw.location or "",
                city=city,
                state=state,
                country=country,
                is_remote=is_remote,
                is_hybrid=is_hybrid,
                work_mode=work_mode,
                employment_type=EmploymentType.FULL_TIME,
                seniority=seniority,
                role_category=role_category,
                industry="",
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=currency,
                salary_raw=raw.salary_raw or "",
                required_skills=required_skills,
                preferred_skills=preferred_skills,
                experience_min_years=raw.experience_min_years,
                experience_max_years=raw.experience_max_years,
                posted_at=raw.posted_at,
                discovered_at=raw.discovered_at,
            )
        except Exception as exc:
            logger.error(f"Normalization failed for {raw.external_id}: {exc}")
            return None

    def normalize_batch(self, raw_jobs: List[RawJob]) -> List[NormalizedJob]:
        """Normalizes a batch, dropping None results silently."""
        result = []
        for raw in raw_jobs:
            norm = self.normalize(raw)
            if norm is not None:
                result.append(norm)
        logger.info(f"Normalized {len(result)}/{len(raw_jobs)} jobs")
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clean_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        # Remove leading/trailing emoji and whitespace
        cleaned = re.sub(r"^[\s\U0001F300-\U0001FAFF🚀💼📢🔥⚡✨🌟]+", "", text)
        cleaned = re.sub(r"[\s]+", " ", cleaned).strip()
        # Remove markdown bold/italic
        cleaned = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", cleaned)
        return cleaned[:500]

    def _normalize_company(self, company: str) -> str:
        """Returns a slug-normalized company name for dedup lookups."""
        normalized = company.lower()
        normalized = re.sub(r"[\s\.\,\-\'\"&()]+", "", normalized)
        return normalized[:255]

    def _detect_work_mode(
        self,
        location: Optional[str],
        title_lower: str,
        desc_lower: str,
        connector_is_remote: bool,
    ) -> tuple[WorkMode, bool, bool]:
        loc = (location or "").lower()
        combined = f"{loc} {title_lower} {desc_lower}"

        is_remote = connector_is_remote or any(kw in combined for kw in _REMOTE_KEYWORDS)
        is_hybrid = any(kw in combined for kw in _HYBRID_KEYWORDS)

        if is_hybrid:
            return WorkMode.HYBRID, False, True
        if is_remote:
            return WorkMode.REMOTE, True, False
        return WorkMode.ONSITE, False, False

    def _parse_location(
        self, location: Optional[str], default_country: str
    ) -> tuple[str, str, str]:
        if not location:
            return default_country or "IN", "", ""

        loc = location.strip()

        # Basic country detection
        country = default_country or "IN"
        if any(kw in loc.lower() for kw in ["usa", "united states", "us,"]):
            country = "US"
        elif any(kw in loc.lower() for kw in ["india", "bangalore", "mumbai", "hyderabad", "chennai"]):
            country = "IN"
        elif any(kw in loc.lower() for kw in ["global", "worldwide", "anywhere"]):
            country = "GLOBAL"

        parts = [p.strip() for p in loc.split(",")]
        city = parts[0] if parts else ""
        state = parts[1] if len(parts) > 1 else ""

        return country, city[:100], state[:100]

    def _parse_salary(
        self,
        salary_raw: Optional[str],
        salary_min: Optional[float],
        salary_max: Optional[float],
        currency: Optional[str],
    ) -> tuple[Optional[float], Optional[float], str]:
        # If structured values already present, use them
        if salary_min is not None or salary_max is not None:
            return salary_min, salary_max, (currency or "INR")

        if not salary_raw:
            return None, None, currency or "INR"

        # Try LPA format first (Indian salary market)
        lpa_match = _SALARY_LPA_RE.search(salary_raw)
        if lpa_match:
            low = float(lpa_match.group(1)) * 100_000
            high = float(lpa_match.group(2)) * 100_000
            return low, high, "INR"

        # Try range format
        range_match = _SALARY_RANGE_RE.search(salary_raw)
        if range_match:
            low = float(range_match.group(1).replace(",", ""))
            high = float(range_match.group(2).replace(",", ""))
            return low, high, currency or "INR"

        # Single value
        single_match = _SALARY_SINGLE_RE.search(salary_raw)
        if single_match:
            val = float(single_match.group(1).replace(",", ""))
            return val, None, currency or "INR"

        return None, None, currency or "INR"

    def _detect_seniority(self, title_lower: str, desc_lower: str) -> Seniority:
        combined = f"{title_lower} {desc_lower[:200]}"
        for seniority, keywords in _SENIORITY_MAP.items():
            if any(kw in combined for kw in keywords):
                return seniority
        return Seniority.MID  # Default to mid-level

    def _detect_role_category(self, title_lower: str) -> str:
        for category, keywords in _ROLE_CATEGORY_MAP.items():
            if any(kw in title_lower for kw in keywords):
                return category
        return "other"
