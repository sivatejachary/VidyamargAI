"""
Base MCP Server — all MCP tool servers inherit from this.
Provides permission checking and logging.
"""
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger("app.mcp")


class BaseMCPServer:
    """Base class for all MCP Tool Servers."""
    required_permission: str = "read"
    server_name: str = "BaseMCP"

    def check_permission(self, user_role: str, db: Session) -> bool:
        """Check if the given role has required permission for this server."""
        try:
            from app.models.mcp_models import ToolPermission
            # Admin always has full access
            if user_role == "admin" or user_role == "super_admin":
                return True
            perm = db.query(ToolPermission).filter(
                ToolPermission.role == user_role,
                ToolPermission.tool.in_([self.__class__.__name__, "*"])
            ).first()
            if not perm:
                # Default: candidates have read access to everything
                return self.required_permission == "read"
            return self.required_permission in perm.grants
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return True  # Fail open for now

    def _log_call(self, method_name: str, user_id: int):
        logger.info(f"[{self.server_name}] {method_name}() called for user_id={user_id}")
