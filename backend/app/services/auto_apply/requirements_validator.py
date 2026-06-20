"""
Requirements Validator — Checks job requirements against candidate profile
before opening a browser. Prevents wasted applications on hard blockers.
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

# Patterns for hard blockers in job descriptions
_SPONSORSHIP_PATTERNS = [
    r"no\s+visa\s+sponsor", r"sponsorship\s+not\s+(available|provided|offered)",
    r"must\s+be\s+(authorized|eligible)\s+to\s+work",
    r"(only|exclusively)\s+(us|uk|eu|uae)\s+citizens",
    r"require[sd]?\s+security\s+clearance",
]
_DEGREE_PATTERNS = {
    "phd": [r"ph\.?d", r"doctorate"],
    "masters": [r"master'?s?\s+degree", r"m\.?s\.?", r"m\.?eng", r"mba"],
    "bachelors": [r"bachelor'?s?\s+degree", r"b\.?s\.?", r"b\.?e\.?", r"b\.?tech"]
}
_DEGREE_LEVEL = {"phd": 3, "masters": 2, "bachelors": 1, "diploma": 0, "none": 0}


@dataclass
class ValidationResult:
    passed: bool
    blockers: List[str] = field(default_factory=list)


class RequirementsValidator:
    """
    Validates job description against candidate profile for hard blockers.
    Fast regex-based checks — no browser, no LLM, no network calls.
    """

    def validate(self, candidate_profile: dict, job: dict) -> ValidationResult:
        """
        Args:
            candidate_profile: Dict with keys: skills, experience_years, education,
                               location, visa_eligible (bool), preferences
            job: Dict with keys: title, description, location, work_mode

        Returns:
            ValidationResult(passed=True) if no blockers found.
        """
        blockers = []
        description = (job.get("description") or "").lower()
        title = (job.get("title") or "").lower()
        full_text = f"{title} {description}"

        # 1. Visa sponsorship check
        if not candidate_profile.get("visa_eligible", True):
            for pattern in _SPONSORSHIP_PATTERNS:
                if re.search(pattern, full_text, re.IGNORECASE):
                    blockers.append("Job requires work authorization/visa sponsorship not supported.")
                    break

        # 2. Location restriction check
        candidate_loc = (candidate_profile.get("location") or "").lower()
        job_loc = (job.get("location") or "").lower()
        remote_pref = candidate_profile.get("remote_only", False)
        if remote_pref and job.get("work_mode", "remote").lower() not in ("remote", "work from home", "wfh"):
            if not re.search(r"remote|work\s+from\s+home|wfh", full_text):
                blockers.append(f"Candidate prefers remote only but job appears on-site: {job_loc}.")

        # 3. Degree requirement check
        candidate_edu = (candidate_profile.get("education") or "").lower()
        candidate_level = 0
        for level, patterns in _DEGREE_PATTERNS.items():
            if any(re.search(p, candidate_edu, re.IGNORECASE) for p in patterns):
                candidate_level = max(candidate_level, _DEGREE_LEVEL.get(level, 0))

        required_level = 0
        required_label = ""
        for level in ["phd", "masters"]:
            for p in _DEGREE_PATTERNS[level]:
                if re.search(p, full_text, re.IGNORECASE):
                    lv = _DEGREE_LEVEL[level]
                    if lv > required_level:
                        required_level = lv
                        required_label = level

        if required_level > candidate_level + 1:
            # Allow 1 level gap (e.g. Masters req but has Bachelors)
            blockers.append(
                f"Job requires {required_label} degree; candidate's education does not match."
            )

        # 4. Experience gap check
        candidate_exp = float(candidate_profile.get("experience_years") or 0)
        exp_match = re.search(
            r"(\d+)\+?\s*(?:to\s*\d+)?\s*years?\s+(?:of\s+)?(?:experience|exp)",
            full_text, re.IGNORECASE
        )
        if exp_match:
            required_exp = float(exp_match.group(1))
            if candidate_exp < required_exp - 2:  # Allow 2-year under-qualification
                blockers.append(
                    f"Job requires {required_exp:.0f}+ years experience; candidate has {candidate_exp:.0f} years."
                )

        return ValidationResult(passed=len(blockers) == 0, blockers=blockers)


# Module-level singleton
requirements_validator = RequirementsValidator()