"""
Apify Dataset Job Importer Script
===================================
Pulls crawled job records from an Apify Actor Dataset and imports them
into the VidyaMarg AI database using the canonical job pipeline.

Usage:
    cd backend
    python import_apify_jobs.py --dataset IdAABmZYVYd86COF7 --token YOUR_APIFY_TOKEN
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
import os
from pathlib import Path
from datetime import datetime

# Bootstrap path
_BACKEND = Path(__file__).parent.resolve()
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import httpx
from app.core.database import SessionLocal
from app.models.job_models import Job, JobSource
from app.job_discovery.normalizer.normalizer import JobNormalizer
from app.job_discovery.validator.validator import JobValidator
from app.job_discovery.deduplicator.deduplicator import JobDeduplicator
from app.job_discovery.persistence.manager import JobPersistenceManager
from app.job_discovery.events.dispatcher import JobEventDispatcher


def _parse_apify_item(item: dict) -> dict:
    """Flexible mapper to handle various Apify LinkedIn scraper schemas."""
    # 1. Extract Title
    title = (
        item.get("title") or 
        item.get("positionName") or 
        item.get("jobTitle") or 
        item.get("role") or 
        ""
    )
    # 2. Extract Company
    company = (
        item.get("company") or 
        item.get("companyName") or 
        item.get("company_name") or 
        ""
    )
    if isinstance(company, dict):
        company = company.get("name", "")

    # 3. Extract Location
    location = item.get("location") or item.get("jobLocation") or "India"
    if isinstance(location, dict):
        location = location.get("name", "India")

    # 4. Extract URL
    url = (
        item.get("url") or 
        item.get("jobUrl") or 
        item.get("link") or 
        item.get("applyUrl") or 
        ""
    )

    # 5. Extract Description
    description = (
        item.get("description") or 
        item.get("descriptionHtml") or 
        item.get("jobDescription") or 
        ""
    )

    # 6. Skills
    skills = item.get("skills") or item.get("keySkills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    return {
        "title": title.strip(),
        "company_name": company.strip(),
        "location": location.strip(),
        "apply_url": url.strip(),
        "job_url": url.strip(),
        "description": description.strip(),
        "required_skills": skills,
        "is_remote": "remote" in location.lower() or item.get("workPlace", "").lower() == "remote",
        "source_name": "linkedin",
    }


async def main():
    parser = argparse.ArgumentParser(description="Import jobs from Apify actor dataset")
    parser.add_argument("--dataset", required=True, help="Apify dataset ID")
    parser.add_argument("--token", required=True, help="Apify API Token")
    args = parser.parse_args()

    url = f"https://api.apify.com/v2/datasets/{args.dataset}/items?token={args.token}"
    print(f"\nFetching dataset items from Apify for dataset: {args.dataset}...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                print(f"[ERROR] Failed to fetch dataset: HTTP {resp.status_code}")
                print(resp.text[:500])
                sys.exit(1)

            items = resp.json()
            if not isinstance(items, list):
                print(f"[ERROR] Unexpected dataset response type: {type(items)}")
                sys.exit(1)

            print(f"Retrieved {len(items)} items from dataset. Processing...")

            normalizer = JobNormalizer()
            validator = JobValidator()
            deduplicator = JobDeduplicator()
            persistence = JobPersistenceManager()
            dispatcher = JobEventDispatcher()

            db = SessionLocal()
            imported_count = 0
            duplicates_count = 0
            invalid_count = 0

            try:
                for idx, raw_item in enumerate(items, 1):
                    parsed = _parse_apify_item(raw_item)
                    
                    if not parsed["title"] or not parsed["job_url"]:
                        invalid_count += 1
                        continue

                    # Create unique external ID based on URL
                    ext_id = hashlib.md5(f"linkedin:{parsed['job_url']}".encode()).hexdigest()
                    parsed["external_id"] = ext_id

                    # Pipeline processing
                    norm = normalizer.normalize(parsed)
                    norm["source_name"] = "linkedin"

                    rejection = validator.validate(norm)
                    if rejection:
                        invalid_count += 1
                        continue

                    if deduplicator.is_duplicate(norm, db):
                        duplicates_count += 1
                        continue

                    # Persist job
                    job_record = persistence.persist_job(norm, db)
                    db.commit()
                    imported_count += 1

                    # Dispatch event
                    await dispatcher.publish_persisted(
                        job_id=job_record.id,
                        title=job_record.title,
                        company=job_record.company_name,
                    )

                print("\n" + "=" * 45)
                print("   APIFY DATASET IMPORT SUMMARY")
                print("=" * 45)
                print(f"  Total items checked: {len(items)}")
                print(f"  Successfully imported: {imported_count}")
                print(f"  Skipped duplicates:    {duplicates_count}")
                print(f"  Skipped invalid/empty: {invalid_count}")
                print("=" * 45 + "\n")

            except Exception as exc:
                db.rollback()
                print(f"[ERROR] Import loop failed: {exc}")
            finally:
                db.close()

        except Exception as exc:
            print(f"[ERROR] Request failed: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
