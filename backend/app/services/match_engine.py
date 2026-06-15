"""
AI Match Engine — calculates how well a candidate's profile
matches a live job listing.

Weights:
  Skill Match      50%
  Experience Match 20%
  Education Match  10%
  Location Match   10%
  Projects Match   10%
"""
import json
import re
import logging
from datetime import datetime
from typing import List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    match_score: int          # 0-100
    missing_skills: List[str]
    skill_match: float
    experience_match: float
    education_match: float
    location_match: float
    projects_match: float


def _parse_years(text: str) -> int:
    """Extract max years from experience strings like '3-5 Years' or '5+ Years'."""
    if not text:
        return 0
    text = text.lower()
    if "fresher" in text or "0-1" in text:
        return 0
    match = re.search(r'(\d+)\s*\+?\s*(?:years?|yrs?)', text)
    if match:
        return int(match.group(1))
    match = re.search(r'(\d+)\s*[-–]\s*(\d+)', text)
    if match:
        return int(match.group(2))
    return 0


def parse_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    from datetime import datetime
    ds = date_str.strip().lower()
    if ds in ["present", "current", "ongoing", "now", "till date", "till now"]:
        return datetime.utcnow()
    
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    
    match = re.search(r'([a-zA-Z]+)\s*(\d{4})', ds)
    if match:
        m_str = match.group(1)
        y_str = match.group(2)
        m_val = months.get(m_str[:3], 1)
        return datetime(int(y_str), m_val, 1)
        
    match = re.search(r'(\d{1,2})[\/\-](\d{4})', ds)
    if match:
        return datetime(int(match.group(2)), int(match.group(1)), 1)
        
    match = re.search(r'(\d{4})', ds)
    if match:
        return datetime(int(match.group(1)), 1, 1)
    return None


def _candidate_years(candidate_experience: Optional[str]) -> int:
    """Estimate years of experience from candidate's experience JSON."""
    if not candidate_experience:
        return 0
    from datetime import datetime
    try:
        roles = json.loads(candidate_experience)
        if isinstance(roles, list):
            total_months = 0.0
            for role in roles:
                years_val = role.get("years") or role.get("duration")
                if years_val:
                    try:
                        val = float(years_val)
                        total_months += val * 12
                        continue
                    except ValueError:
                        pass
                    
                    parts = re.split(r'[-–—]|(?:\bto\b)', str(years_val))
                    if len(parts) == 2:
                        start = parse_date(parts[0])
                        end = parse_date(parts[1])
                        if start and end:
                            diff = end - start
                            months = diff.days / 30.44
                            if months > 0:
                                total_months += months
                                continue
                    
                    y_match = re.search(r'(\d+)\s*y', str(years_val), re.IGNORECASE)
                    m_match = re.search(r'(\d+)\s*m', str(years_val), re.IGNORECASE)
                    r_months = 0.0
                    if y_match:
                        r_months += float(y_match.group(1)) * 12
                    if m_match:
                        r_months += float(m_match.group(1))
                    if r_months > 0:
                        total_months += r_months
                        continue
            if total_months > 0:
                # If they have a fraction, let's round or cast to int.
                # If total_months is less than 6, round to 0 (fresher), otherwise round to nearest integer.
                return max(0, int(round(total_months / 12.0)))
    except Exception:
        pass
    # Fallback: look for year patterns in text
    try:
        match = re.search(r'(\d+)\+?\s*years?', candidate_experience, re.IGNORECASE)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    
    # Original fallback: list count
    try:
        exp_list = json.loads(candidate_experience)
        if isinstance(exp_list, list):
            return len(exp_list) * 2
    except Exception:
        pass
    return 1  # assume at least 1 year


def _skill_match(
    candidate_skills: List[str],
    job_skills: List[str]
) -> Tuple[float, List[str]]:
    """
    Compute Jaccard-style skill match.
    Returns (score_0_to_100, missing_skill_names).
    """
    if not job_skills:
        return 75.0, []

    cand_lower = {s.lower().strip() for s in candidate_skills}
    job_lower = [s.lower().strip() for s in job_skills]

    matched = []
    missing = []
    for js in job_lower:
        # Check if candidate has this skill (partial match allowed)
        found = any(
            js in cs or cs in js or
            js.replace(".", "").replace(" ", "") in cs.replace(".", "").replace(" ", "")
            for cs in cand_lower
        )
        if found:
            matched.append(js)
        else:
            missing.append(js.title())

    score = (len(matched) / len(job_lower)) * 100.0
    return score, missing


