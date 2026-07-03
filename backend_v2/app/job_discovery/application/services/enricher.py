"""
VidyaMarg AI — Job Enricher
=============================
AI-driven enrichment of validated job entities.
Enrichment operations:
  1. AI-generated 3-sentence description summary (via Gemini/OpenAI)
  2. Freshness score computation (decays logarithmically from posted_at)
  3. Skill graph construction (weighted {skill: relevance_score})
  4. Role sub-category detection (backend, frontend, devops, etc.)
  5. Industry classification
  6. Spam score refinement using LLM when borderline

The enricher runs BEFORE bulk persistence so that all intelligence
is stored on first write. This avoids costly post-hoc update queries.

AI calls are batched and run concurrently using asyncio.gather.
If AI is unavailable, the enricher degrades gracefully with defaults.
"""
from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.job_discovery.domain.models import EnrichedJob, JobLifecycle, ValidatedJob

logger = logging.getLogger("jd.pipeline.enricher")

# ---------------------------------------------------------------------------
# Skill importance weights (boost high-value skills)
# ---------------------------------------------------------------------------

_HIGH_VALUE_SKILLS = {
    "kubernetes", "terraform", "rust", "go", "pytorch", "fastapi",
    "spark", "kafka", "machine learning", "deep learning",
    "system design", "distributed systems", "llm", "rag",
}

_ROLE_SUB_CATEGORY_MAP = {
    "engineering": {
        "backend": ["backend", "api", "server", "django", "fastapi", "spring"],
        "frontend": ["frontend", "react", "vue", "angular", "ui", "next.js"],
        "full_stack": ["full stack", "fullstack"],
        "mobile": ["android", "ios", "flutter", "react native", "mobile"],
        "devops": ["devops", "sre", "platform", "kubernetes", "docker", "terraform"],
        "data_engineering": ["data engineer", "etl", "spark", "airflow", "dbt"],
        "ml_ai": ["machine learning", "ml engineer", "ai engineer", "mlops", "llm"],
        "security": ["security", "soc", "penetration", "infosec"],
        "embedded": ["embedded", "iot", "firmware", "rtos"],
    },
}

_INDUSTRY_MAP = {
    "fintech": ["fintech", "banking", "payments", "crypto", "defi", "trading"],
    "healthtech": ["health", "medical", "pharma", "biotech", "clinical"],
    "edtech": ["education", "learning", "edtech", "e-learning", "lms"],
    "ecommerce": ["ecommerce", "e-commerce", "retail", "marketplace", "shopify"],
    "saas": ["saas", "b2b", "enterprise software", "platform"],
    "ai": ["artificial intelligence", "ai", "machine learning", "llm", "nlp"],
    "logistics": ["logistics", "supply chain", "delivery", "shipping"],
    "gaming": ["gaming", "game", "unity", "unreal"],
}


