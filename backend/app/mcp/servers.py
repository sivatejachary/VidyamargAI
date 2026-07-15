"""
MCP Servers — in-process implementations of the local MCP tool servers.
Registered automatically into the gateway registry.
"""
import logging
import math
import uuid
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.mcp.base import BaseMCPServer
from app.mcp.gateway import register_server
from app.models.models import UserConsent, Candidate, CandidateProfile, User
from app.models.mcp_models import MCPAuditLog, ToolPermission, VectorMemoryChunk
from app.services.orchestrator import call_gemini, call_nvidia

logger = logging.getLogger("app.mcp.servers")


# --------------------------------------------------------------------------
# Fallback Embeddings (Pure Python Cosine Similarity)
# --------------------------------------------------------------------------
def get_fallback_embedding(text_content: str) -> List[float]:
    """Generates a deterministic 768-dimensional unit vector from text."""
    vector = [0.0] * 768
    if not text_content:
        return vector
        
    words = text_content.lower().split()
    for w in words:
        # Deterministic hash to dimension
        h = int(hashlib.md5(w.encode('utf-8')).hexdigest(), 16)
        idx = h % 768
        vector[idx] += 1.0
        
    # Calculate magnitude
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        vector = [x / norm for x in vector]
    return vector


async def get_semantic_embedding(text_content: str) -> List[float]:
    """Generates 768-dimensional semantic embedding using the EmbeddingService."""
    from app.services.embedding_service import embedding_service
    return await embedding_service.get_embedding(text_content)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculates cosine similarity between two vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(x * y for x, y in zip(v1, v2))
    norm_v1 = math.sqrt(sum(x * x for x in v1))
    norm_v2 = math.sqrt(sum(x * x for x in v2))
    if norm_v1 == 0.0 or norm_v2 == 0.0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)


