import logging
from ..runtime.tool_context import ToolContext

logger = logging.getLogger("ai_os.tools.resume_tool.permissions")

def check_resume_permissions(candidate_id: str, context: ToolContext) -> bool:
    """
    Checks if active context parameters grant permission to modify candidate data.
    """
    logger.info(f"Checking candidate ownership for: '{candidate_id}'")
    
    # Enforce basic ownership boundaries
    if str(context.user_id) != str(candidate_id):
        # Allow admin overrides
        role = context.permissions.get("role", "candidate")
        if role in ["admin", "super_admin"]:
            logger.info("Admin scope override authorized.")
            return True
            
        logger.warning(f"Unauthorized: User '{context.user_id}' does not own Candidate record '{candidate_id}'")
        return False
        
    return True