def _experience_match(candidate_years: int, job_experience_str: str) -> float:
    """Compare candidate years vs job required years."""
    req_years = _parse_years(job_experience_str)

    if req_years == 0:  # Fresher role
        return 100.0 if candidate_years <= 2 else 85.0

    diff = candidate_years - req_years
    if diff >= 0:
        return 100.0 if diff <= 2 else 90.0   # Slightly overqualified is fine
    if diff == -1:
        return 75.0
    if diff == -2:
        return 50.0
    return 25.0   # Under-qualified by 3+ years


def _education_match(candidate_education: Optional[str], job_description: str) -> float:
    """Check if candidate's education meets job requirements."""
    if not candidate_education:
        return 50.0

    desc_lower = job_description.lower()
    edu_lower = candidate_education.lower()

    # If job doesn't specify education, neutral
    if not any(kw in desc_lower for kw in ["degree", "bachelor", "btech", "mtech", "ms ", "b.e", "m.e"]):
        return 75.0

    # Candidate has a degree
    if any(kw in edu_lower for kw in ["b.tech", "btech", "b.e", "bachelor", "m.tech", "mtech", "m.s", "master", "mca", "bca"]):
        return 100.0

    return 40.0


def _location_match(candidate_location: Optional[str], job_location: str) -> float:
    """Compare locations."""
    if not candidate_location:
        return 50.0

    j_loc = job_location.lower()
    c_loc = candidate_location.lower()

    if "remote" in j_loc:
        return 100.0

    # Extract city keywords
    cities = ["bangalore", "bengaluru", "hyderabad", "mumbai", "pune", "chennai",
              "delhi", "noida", "gurgaon", "gurugram", "kolkata", "ahmedabad"]

    for city in cities:
        if city in j_loc and city in c_loc:
            return 100.0

    # Same country (India)
    if "india" in j_loc and "india" in c_loc:
        return 60.0

    return 40.0


def _projects_match(candidate_projects: Optional[str], job_skills: List[str]) -> float:
    """Check if candidate's projects mention job skills."""
    if not candidate_projects or not job_skills:
        return 50.0

    proj_lower = candidate_projects.lower()
    skill_hits = sum(1 for s in job_skills if s.lower() in proj_lower)

    if skill_hits >= 3:
        return 100.0
    if skill_hits >= 2:
        return 80.0
    if skill_hits >= 1:
        return 60.0
    return 40.0


def calculate_match(
    candidate_skills: List[str],
    candidate_experience: Optional[str],
    candidate_education: Optional[str],
    candidate_location: Optional[str],
    candidate_projects: Optional[str],
    job_skills: List[str],
    job_experience_str: str,
    job_description: str,
    job_location: str,
) -> MatchResult:
    """
    Main match calculation function.
    Weights: Skill 50% | Experience 20% | Education 10% | Location 10% | Projects 10%
    """
    cand_years = _candidate_years(candidate_experience)

    skill_score, missing = _skill_match(candidate_skills, job_skills)
    exp_score = _experience_match(cand_years, job_experience_str)
    edu_score = _education_match(candidate_education, job_description)
    loc_score = _location_match(candidate_location, job_location)
    proj_score = _projects_match(candidate_projects, job_skills)

    final_score = (
        skill_score * 0.50 +
        exp_score   * 0.20 +
        edu_score   * 0.10 +
        loc_score   * 0.10 +
        proj_score  * 0.10
    )

    return MatchResult(
        match_score=min(100, int(final_score)),
        missing_skills=missing[:8],  # Cap to 8
        skill_match=skill_score,
        experience_match=exp_score,
        education_match=edu_score,
        location_match=loc_score,
        projects_match=proj_score,
    )