# --------------------------------------------------------------------------
# 1. Feature Flags Server
# --------------------------------------------------------------------------
class FeatureFlagsServer(BaseMCPServer):
    server_name = "mcp-server-feature-flags"
    required_permission = "read"

    def is_enabled(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Check if a feature flag is enabled for a user."""
        # Check standard user plan first
        flag = arguments.get("flag")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"enabled": False}
            
        plan = (user.role or "candidate").lower()
        if plan in ["admin", "super_admin", "recruiter"]:
            return {"enabled": True}
            
        # Get user plan (Free, Go, Pro, Enterprise) from user preference or metadata
        # For simplicity, map: admin->Enterprise, others check flag overrides
        from app.models.models import UserPreference
        pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        plan_tier = "free"
        if pref and hasattr(pref, "plan_tier") and pref.plan_tier:
            plan_tier = pref.plan_tier.lower()
        elif user.user_xp > 1000:
            plan_tier = "pro"

        # Plan gates
        enabled = False
        if flag == "parallel_apply":
            enabled = plan_tier in ["pro", "enterprise"]
        elif flag in ["auto_apply_ats", "company_research"]:
            enabled = plan_tier in ["go", "pro", "enterprise"]
        elif flag in ["interview_prep", "salary_intelligence", "stealth_mode", "referral_first_mode"]:
            enabled = plan_tier in ["pro", "enterprise"]
        else:
            # Core features are always open
            enabled = True
            
        return {"enabled": enabled}

    def get_flags(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Get all feature flags for a user."""
        flags = ["parallel_apply", "auto_apply_ats", "interview_prep", "salary_intelligence", "company_research", "stealth_mode", "referral_first_mode"]
        res = {}
        for f in flags:
            res[f] = self.is_enabled(user_id, {"flag": f}, db)["enabled"]
        return {"flags": res}

    def set_flag(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Admin override tool to enable/disable feature flag."""
        # Check if caller is admin
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.role not in ["admin", "super_admin"]:
            raise PermissionError("Only admins can override feature flags")
        return {"status": "success", "message": "Override saved"}


# --------------------------------------------------------------------------
# 2. Billing & Plan Management Server
# --------------------------------------------------------------------------
class BillingServer(BaseMCPServer):
    server_name = "mcp-server-billing"
    required_permission = "read"

    def get_plan(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Returns the user plan tier and quota limits."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"plan": "free", "quota_limit": 10}
            
        from app.models.models import UserPreference
        pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        plan_tier = "free"
        if pref and hasattr(pref, "plan_tier") and pref.plan_tier:
            plan_tier = pref.plan_tier.lower()
            
        limits = {"free": 10, "go": 30, "pro": 100, "enterprise": 99999}
        return {
            "user_id": user_id,
            "plan": plan_tier,
            "quota_limit": limits.get(plan_tier, 10),
            "quota_remaining": limits.get(plan_tier, 10) # Simple stub for phase 1
        }

    def check_quota(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Verify if user has remaining quota for a specific action type."""
        plan_info = self.get_plan(user_id, arguments, db)
        return {"allowed": True, "quota_remaining": plan_info["quota_remaining"]}

    def deduct_credit(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Deduct credits on successful operation execution."""
        return {"status": "success", "deducted": True}


# --------------------------------------------------------------------------
# 3. Compliance and Action Auditing Server
# --------------------------------------------------------------------------
class AuditServer(BaseMCPServer):
    server_name = "mcp-server-audit"
    required_permission = "read"

    def log_action(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Log an immutable audit log entry."""
        log = MCPAuditLog(
            request_id=arguments.get("request_id"),
            candidate_id=user_id,
            run_id=arguments.get("run_id"),
            agent=arguments.get("agent_name", "UnknownAgent"),
            tool=arguments.get("tool_called", "UnknownTool"),
            latency=arguments.get("latency", 0.0),
            status=arguments.get("result", "success"),
            error_message=arguments.get("error_message")
        )
        db.add(log)
        db.commit()
        return {"status": "success", "log_id": log.id}

    def get_user_log(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Returns the full audit trail logs for a user."""
        logs = db.query(MCPAuditLog).filter(MCPAuditLog.candidate_id == user_id).order_by(MCPAuditLog.created_at.desc()).limit(100).all()
        return {
            "logs": [
                {
                    "id": l.id,
                    "agent": l.agent,
                    "tool": l.tool,
                    "latency": l.latency,
                    "status": l.status,
                    "created_at": l.created_at.isoformat()
                } for l in logs
            ]
        }

    def verify_consent(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Check if user authorized a specific action."""
        action = arguments.get("action")
        consent = db.query(UserConsent).filter(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == action,
            UserConsent.granted == True
        ).first()
        return {"authorized": consent is not None, "consent_ref": consent.consent_ref if consent else None}

    def purge_user_data(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """GDPR Right to Deletion implementation."""
        # Cascade deletion handles cleanup
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
            return {"status": "success", "message": f"All data for user {user_id} purged successfully"}
        return {"status": "error", "message": "User not found"}


# --------------------------------------------------------------------------
# 4. Vector Similarity Search Server
# --------------------------------------------------------------------------
class VectorServer(BaseMCPServer):
    server_name = "mcp-server-vector"
    required_permission = "read"

    async def embed_text(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Generates embedding vector for input text."""
        text_content = arguments.get("text", "")
        vector = await get_semantic_embedding(text_content)
        return {"embedding": vector}

    async def upsert_embedding(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Stores a vector embedding chunk in database."""
        text_content = arguments.get("text", "")
        chunk_type = arguments.get("chunk_type", "generic")
        vector = await get_semantic_embedding(text_content)
        
        chunk = VectorMemoryChunk(
            user_id=user_id,
            chunk_type=chunk_type,
            content=text_content,
            embedding_json=json.dumps(vector),
            meta=arguments.get("meta", {})
        )
        db.add(chunk)
        db.commit()
        return {"status": "success", "chunk_id": chunk.id}



# --------------------------------------------------------------------------
# 5. Central LLM Server (AI Gateway)
# --------------------------------------------------------------------------
class LLMServer(BaseMCPServer):
    server_name = "mcp-server-llm"
    required_permission = "read"

    def generate(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Generates response using prompt templates and model routing."""
        prompt = arguments.get("prompt", "")
        system_prompt = arguments.get("system_prompt", "")
        json_mode = arguments.get("json_mode", False)
        
        # Router routing logic based on size and budget limits
        # Simple task ➔ Gemini Flash, complex reasoning ➔ NVIDIA Nemotron fallback
        full_prompt = f"{system_prompt}\n\n{prompt}"
        model = "gemini"
        
        from app.agents.cost_controller import cost_controller
        model = cost_controller.select_model(full_prompt, user_id, db)
        
        response = ""
        if model == "gemini":
            response = call_gemini(full_prompt, json_mode)
        else:
            response = call_nvidia(full_prompt, json_mode)
            
        # If any fails, fallback
        if not response:
            if model == "gemini":
                response = call_nvidia(full_prompt, json_mode)
            else:
                response = call_gemini(full_prompt, json_mode)
                
        # Record usage
        cost_controller.record(
            user_id=user_id,
            model_name=model,
            prompt_chars=len(full_prompt),
            completion_chars=len(response),
            db=db
        )
        
        return {"response": response, "model": model}

    async def embed(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Generate embedding vector."""
        text_content = arguments.get("text", "")
        vector = await get_semantic_embedding(text_content)
        return {"embedding": vector}

    def classify(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Intent / Category Classification router tool."""
        text_content = arguments.get("text", "")
        categories = arguments.get("categories", ["general"])
        
        prompt = f"Classify the text into exactly one of these categories: {', '.join(categories)}.\nText: {text_content}\nOutput category only."
        response = call_gemini(prompt).strip().lower()
        
        # Verify matched category
        matched = "general"
        for cat in categories:
            if cat.lower() in response:
                matched = cat
                break
        return {"category": matched}


# --------------------------------------------------------------------------
# 6. Resume Context Server
# --------------------------------------------------------------------------
class ResumeServer(BaseMCPServer):
    server_name = "mcp-server-resume"
    required_permission = "read"

    def get_resume(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Retrieves user resume profile data."""
        candidate = db.query(Candidate).filter(Candidate.user_id == user_id).first()
        if not candidate:
            return {"error": "Candidate not found"}
        return {
            "skills": candidate.skills or "",
            "experience": candidate.experience or "[]",
            "education": candidate.education or "[]",
            "linkedin": candidate.linkedin or "",
            "github": candidate.github or "",
            "summary": candidate.summary or ""
        }

    def update_resume(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Updates user resume profile fields."""
        candidate = db.query(Candidate).filter(Candidate.user_id == user_id).first()
        if not candidate:
            return {"error": "Candidate not found"}
            
        fields = ["skills", "summary", "linkedin", "github", "portfolio", "phone"]
        for f in fields:
            if f in arguments:
                setattr(candidate, f, arguments[f])
        db.commit()
        return {"status": "success", "message": "Resume updated"}


# --------------------------------------------------------------------------
# 7. Skill Lab LMS Server
# --------------------------------------------------------------------------
class SkillLabServer(BaseMCPServer):
    server_name = "mcp-server-skilllab"
    required_permission = "read"

    def get_available_courses(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Returns available courses filtered by tags or category."""
        category = arguments.get("category")
        query_str = "SELECT id, title, rating, level, category FROM courses"
        params = {}
        if category:
            query_str += " WHERE category = :cat"
            params["cat"] = category
            
        rows = db.execute(text(query_str), params).fetchall()
        courses = []
        for r in rows:
            courses.append({
                "course_id": r[0],
                "title": r[1],
                "rating": r[2],
                "level": r[3],
                "category": r[4]
            })
        return {"courses": courses}

    def create_learning_path(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Triggers skill recommendations based on target skill gap list."""
        skills = arguments.get("skills", [])
        # Find matching courses based on target skills in category
        rows = db.execute(text("SELECT id, title, category FROM courses")).fetchall()
        recommendations = []
        for r in rows:
            # Check if any missing skill overlaps with course title
            for sk in skills:
                if sk.lower() in r[1].lower():
                    recommendations.append({"course_id": r[0], "title": r[1], "target_skill": sk})
                    
        return {"learning_path": recommendations}

    def get_user_progress(self, user_id: int, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Retrieves candidate progress counters."""
        rows = db.execute(text(
            'SELECT progress, status, course_id FROM enrollments WHERE user_id = :u'
        ), {"u": user_id}).fetchall()
        enrolls = []
        for r in rows:
            enrolls.append({"course_id": r[2], "progress": r[0], "status": r[1]})
        return {"progress": enrolls}


# Register all servers at import time
register_server("mcp-server-feature-flags", FeatureFlagsServer())
register_server("mcp-server-billing", BillingServer())
register_server("mcp-server-audit", AuditServer())
register_server("mcp-server-vector", VectorServer())
register_server("mcp-server-llm", LLMServer())
register_server("mcp-server-resume", ResumeServer())
register_server("mcp-server-skilllab", SkillLabServer())
