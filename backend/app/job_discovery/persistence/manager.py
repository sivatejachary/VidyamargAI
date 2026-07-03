from datetime import datetime
from sqlalchemy.orm import Session
from app.models.job_models import Job, Company, JobSource
import logging

logger = logging.getLogger("app.job_discovery.persistence.manager")

class JobPersistenceManager:
    def persist_job(self, job_data: dict, db: Session) -> Job:
        """
        Persists a normalized, validated, and deduplicated job dictionary to PostgreSQL.
        Upserts the associated company details.
        """
        # 1. Upsert company
        company_name = (job_data.get("company_name") or "").strip()
        company_normalized = company_name.lower().replace(" ", "").replace(".", "").replace(",", "")

        company = db.query(Company).filter(Company.normalized_name == company_normalized).first()
        if not company:
            company = Company(
                name=company_name,
                normalized_name=company_normalized,
                industry=job_data.get("industry"),
                trust_score=0.7,
            )
            db.add(company)
            db.flush()

        # 2. Get or create job source
        source_name = job_data.get("source_name", "serper_jobs")
        source = db.query(JobSource).filter_by(name=source_name).first()
        if not source:
            source = JobSource(name=source_name, display_name=source_name.title(), source_type="api")
            db.add(source)
            db.flush()

        # 3. Create job record
        job = Job(
            external_id=job_data.get("external_id"),
            source_id=source.id if source else None,
            company_id=company.id,
            title=job_data.get("title", ""),
            title_normalized=(job_data.get("title") or "").lower().strip(),
            company_name=company_name,
            description=job_data.get("description"),
            description_summary=job_data.get("description_summary"),
            apply_url=job_data.get("apply_url"),
            job_url=job_data.get("job_url"),
            location=job_data.get("location"),
            city=job_data.get("city"),
            state=job_data.get("state"),
            country=job_data.get("country", "IN"),
            is_remote=job_data.get("is_remote", False),
            is_hybrid=job_data.get("is_hybrid", False),
            role_category=job_data.get("role_category"),
            industry=job_data.get("industry"),
            seniority=job_data.get("seniority", "mid"),
            employment_type=job_data.get("employment_type", "full_time"),
            required_skills=job_data.get("required_skills", []),
            preferred_skills=job_data.get("preferred_skills", []),
            salary_min=job_data.get("salary_min"),
            salary_max=job_data.get("salary_max"),
            salary_currency=job_data.get("salary_currency", "INR"),
            salary_raw=job_data.get("salary_raw"),
            experience_min_years=job_data.get("experience_min_years"),
            experience_max_years=job_data.get("experience_max_years"),
            trust_score=0.7,
            quality_score=0.6,
            freshness_score=1.0,
            spam_score=0.0,
            is_active=True,
            is_verified=True,
            posted_at=job_data.get("posted_at") or datetime.utcnow(),
            discovered_at=datetime.utcnow(),
            verified_at=datetime.utcnow(),
            lifecycle_status="persisted"
        )
        db.add(job)
        db.flush()
        return job
