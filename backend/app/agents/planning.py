import logging
from typing import List
from app.agents.resume_intelligence import CandidateProfileData
from app.services.job_connectors.query_generator import SKILL_TO_ROLE, FALLBACK_ROLES

logger = logging.getLogger(__name__)

class PlanningAgent:
    def __init__(self, profile: CandidateProfileData):
        self.profile = profile

    def generate_strategy(self) -> List[str]:
        """
        Generates multiple search queries and variations based on candidate profile.
        Includes role, location, remote, and experience level variations.
        """
        skills = self.profile.skills
        exp_years = self.profile.experience_years

        if not skills:
            skills = ["Python"]

        # 1. Identify primary role targets from skills
        roles = []
        for skill in skills[:3]:
            skill_lower = skill.lower().strip()
            if skill_lower in SKILL_TO_ROLE:
                roles.extend(SKILL_TO_ROLE[skill_lower])
        
        # Fallback to general roles if none matched
        if not roles:
            roles = [f"{skills[0]} Developer"] + FALLBACK_ROLES

        # Deduplicate roles
        seen_roles = set()
        deduped_roles = []
        for r in roles:
            r_l = r.lower()
            if r_l not in seen_roles:
                seen_roles.add(r_l)
                deduped_roles.append(r)
        
        # Limit to top 3 roles to avoid combinatorial explosion
        target_roles = deduped_roles[:3]

        # 2. Add seniority modifiers based on experience years
        seniority = ""
        if exp_years >= 5.0:
            seniority = "Senior"
        elif exp_years >= 3.0:
            seniority = "Lead"
        elif exp_years <= 1.0:
            # Check if fresher/intern
            seniority = "Junior"

        queries = set()

        # 3. Create combinations of Role + Location/Remote
        locations = ["Remote", "India", "Bangalore", "Hyderabad"]

        for role in target_roles:
            # Base query
            role_title = f"{seniority} {role}" if seniority else role
            queries.add(f'"{role_title}" India jobs')
            
            # Location variations
            for loc in locations[:2]:  # Remote, India
                queries.add(f'"{role_title}" {loc}')
            
            # Skill inclusion variation
            if len(skills) >= 2:
                queries.add(f'"{role_title}" "{skills[0]}"')
                
        # Fallbacks/additional
        if seniority == "Junior":
            queries.add(f'"{target_roles[0]}" fresher')
            queries.add(f'"{target_roles[0]}" intern')
        elif seniority == "Senior" or seniority == "Lead":
            queries.add(f'senior "{target_roles[0]}" architect')

        # Convert to list and limit to 8 queries (to optimize performance under 10 seconds)
        final_queries = list(queries)[:8]
        logger.info(f"PlanningAgent: Generated {len(final_queries)} query variations: {final_queries}")
        return final_queries
