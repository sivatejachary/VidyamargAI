from typing import Dict, Any, List, Set, Tuple
import logging

logger = logging.getLogger("app.job_discovery.workers.matching.scoring")

class MatchScorer:
    WEIGHTS = {
        "skill": 0.35,
        "semantic": 0.25,
        "experience": 0.15,
        "seniority": 0.10,
        "location": 0.08,
        "salary": 0.07,
    }

    SENIORITY_RANK = {
        "intern": 0, "junior": 1, "mid": 2, "senior": 3, "lead": 3, "director": 4, "vp": 5, "cxo": 6
    }

    def compute_match(
        self,
        candidate_profile: Dict[str, Any],
        job_data: Dict[str, Any],
        semantic_score: float = 50.0
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Computes structural match scoring and returns the overall score + match metadata.
        """
        # 1. Skill Score
        candidate_skills = set(s.lower() for s in candidate_profile.get("skills", []))
        job_skills = set(s.lower() for s in (job_data.get("required_skills") or []))
        pref_skills = set(s.lower() for s in (job_data.get("preferred_skills") or []))

        if job_skills:
            matched_required = len(candidate_skills & job_skills)
            skill_score = min(100.0, (matched_required / len(job_skills)) * 100)
            if pref_skills:
                pref_match = len(candidate_skills & pref_skills) / max(len(pref_skills), 1)
                skill_score = min(100.0, skill_score + pref_match * 15)
        else:
            skill_score = 60.0

        # 2. Experience Score
        candidate_exp = float(candidate_profile.get("experience_years") or 0)
        min_exp = float(job_data.get("experience_min_years") or 0)
        max_exp = float(job_data.get("experience_max_years") or 30)

        if min_exp <= candidate_exp <= max_exp:
            exp_score = 100.0
        elif candidate_exp < min_exp:
            gap = min_exp - candidate_exp
            exp_score = max(0.0, 100.0 - gap * 20)
        else:
            over = candidate_exp - max_exp
            exp_score = max(60.0, 100.0 - over * 5)

        # 3. Seniority Score
        cand_seniority = (candidate_profile.get("seniority") or "mid").lower()
        cand_seniority_rank = self.SENIORITY_RANK.get(cand_seniority, 2)
        
        job_seniority = (job_data.get("seniority") or "mid").lower()
        job_seniority_rank = self.SENIORITY_RANK.get(job_seniority, 2)
        
        seniority_diff = abs(cand_seniority_rank - job_seniority_rank)
        seniority_score = max(0.0, 100.0 - seniority_diff * 25)

        # 4. Location Score
        candidate_locations = set(l.lower() for l in (candidate_profile.get("locations") or []))
        job_location = (job_data.get("location") or "").lower()
        job_country = (job_data.get("country") or "").lower()

        if job_data.get("is_remote"):
            location_score = 95.0
        elif not candidate_locations:
            location_score = 65.0
        elif any(loc in job_location or loc in job_country for loc in candidate_locations):
            location_score = 100.0
        else:
            location_score = 30.0

        # 5. Salary Score
        salary_score = 70.0

        # Composite score
        overall_score = (
            skill_score * self.WEIGHTS["skill"] +
            semantic_score * self.WEIGHTS["semantic"] +
            exp_score * self.WEIGHTS["experience"] +
            seniority_score * self.WEIGHTS["seniority"] +
            location_score * self.WEIGHTS["location"] +
            salary_score * self.WEIGHTS["salary"]
        )

        # Quality boost
        quality_score = float(job_data.get("quality_score", 0.5))
        overall_score = min(100.0, overall_score * (0.7 + 0.3 * quality_score))

        # Missing skills
        missing = list(job_skills - candidate_skills)[:10]
        gap_severity = "none"
        if missing:
            ratio = len(missing) / max(len(job_skills), 1)
            gap_severity = "minor" if ratio < 0.3 else "moderate" if ratio < 0.6 else "major"

        # Match reasons
        reasons = []
        if skill_score >= 70:
            matched = list((candidate_skills & job_skills))[:3]
            if matched:
                reasons.append(f"Strong skill match: {', '.join(s.title() for s in matched)}")
        if exp_score >= 90:
            reasons.append(f"{int(candidate_exp)}+ years experience aligns with role requirements")
        if location_score >= 90:
            reasons.append("Location or remote preference matches")
        if not reasons:
            reasons.append("Profile is a reasonable match for this role")

        career_growth_score = max(0.0, seniority_score * 0.5 + exp_score * 0.3 + skill_score * 0.2 - 10)

        meta = {
            "skill_score": round(skill_score, 2),
            "experience_score": round(exp_score, 2),
            "location_score": round(location_score, 2),
            "seniority_score": round(seniority_score, 2),
            "career_growth_score": round(career_growth_score, 2),
            "missing_skills": missing,
            "skill_gap_severity": gap_severity,
            "match_reasons": reasons
        }

        return round(overall_score, 2), meta
