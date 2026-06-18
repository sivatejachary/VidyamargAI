"""
Query Builder — converts candidate skills, preferences, and profiles
into targeted search queries for Google, LinkedIn, Naukri, and Indeed.
"""
from typing import List, Dict, Any


def build_queries(candidate: Any, preferences: dict = None) -> List[str]:
    """
    Builds a list of search queries based on candidate profile and preferences.
    """
    skills = [s.strip() for s in (candidate.skills or "").split(",") if s.strip()]
    
    # Extract roles and preferences
    pref_roles = []
    location_pref = "India"
    work_mode = "any"
    
    if preferences:
        pref_roles = preferences.get("preferred_roles", [])
        locs = preferences.get("location_preferences", [])
        if locs:
            location_pref = locs[0]
        work_mode = preferences.get("work_mode", "any")

    # Fallback to candidate summary if no preferred roles
    if not pref_roles:
        # Simple extraction from candidate summary/title
        if candidate.summary:
            words = candidate.summary.split()
            # look for common roles
            for r in ["Software Engineer", "Full Stack Developer", "Backend Developer", "Frontend Developer", "ML Engineer", "Data Scientist"]:
                if r.lower() in candidate.summary.lower():
                    pref_roles.append(r)
                    break
        if not pref_roles:
            pref_roles = ["Software Engineer"]

    queries = []
    
    # 1. Site-specific queries for top portals
    for role in pref_roles[:2]:
        # LinkedIn
        queries.append(f'site:linkedin.com/jobs/view "{role}" "{location_pref}"')
        # Naukri
        queries.append(f'site:naukri.com/job-listings "{role}"')
        # Indeed
        queries.append(f'site:indeed.com/viewjob "{role}"')

    # 2. Skill-specific queries if we have skills
    if skills:
        top_skills = " ".join(skills[:2])
        for role in pref_roles[:1]:
            queries.append(f'site:linkedin.com/jobs/view "{role}" {top_skills}')
            if work_mode == "remote" or work_mode == "any":
                queries.append(f'"{role}" "{top_skills}" remote jobs')

    return list(set(queries))
