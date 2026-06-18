"""
Opportunity Scorer — 5-factor composite opportunity scoring system.
Replaces basic match scores with a holistic opportunity metric on the career dashboard.
"""
import logging
from datetime import datetime, timedelta
import re
from typing import Dict, Any

logger = logging.getLogger("app.opportunity_scorer")


class OpportunityScorer:
    """Calculates composite opportunity scores for candidate-job pairings."""

    def score(
        self,
        job: Dict[str, Any],
        match_score: float,
        company_intel: Dict[str, Any],
        candidate_prefs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculates a composite Opportunity Score (0-100) and returns the breakdown.
        Formula:
          Match Score (35%) + Company Quality (25%) + Salary Fit (15%) + Freshness (15%) + Legitimacy (10%)
        """
        # Factor 1: Skill + Semantic Match (35%)
        f1_match = match_score * 0.35

        # Factor 2: Company Quality Score (25%)
        company_quality = company_intel.get("quality_score", 60.0) # Default to average
        f2_company = company_quality * 0.25

        # Factor 3: Salary Fit (15%)
        salary_score = self._score_salary_fit(
            job.get("salary_range", ""),
            candidate_prefs.get("salary_min_lpa", 0.0),
            candidate_prefs.get("salary_max_lpa", 100.0)
        )
        f3_salary = salary_score * 0.15

        # Factor 4: Freshness (15%)
        freshness_score = self._score_freshness(job.get("posted_date", ""))
        f4_freshness = freshness_score * 0.15

        # Factor 5: Legitimacy (10%)
        legitimacy_score = self._score_legitimacy(job, company_intel)
        f5_legitimacy = legitimacy_score * 0.10

        opportunity_score = f1_match + f2_company + f3_salary + f4_freshness + f5_legitimacy
        opportunity_score = max(0.0, min(100.0, opportunity_score))

        return {
            "opportunity_score": round(opportunity_score, 1),
            "breakdown": {
                "match": round(match_score, 1),
                "company": round(company_quality, 1),
                "salary_fit": round(salary_score, 1),
                "freshness": round(freshness_score, 1),
                "legitimacy": round(legitimacy_score, 1)
            },
            "label": self._get_label(opportunity_score),
            "should_apply": opportunity_score >= 70.0
        }

    def _score_salary_fit(self, job_salary: str, expected_min: float, expected_max: float) -> float:
        """Parses job salary numbers and matches them against user expectations."""
        if not job_salary or expected_min <= 0:
            return 70.0  # Fair default for missing details

        # Try to find numbers in the salary string (e.g. "15 - 25 LPA" or "₹1,800,000")
        numbers = [float(x) for x in re.findall(r"\d+\.?\d*", job_salary.replace(",", ""))]
        if not numbers:
            return 70.0

        # Estimate average job salary (if range is provided, calculate average)
        job_avg = sum(numbers) / len(numbers)

        # Normalize to LPA if job_avg is in lakhs/millions (large numbers like 1,500,000 -> 15 LPA)
        if job_avg > 100000:
            job_avg = job_avg / 100000.0
        elif job_avg > 1000:
            # Maybe in USD or per month, normalize or scale roughly
            pass

        if job_avg >= expected_min:
            # Exceeds or matches expectation
            return 100.0
        else:
            # Under expectation, deduct points proportionally
            deficit_ratio = (expected_min - job_avg) / expected_min
            score = 100.0 - (deficit_ratio * 100.0)
            return max(10.0, score)

    def _score_freshness(self, posted_date_str: str) -> float:
        """Scores job freshness based on posting age."""
        if not posted_date_str:
            return 70.0 # Default fallback

        # Attempt to parse age keywords like "today", "1 day ago", "3 days ago", "1 week ago", or dates
        lower = posted_date_str.lower()
        if "today" in lower or "just now" in lower or "hour" in lower:
            return 100.0
        if "1 day" in lower or "yesterday" in lower:
            return 90.0
        if "2 day" in lower or "3 day" in lower:
            return 80.0
        if "4 day" in lower or "5 day" in lower or "6 day" in lower or "7 day" in lower or "week" in lower:
            return 60.0
        if "14 day" in lower or "2 week" in lower:
            return 30.0

        # Parse actual datetime if possible
        try:
            posted_dt = datetime.fromisoformat(posted_date_str.replace("Z", "+00:00"))
            age_days = (datetime.utcnow() - posted_dt.replace(tzinfo=None)).days
            if age_days <= 0: return 100.0
            if age_days <= 2: return 90.0
            if age_days <= 5: return 80.0
            if age_days <= 10: return 60.0
            if age_days <= 20: return 30.0
            return 10.0
        except Exception:
            pass

        return 70.0

    def _score_legitimacy(self, job: Dict[str, Any], company_intel: Dict[str, Any]) -> float:
        """Deducts points for mass-hiring flags, scams, or unverified job posts."""
        score = 100.0

        # Deduct if company is flagged as mass-hiring (e.g. 500+ open roles indicating low filter rate)
        if company_intel.get("is_mass_hiring", False):
            score -= 30.0

        # Check job description for spam signals
        desc = (job.get("description", "") or "").lower()
        title = (job.get("title", "") or "").lower()
        text_to_scan = f"{title} {desc}"

        spam_indicators = [
            ("wire transfer", 20.0),
            ("financial deposit", 20.0),
            ("unlimited earning", 10.0),
            ("work from home cash", 15.0),
            ("no experience needed", 5.0)  # soft deduction if coupled with senior title
        ]

        for word, penalty in spam_indicators:
            if word in text_to_scan:
                score -= penalty

        # Soft deduction if the job source is Playwright scraping vs direct API
        if job.get("source") == "Playwright":
            score -= 5.0

        return max(10.0, score)

    def _get_label(self, score: float) -> str:
        if score >= 90: return "🔥 Top Opportunity"
        if score >= 75: return "✅ Strong Match"
        if score >= 60: return "⚡ Good Fit"
        if score >= 45: return "🤔 Partial Match"
        return "⚠ Low Priority"


opportunity_scorer = OpportunityScorer()
