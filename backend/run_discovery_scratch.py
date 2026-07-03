import os
import sys

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.job_discovery.crawler.orchestrator import DiscoveryOrchestrator
from app.models.job_models import Job

def main():
    db = SessionLocal()
    try:
        # Count current jobs in DB
        initial_count = db.query(Job).count()
        print(f"Initial jobs in database: {initial_count}")

        # Instantiate orchestrator
        orchestrator = DiscoveryOrchestrator(db)
        
        # Define roles, locations, skills to search
        roles = ["Software Engineer", "Full Stack Developer", "Backend Engineer"]
        locations = ["India", "Remote"]
        skills = ["Python", "JavaScript", "React"]

        print(f"Triggering job discovery for roles: {roles}...")
        persisted_ids = orchestrator.run_discovery(
            roles=roles,
            locations=locations,
            skills=skills,
            max_per_source=15
        )

        final_count = db.query(Job).count()
        new_jobs = len(persisted_ids)
        
        print("\n=== Discovery Summary ===")
        print(f"New jobs persisted to database: {new_jobs}")
        print(f"Total jobs currently in database: {final_count}")
        
    except Exception as e:
        print(f"Error during discovery: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
