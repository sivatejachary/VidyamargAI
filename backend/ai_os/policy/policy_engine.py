import logging
from typing import Dict, Any, List
from ..schemas.memory import CandidatePreferencesSchema

logger = logging.getLogger("ai_os.policy.policy_engine")

class PolicyViolation(Exception):
    """Raised when a policy engine check fails a strict filter constraint."""
    pass

class PolicyEngine:
    """
    Enforces user preference constraints and filters output items.
    """
    def __init__(self):
        pass

    async def evaluate_tool_input(self, tool_name: str, arguments: Dict[str, Any], preferences: CandidatePreferencesSchema) -> bool:
        """
        Validates if tool arguments comply with user constraints before execution.
        """
        logger.info(f"Policy evaluation: checking inputs for tool: '{tool_name}'")
        
        # Prevent automated applications if user-configured rules require verification
        if tool_name == "apply_job_automatically":
            if preferences.approval_required:
                logger.warning("Policy violation: Automated applications are blocked. User approval required.")
                return False

        # Apply technology exclusions
        if "description" in arguments or "skills" in arguments:
            payload_text = str(arguments.get("description", "")) + " " + " ".join(arguments.get("skills", []))
            for tech in preferences.excluded_technologies:
                if tech.strip().lower() in payload_text.lower():
                    logger.warning(f"Policy violation: Action references excluded technology '{tech}'. Blocking tool run.")
                    return False

        return True

    async def filter_job_matches(self, jobs: List[Dict[str, Any]], preferences: CandidatePreferencesSchema) -> List[Dict[str, Any]]:
        """
        Filters discovered jobs based on locations, salary, and technology preferences.
        """
        filtered_jobs = []
        for job in jobs:
            try:
                # 1. Location constraints
                job_location = job.get("location", "").lower()
                if preferences.locations:
                    loc_match = any(loc.lower() in job_location for loc in preferences.locations)
                    if not loc_match:
                        continue

                # 2. Remote constraints
                if preferences.remote_only:
                    if "remote" not in job_location and not job.get("is_remote", False):
                        continue

                # 3. Technology exclusions
                job_desc = (job.get("description", "") + " " + job.get("title", "")).lower()
                tech_excluded = False
                for tech in preferences.excluded_technologies:
                    if tech.strip().lower() in job_desc:
                        tech_excluded = True
                        break
                if tech_excluded:
                    continue

                # 4. Salary constraints
                if preferences.preferred_salary:
                    job_salary = job.get("salary")
                    if job_salary and float(job_salary) < float(preferences.preferred_salary):
                        continue

                filtered_jobs.append(job)
            except Exception as e:
                logger.error(f"Error filtering job {job.get('id')}: {e}")
                continue
                
        return filtered_jobs
