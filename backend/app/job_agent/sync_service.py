import logging
import psycopg2
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.job_models import Job, JobSource

logger = logging.getLogger("app.job_agent.sync_service")

JOB_AGENT_DB_CONFIG = {
    "host": "hayabusa.proxy.rlwy.net",
    "port": 13794,
    "database": "railway",
    "user": "postgres",
    "password": "oUxhTXwbQQnDTJzoDiISefZaARGIinAS"
}

class JobSyncService:
    def __init__(self, db: Session):
        self.db = db

    def sync_jobs(self, limit: int = 200) -> int:
        """
        Fetches the latest jobs from the Job Agent database (hayabusa:13794)
        and stores them in VidyaMarg AI's local database.
        """
        logger.info("Connecting to Job Agent database to fetch latest jobs...")
        try:
            conn = psycopg2.connect(**JOB_AGENT_DB_CONFIG)
            cur = conn.cursor()
            
            # Query recent jobs from Job Agent database
            cur.execute("""
                SELECT job_id, channel, message_id, date, title, company, 
                       location, experience, skills, salary, apply_link, 
                       original_link, email, message_link, raw_text, job_hash
                FROM jobs
                ORDER BY date DESC
                LIMIT %s
            """, (limit,))
            
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
            logger.info(f"Fetched {len(rows)} raw jobs from Job Agent database.")
            
            # Ensure 'job_agent' source exists in local database
            source = self.db.query(JobSource).filter_by(name="job_agent").first()
            if not source:
                source = JobSource(
                    name="job_agent",
                    display_name="AI Job Agent",
                    source_type="database",
                    is_active=True,
                    priority=1
                )
                self.db.add(source)
                self.db.flush()
            
            synced_count = 0
            for row in rows:
                job_data = dict(zip(colnames, row))
                
                # Use job_hash or external_id (ja-{job_id}) as unique identifier
                ext_id = f"ja-{job_data['job_id']}"
                job_hash = job_data['job_hash'] or ext_id
                
                # Check if job already exists in VidyaMarg AI
                existing_job = self.db.query(Job).filter(
                    (Job.external_id == ext_id) | (Job.job_url == job_data['apply_link'])
                ).first()
                
                if existing_job:
                    continue
                
                # Heuristics for remote/hybrid
                loc = (job_data['location'] or "India").strip()
                is_remote = "remote" in loc.lower() or "wfh" in loc.lower() or "work from home" in loc.lower()
                is_hybrid = "hybrid" in loc.lower()
                
                # Process skills string into a JSON list
                skills_list = []
                if job_data['skills']:
                    skills_list = [s.strip() for s in job_data['skills'].split(",") if s.strip()]
                
                # Map fields
                new_job = Job(
                    external_id=ext_id,
                    source_id=source.id,
                    title=job_data['title'] or "Software Engineer",
                    company_name=job_data['company'] or "Tech Company",
                    description=job_data['raw_text'] or job_data['title'],
                    description_summary=job_data['raw_text'][:200] if job_data['raw_text'] else "",
                    apply_url=job_data['apply_link'] or "",
                    job_url=job_data['original_link'] or job_data['apply_link'] or "",
                    location=loc,
                    city=loc.split(",")[0].strip() if "," in loc else loc,
                    country="IN",
                    is_remote=is_remote,
                    is_hybrid=is_hybrid,
                    role_category="Engineering",
                    industry="Technology",
                    seniority="Mid",
                    employment_type="full_time",
                    work_mode="remote" if is_remote else ("hybrid" if is_hybrid else "onsite"),
                    required_skills=skills_list,
                    preferred_skills=[],
                    salary_raw=job_data['salary'],
                    experience_min_years=1.0,
                    is_active=True,
                    is_verified=True,
                    lifecycle_status="discovered",
                    posted_at=job_data['date'] or datetime.utcnow(),
                    discovered_at=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                self.db.add(new_job)
                synced_count += 1
                
            self.db.commit()
            cur.close()
            conn.close()
            logger.info(f"Successfully synced {synced_count} new jobs to VidyaMarg AI database.")
            return synced_count
            
        except Exception as e:
            logger.error(f"Failed to sync jobs from Job Agent database: {e}", exc_info=True)
            self.db.rollback()
            return 0
