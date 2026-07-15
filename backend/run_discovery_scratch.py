"""
Discovery Scratch Script — Test and verify the async Job Discovery platform.
Usage:
    cd backend
    python run_discovery_scratch.py
"""
import asyncio
import os
import sys

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine
from app.job_discovery.crawler.orchestrator import DiscoveryOrchestrator
from app.models.job_models import Job, JobSource
from sqlalchemy import text


def init_db_and_seed():
    """Runs migration & seeds job sources in the database using synchronous engine."""
    print("Migrating and seeding job_sources...")
    with engine.begin() as conn:
        # Run migrations
        conn.execute(
            text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(50) DEFAULT 'discovered';")
        )
        conn.execute(
            text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;")
        )
        # Seed
        conn.execute(
            text("""
            INSERT INTO job_sources (name, display_name, source_type, is_active, priority)
            VALUES 
                ('linkedin', 'LinkedIn', 'api', true, 2),
                ('linkedin_posts', 'LinkedIn Posts', 'api', true, 3),
                ('telegram', 'Telegram', 'api', true, 4),
                ('naukri', 'Naukri', 'api', true, 5),
                ('serper_jobs', 'Serper Jobs', 'api', true, 1)
            ON CONFLICT (name) DO UPDATE SET is_active = true;
            """)
        )
        # Deactivate unwanted sources
        conn.execute(
            text("UPDATE job_sources SET is_active = false WHERE name IN ('remoteok', 'indeed_rss');")
        )
    print("DB initialized and job_sources seeded successfully.")


async def async_main():
    # Connect EventBus
    try:
        from app.core.event_bus import event_bus
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        print(f"Connecting EventBus to {redis_url}...")
        await event_bus.connect(redis_url)
    except Exception as exc:
        print(f"EventBus connection failed, falling back to local: {exc}")

    # 1. Get initial count using a fresh, short-lived session
    with SessionLocal() as db:
        initial_count = db.query(Job).count()
        print(f"Initial jobs in database: {initial_count}")
        sources = db.query(JobSource).filter(JobSource.is_active == True).all()
        print(f"Active job sources in DB: {[s.name for s in sources]}")

    # 2. Instantiate orchestrator and run discovery
    orchestrator = DiscoveryOrchestrator()
    
    roles = ["Software Engineer", "Full Stack Developer", "Backend Engineer"]
    locations = ["India", "Remote"]
    skills = ["Python", "JavaScript", "React"]

    print(f"Triggering job discovery for roles: {roles}...")
    
    # Await the async run_discovery method (takes some time, other connections closed)
    persisted_ids = await orchestrator.run_discovery(
        roles=roles,
        locations=locations,
        skills=skills,
        max_per_source=10
    )

    # 3. Get final count using a fresh, short-lived session to prevent stale connection errors
    with SessionLocal() as db:
        final_count = db.query(Job).count()
        new_jobs = len(persisted_ids)
        
        print("\n=== Discovery Summary ===")
        print(f"New jobs persisted to database: {new_jobs}")
        print(f"Total jobs currently in database: {final_count}")
        print(f"New Job IDs: {persisted_ids}")


def main():
    # Sync seed first
    try:
        init_db_and_seed()
    except Exception as exc:
        print(f"DB Seeding failed: {exc}")

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
