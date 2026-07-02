import time
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.tools.base import BaseAgentTool

# Simple in-memory rate-limiting storage fallback if redis isn't available
_RATE_LIMIT_CACHE = {} # {f"{user_id}:{tool_name}": [timestamps]}

class PolicyEngine:
    """
    PolicyEngine evaluates authorization, domain scopes, and rate limits
    before executing agent tools.
    """
    
    @staticmethod
    def check_permissions(user_role: str, tool_name: str) -> Tuple[bool, str]:
        """
        Enforce role-based access control.
        """
        # Admin can do anything
        if user_role == "admin":
            return True, "Authorized"
            
        # Candidates are restricted from administrative or sensitive config tools
        admin_only_tools = ["db_wipe", "system_status_check", "sync_all_jobs"]
        if tool_name in admin_only_tools:
            return False, f"Permission denied: Tool '{tool_name}' requires admin role."
            
        return True, "Authorized"

    @staticmethod
    def check_rate_limits(user_id: int, tool: BaseAgentTool) -> Tuple[bool, str]:
        """
        Verify rate limits (limit requests per window period).
        """
        now = time.time()
        key = f"{user_id}:{tool.name}"
        
        # Initialize or clean up expired timestamps
        if key not in _RATE_LIMIT_CACHE:
            _RATE_LIMIT_CACHE[key] = []
            
        # Filter timestamps within active window period
        window_start = now - tool.rate_limit_period
        _RATE_LIMIT_CACHE[key] = [t for t in _RATE_LIMIT_CACHE[key] if t > window_start]
        
        if len(_RATE_LIMIT_CACHE[key]) >= tool.rate_limit_limit:
            return False, f"Rate limit exceeded: tool {tool.name} is restricted to {tool.rate_limit_limit} calls per {tool.rate_limit_period} seconds."
            
        # Register new call timestamp
        _RATE_LIMIT_CACHE[key].append(now)
        return True, "Authorized"

    @staticmethod
    def check_domain_scope(tool_name: str, domain: str) -> Tuple[bool, str]:
        """
        Ensure external requests are within the allowed domain scope.
        """
        allowed_domains = [
            "api.nvidia.com", "integrate.api.nvidia.com", 
            "api.gemini.com", "generativelanguage.googleapis.com", 
            "linkedin.com", "indeed.com", "github.com"
        ]
        
        # Allow domestic local hosts and approved domains
        if domain == "localhost" or any(allowed in domain for allowed in allowed_domains):
            return True, "Authorized"
            
        return False, f"Domain scope violation: domain '{domain}' is not on the permitted safety list."

    @classmethod
    def evaluate(cls, user_id: int, user_role: str, tool: BaseAgentTool, arguments: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Run all policy checks in sequence.
        """
        # 1. Check role-based access
        allowed, msg = cls.check_permissions(user_role, tool.name)
        if not allowed:
            return False, msg
            
        # 2. Check rate limit
        allowed, msg = cls.check_rate_limits(user_id, tool)
        if not allowed:
            return False, msg
            
        # 3. Check domain if target domain argument is provided
        target_domain = arguments.get("domain") or arguments.get("url")
        if target_domain and isinstance(target_domain, str):
            # Simple domain extraction
            if "://" in target_domain:
                target_domain = target_domain.split("://")[1].split("/")[0]
            allowed, msg = cls.check_domain_scope(tool.name, target_domain)
            if not allowed:
                return False, msg
                
        return True, "Authorized"
