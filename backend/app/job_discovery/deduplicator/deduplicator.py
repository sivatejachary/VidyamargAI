from typing import Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger("app.job_discovery.deduplicator")

class JobDeduplicator:
    def is_duplicate(self, job: Dict[str, Any], db: Session) -> bool:
        """
        Deduplicates jobs based on external_id or duplicate apply_url.
        """
        ext_id = job.get("external_id")
        apply_url = job.get("apply_url")
        
        # Check by external_id
        if ext_id:
            try:
                row = db.execute(
                    text("SELECT id FROM jobs WHERE external_id = :ext_id AND is_active = true LIMIT 1"),
                    {"ext_id": ext_id}
                ).first()
                if row:
                    return True
            except Exception as e:
                logger.warning(f"Error checking external_id deduplication: {e}")

        # Check by apply_url
        if apply_url and len(apply_url) > 10:
            try:
                row = db.execute(
                    text("SELECT id FROM jobs WHERE apply_url = :apply_url AND is_active = true LIMIT 1"),
                    {"apply_url": apply_url}
                ).first()
                if row:
                    return True
            except Exception as e:
                logger.warning(f"Error checking apply_url deduplication: {e}")

        return False
