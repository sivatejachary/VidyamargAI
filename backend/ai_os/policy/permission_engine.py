import logging
from typing import Dict, Any

logger = logging.getLogger("ai_os.policy.permission_engine")

class PermissionEngine:
    """
    Evaluates permissions based on user attributes, roles, and tool scope.
    """
    def __init__(self):
        pass

    async def check_permission(self, candidate_id: str, tool_permission: str, context: Dict[str, Any]) -> bool:
        """
        Validates if the active candidate context matches required permission scopes.
        """
        logger.info(f"Checking permission: '{tool_permission}' for candidate: '{candidate_id}'")
        
        # Enforce basic ownership boundary
        user_id = context.get("user_id")
        user_role = context.get("user_role", "candidate")

        if user_role == "admin" or user_role == "super_admin":
            logger.info("Admin override granted.")
            return True

        if not user_id or str(user_id) != str(candidate_id):
            logger.warning(f"Access Denied: Candidate ownership mismatch. User '{user_id}' does not own Candidate '{candidate_id}'")
            return False

        # Role-based constraints for advanced tools
        if tool_permission == "recruiter:access":
            if user_role not in ["recruiter", "admin"]:
                logger.warning(f"Access Denied: Role '{user_role}' is not authorized for recruiter tool access.")
                return False

        if tool_permission == "analytics:billing":
            if user_role not in ["admin", "super_admin"]:
                logger.warning(f"Access Denied: Role '{user_role}' cannot access billing analytics tools.")
                return False

        logger.info(f"Permission '{tool_permission}' granted successfully.")
        return True