class JobEnricher:
    """
    Enriches ValidatedJob entities with AI-generated metadata.
    Operates in async batch mode using asyncio.gather for concurrency.
    """

    def __init__(self, openai_api_key: Optional[str] = None) -> None:
        self._openai_key = openai_api_key
        self._ai_available = openai_api_key is not None

    async def enrich_batch(
        self, validated_jobs: List[ValidatedJob], concurrency: int = 10
    ) -> List[EnrichedJob]:
        """
        Enriches a batch of validated jobs concurrently.
        Uses a semaphore to limit concurrency and avoid API rate limits.
        """
        sem = asyncio.Semaphore(concurrency)
        tasks = [self._enrich_one(job, sem) for job in validated_jobs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        enriched: List[EnrichedJob] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    f"Enrichment failed for {validated_jobs[i].external_id}: {result}. "
                    f"Using defaults."
                )
                # Apply defaults — never drop a job due to enrichment failure
                enriched.append(self._apply_defaults(validated_jobs[i]))
            else:
                enriched.append(result)

        logger.info(f"Enriched {len(enriched)} jobs")
        return enriched

    async def _enrich_one(
        self, job: ValidatedJob, sem: asyncio.Semaphore
    ) -> EnrichedJob:
        async with sem:
            # Compute non-AI enrichment synchronously (fast)
            freshness = self._compute_freshness(job.posted_at or job.discovered_at)
            skill_graph = self._build_skill_graph(job.required_skills, job.preferred_skills)
            role_sub_category = self._detect_sub_category(
                job.role_category, job.title_normalized
            )
            industry = self._detect_industry(
                job.title_normalized + " " + job.description[:300]
            )

            # AI summary generation (optional — degrades gracefully)
            summary = await self._generate_summary(job) if self._ai_available else ""

            return EnrichedJob(
                # Copy all fields from ValidatedJob
                external_id=job.external_id,
                source_name=job.source_name,
                title=job.title,
                title_normalized=job.title_normalized,
                company_name=job.company_name,
                company_normalized=job.company_normalized,
                description=job.description,
                description_summary=summary,
                apply_url=job.apply_url,
                job_url=job.job_url,
                location=job.location,
                city=job.city,
                state=job.state,
                country=job.country,
                is_remote=job.is_remote,
                is_hybrid=job.is_hybrid,
                work_mode=job.work_mode,
                employment_type=job.employment_type,
                seniority=job.seniority,
                role_category=job.role_category,
                role_sub_category=role_sub_category,
                industry=industry,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                salary_currency=job.salary_currency,
                salary_period=job.salary_period,
                salary_raw=job.salary_raw,
                required_skills=job.required_skills,
                preferred_skills=job.preferred_skills,
                experience_min_years=job.experience_min_years,
                experience_max_years=job.experience_max_years,
                posted_at=job.posted_at,
                discovered_at=job.discovered_at,
                trust_score=job.trust_score,
                quality_score=job.quality_score,
                spam_score=job.spam_score,
                validation_errors=job.validation_errors,
                is_valid=job.is_valid,
                skill_graph=skill_graph,
                freshness_score=freshness,
                lifecycle_status=JobLifecycle.ENRICHED,
            )

    def _apply_defaults(self, job: ValidatedJob) -> EnrichedJob:
        """Returns an EnrichedJob with default values when enrichment fails."""
        return EnrichedJob(
            **{k: v for k, v in vars(job).items()},
            skill_graph={},
            freshness_score=self._compute_freshness(job.posted_at or job.discovered_at),
            lifecycle_status=JobLifecycle.ENRICHED,
        )

    def _compute_freshness(self, date: Optional[datetime]) -> float:
        """
        Logarithmic decay: freshness = 1.0 when posted today, decays to ~0.1 at 30 days.
        Formula: max(0.0, 1.0 - log(days + 1) / log(31))
        """
        if not date:
            return 0.7  # Unknown posting date — moderate freshness
        try:
            if date.tzinfo:
                date = date.replace(tzinfo=None)
            days_old = max(0, (datetime.utcnow() - date).days)
            score = max(0.0, 1.0 - math.log(days_old + 1) / math.log(31))
            return round(score, 3)
        except Exception:
            return 0.7

    def _build_skill_graph(
        self, required: List[str], preferred: List[str]
    ) -> Dict[str, float]:
        """
        Assigns importance weights to each skill.
        Required skills get higher weight than preferred.
        High-value skills get an additional 0.15 boost.
        """
        graph: Dict[str, float] = {}
        for skill in required:
            weight = 1.0
            if skill in _HIGH_VALUE_SKILLS:
                weight = min(1.0, weight + 0.15)
            graph[skill] = round(weight, 2)
        for skill in preferred:
            if skill not in graph:
                weight = 0.6
                if skill in _HIGH_VALUE_SKILLS:
                    weight = min(1.0, weight + 0.15)
                graph[skill] = round(weight, 2)
        return graph

    def _detect_sub_category(self, role_category: str, title_lower: str) -> str:
        sub_map = _ROLE_SUB_CATEGORY_MAP.get(role_category, {})
        for sub, keywords in sub_map.items():
            if any(kw in title_lower for kw in keywords):
                return sub
        return ""

    def _detect_industry(self, text_lower: str) -> str:
        for industry, keywords in _INDUSTRY_MAP.items():
            if any(kw in text_lower for kw in keywords):
                return industry
        return "technology"

    async def _generate_summary(self, job: ValidatedJob) -> str:
        """
        Generates a 3-sentence AI summary of the job description.
        Falls back to empty string if OpenAI is unavailable.
        """
        if not self._ai_available or not job.description or len(job.description) < 100:
            return ""
        try:
            from openai import AsyncOpenAI  # type: ignore

            client = AsyncOpenAI(api_key=self._openai_key)
            prompt = (
                f"Summarize this job description in exactly 3 sentences. "
                f"Focus on the role responsibilities and required skills. "
                f"Be factual and concise.\n\n"
                f"Job Title: {job.title}\n"
                f"Company: {job.company_name}\n"
                f"Description: {job.description[:2000]}"
            )
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            logger.debug(f"AI summary failed: {exc}")
            return ""
