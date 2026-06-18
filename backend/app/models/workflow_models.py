"""
VidyaMarg AI OS — Workflow Models
Database tables for durable workflow tracking and step-level recovery.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class WorkflowRun(Base):
    """
    Durable workflow run execution instance.
    Stores the active context and overall state.
    """
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workflow_type = Column(String(100), nullable=False)  # "job_discovery", "auto_apply", etc.
    status = Column(String(50), default="pending")        # "pending", "running", "completed", "failed"
    context = Column(JSON, default=dict)                  # Variables shared between steps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    steps = relationship("WorkflowStep", back_populates="run", cascade="all, delete-orphan")
    events = relationship("WorkflowEvent", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_wfr_user_status", "user_id", "status"),
    )


class WorkflowStep(Base):
    """
    Step within a workflow run. Used for checkpointing/recovery.
    """
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    step_name = Column(String(255), nullable=False)
    status = Column(String(50), default="pending")        # "pending", "running", "completed", "failed"
    result = Column(JSON, nullable=True)                  # Output data from this step
    error = Column(Text, nullable=True)                   # Error message on failure
    attempts = Column(Integer, default=0)                 # Retry count
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    run = relationship("WorkflowRun", back_populates="steps")

    __table_args__ = (
        Index("idx_wfs_run_name", "run_id", "step_name"),
    )


class WorkflowEvent(Base):
    """
    Event log generated during a workflow run.
    """
    __tablename__ = "workflow_events"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("WorkflowRun", back_populates="events")

    __table_args__ = (
        Index("idx_wfe_run_created", "run_id", "created_at"),
    )
