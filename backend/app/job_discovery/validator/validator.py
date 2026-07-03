from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("app.job_discovery.validator")

class JobValidator:
    SPAM_KEYWORDS = {
        "work from home data entry", "typing job", "earn lakhs",
        "no experience required high salary", "copy paste work",
        "part time earn daily", "reseller", "mlm", "pyramid scheme",
        "make money online guarantee", "investment return", "financial advisor bitcoin",
    }

    def validate(self, job: Dict[str, Any]) -> Optional[str]:
        """
        Validates job criteria and filters spam.
        Returns None if job is valid, or a string rejection reason if invalid.
        """
        title = (job.get("title") or "").lower()
        desc = (job.get("description") or "").lower()
        company = (job.get("company_name") or "").strip()

        # No title or company
        if not title or not company or len(company) < 2:
            return "invalid_data"

        # Spam detection
        combined = f"{title} {desc[:500]}"
        for kw in self.SPAM_KEYWORDS:
            if kw in combined:
                return "spam"

        # Title sanity
        if len(title) < 3 or len(title) > 300:
            return "invalid_title"

        return None
