import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SkillGapAgent:
    def __init__(self, top_jobs: List[Dict[str, Any]]):
        self.top_jobs = top_jobs

    def analyze_gaps(self) -> List[Dict[str, Any]]:
        """
        Analyzes the top 10 ranked jobs to find missing skills and determines their priority:
        - High: missing in > 50% of top jobs.
        - Medium: missing in 25%-50% of top jobs.
        - Low: missing in < 25% of top jobs.
        """
        if not self.top_jobs:
            return []

        # Focus on top 10 jobs to determine industry demand
        target_jobs = self.top_jobs[:10]
        total_jobs = len(target_jobs)

        missing_counts = {}
        for job in target_jobs:
            missing = job.get("missing_skills", [])
            for sk in missing:
                sk_title = sk.strip().title()
                if sk_title:
                    missing_counts[sk_title] = missing_counts.get(sk_title, 0) + 1

        skill_gaps = []
        for skill, count in missing_counts.items():
            percentage = (count / total_jobs) * 100.0
            
            if percentage > 50.0:
                priority = "High"
            elif percentage >= 25.0:
                priority = "Medium"
            else:
                priority = "Low"

            skill_gaps.append({
                "skill": skill,
                "missing_in_percentage": int(round(percentage)),
                "priority": priority,
                "count": count
            })

        # Sort by percentage descending
        skill_gaps.sort(key=lambda x: x["missing_in_percentage"], reverse=True)
        
        logger.info(f"SkillGapAgent: Analyzed gaps. Identified {len(skill_gaps)} missing skills across top jobs")
        return skill_gaps
