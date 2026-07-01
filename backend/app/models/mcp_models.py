"""
VidyaMarg AI OS — MCP Models
New database tables for the agent OS layer.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class ToolPermission(Base):
    """
    Controls what each MCP server can do per user role.
    Seeded at startup with default role-based permissions.
    """
    __tablename__ = "tool_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False)    # "candidate", "admin", "recruiter"
    tool = Column(String, nullable=False)    # "ResumeMCPServer", "JobMCPServer", "*"
    grants = Column(String, nullable=False)  # "read" | "read,write" | "read,apply" | "full"
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_tool_permission_role_tool", "role", "tool"),)


class AgentActivity(Base):
    """
    Activity feed — every meaningful agent action stored here.
    Powers the live dashboard activity feed.
    """
    __tablename__ = "agent_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agent_name = Column(String, nullable=False)  # "LearningAgent", "JobAgent"
    action = Column(String, nullable=False)       # "found_42_jobs", "detected_aws_gap"
    detail = Column(Text, nullable=True)          # Human-readable description
    meta = Column(JSON, default=dict)             # {job_count: 42, top_job: "ML Engineer"}
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_agent_activity_user_created", "user_id", "created_at"),)


class HumanActionItem(Base):
    """
    Items requiring human attention before an agent can continue.
    Used for: CAPTCHA, OTP, 2FA, Payment, Manual Review.
    """
    __tablename__ = "human_action_queue"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agent_name = Column(String, nullable=False)   # "ApplicationAgent"
    action_type = Column(String, nullable=False)  # "captcha" | "otp" | "2fa" | "payment" | "manual_review" | "recruiter_question"
    title = Column(String, nullable=False)         # "Google OTP Needed"
    description = Column(Text, nullable=True)      # Friendly explanation
    status = Column(String, default="pending")     # "pending" | "completed" | "dismissed" | "expired"
    payload = Column(JSON, default=dict)           # {url, form_data, job_id} — agent resume data
    callback_key = Column(String, unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    expires_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_haq_user_status", "user_id", "status"),)


class AgentMemory(Base):
    """
    Structured per-user memory that persists across all chat sessions.
    The AI reads this at the start of every conversation.
    """
    __tablename__ = "agent_memory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    career_goal = Column(Text, nullable=True)                # "Become ML Engineer at a product company"
    preferred_role = Column(String, nullable=True)           # "Full Stack Developer"
    target_companies = Column(Text, nullable=True)           # JSON list ["Razorpay", "Sarvam"]
    strong_skills = Column(Text, nullable=True)              # JSON list ["Python", "React"]
    weak_skills = Column(Text, nullable=True)                # JSON list ["AWS", "Docker"]
    learning_style = Column(String, nullable=True)           # "visual" | "hands-on" | "reading"
    salary_expectation = Column(String, nullable=True)       # "18–25 LPA"
    location_preference = Column(String, nullable=True)      # "Remote" | "Bangalore" | "Hybrid"
    last_conversation_summary = Column(Text, nullable=True)  # Rolling 500-char summary
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("idx_agent_memory_user", "user_id"),)


class VectorMemoryChunk(Base):
    """
    Long-term semantic memory stored as text chunks.
    When pgvector is enabled, the embedding column stores 768-dim vectors.
    Falls back to full-text search without pgvector.
    """
    __tablename__ = "vector_memory"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chunk_type = Column(String, nullable=False)   # "chat", "resume_change", "job_applied", "course_completed"
    content = Column(Text, nullable=False)         # Original text
    embedding_json = Column(Text, nullable=True)   # JSON-serialized float list (pgvector fallback)
    meta = Column(JSON, default=dict)              # {session_id, timestamp, related_entity_id}
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_vector_memory_user_type", "user_id", "chunk_type"),)


class AgentHealth(Base):
    """
    Tracks real-time health, heartbeats, and runtime statistics for agents.
    """
    __tablename__ = "agent_health"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String, unique=True, index=True, nullable=False)
    last_heartbeat = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="healthy")         # "healthy" | "degraded" | "unhealthy" | "idle"
    avg_runtime = Column(Float, default=0.0)           # running average in seconds
    last_runtime = Column(Float, default=0.0)          # most recent runtime in seconds
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)           # details of the last incident

    @classmethod
    def record_heartbeat(cls, db, agent_name: str, status: str = "healthy", runtime: float = None, is_failure: bool = False, error_msg: str = None):
        import logging
        logger = logging.getLogger("app.models.mcp_models")
        try:
            record = db.query(cls).filter(cls.agent_name == agent_name).first()
            if not record:
                record = cls(agent_name=agent_name)
                db.add(record)
            
            record.last_heartbeat = datetime.utcnow()
            record.status = status
            if is_failure:
                record.failure_count += 1
                record.last_error = error_msg
            else:
                record.success_count += 1
                
            if runtime is not None:
                record.last_runtime = runtime
                total_runs = record.success_count + record.failure_count
                if total_runs > 1:
                    record.avg_runtime = (record.avg_runtime * (total_runs - 1) + runtime) / total_runs
                else:
                    record.avg_runtime = runtime
            db.commit()
        except Exception as e:
            logger.error(f"Failed to record agent health: {e}")
            db.rollback()


class MCPAuditLog(Base):
    """
    Correlation-aware audit logs for every public tool call.
    """
    __tablename__ = "mcp_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, index=True, nullable=True)   # HTTP request correlation ID
    candidate_id = Column(Integer, index=True, nullable=True) # Candidate association
    run_id = Column(Integer, index=True, nullable=True)       # Background run association
    agent = Column(String, index=True, nullable=False)        # e.g., "ResumeMCP"
    tool = Column(String, index=True, nullable=False)         # e.g., "get_ats_score"
    latency = Column(Float, nullable=False)                   # in milliseconds
    status = Column(String, nullable=False)                   # "success" | "failure"
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DeadLetterJob(Base):
    """
    Operational recovery center for failed background agent tasks.
    """
    __tablename__ = "dead_letter_jobs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, nullable=True)
    candidate_id = Column(Integer, nullable=True)
    job_type = Column(String, nullable=False)
    arguments = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    status = Column(String, default="pending")                 # "pending" | "resolved" | "ignored"
    resolved_by = Column(String, nullable=True)                # Admin user identifier
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CircuitBreakerState(Base):
    """
    Persists circuit breaker status centrally across restarts and multiple workers.
    """
    __tablename__ = "circuit_breaker_states"

    id = Column(Integer, primary_key=True, index=True)
    tool_name = Column(String, unique=True, index=True, nullable=False) # e.g. "ResumeMCP"
    state = Column(String, default="CLOSED")                            # "CLOSED" | "OPEN" | "HALF-OPEN"
    failure_count = Column(Integer, default=0)
    last_failure = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)


class BackgroundMonitoringTask(Base):
    """
    Saves candidate tasks that execute periodically in background workers.
    """
    __tablename__ = "background_monitoring_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)              # e.g., "AI Jobs Alert"
    query = Column(String, nullable=False)
    schedule = Column(String, nullable=False)          # Cron expression e.g. "0 9 * * 1"
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    task_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentExecutionHistory(Base):
    """
    Saves a record of every supervisor run, its compiled plan DAG, and execution details.
    """
    __tablename__ = "agent_execution_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(50), nullable=False, index=True)
    plan_dag = Column(JSON, nullable=False)            # The original compiled plan list
    execution_steps = Column(JSON, default=list)       # List of executed tools, parameters, and outputs
    confidence_score = Column(Float, nullable=False)   # Score calculated during planning
    status = Column(String(50), default="pending")     # "completed", "failed", "clarifying", "halted"
    error_log = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

