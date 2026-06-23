import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, Index, JSON, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="candidate")  # candidate, admin, super_admin
    user_xp = Column(Integer, default=0)
    user_badges = Column(Text, default='[]')
    user_streaks = Column(Integer, default=0)
    last_active_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    candidate = relationship("Candidate", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Candidate(Base):
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    
    # JSON or serialized text fields
    education = Column(Text, nullable=True)  # JSON String of degrees
    experience = Column(Text, nullable=True) # JSON String of jobs
    skills = Column(Text, nullable=True)     # Comma separated
    projects = Column(Text, nullable=True)   # JSON String
    certifications = Column(Text, nullable=True) # Comma separated
    
    # Extended resume fields
    summary = Column(Text, nullable=True)          # Professional summary
    achievements = Column(Text, nullable=True)     # JSON String array
    languages = Column(Text, nullable=True)        # Comma separated
    
    # Social links
    linkedin = Column(String, nullable=True)
    github = Column(String, nullable=True)
    portfolio = Column(String, nullable=True)
    
    # Resume ingestion tracking
    resume_status = Column(String, default="pending")
    resume_progress = Column(Integer, default=0)
    resume_step = Column(String(100), nullable=True)
    resume_last_processed_at = Column(DateTime, nullable=True)
    resume_processing_error = Column(Text, nullable=True)
    
    status = Column(String, default="Registered")
    current_step = Column(String, default="Profile")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Hackathon Assignment Details
    hackathon_team = Column(String, nullable=True)
    assigned_mentor = Column(String, nullable=True)
    hackathon_problem = Column(String, nullable=True)
    hackathon_members = Column(Text, nullable=True)
    
    parsed_name = Column(String, nullable=True)
    parsed_email = Column(String, nullable=True)
    
    user = relationship("User", back_populates="candidate")
    profiles = relationship("CandidateProfile", back_populates="candidate")
    resumes = relationship("CandidateResume", back_populates="candidate")

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    resume_id = Column(Integer, ForeignKey("candidate_resumes.id", ondelete="CASCADE"), nullable=True)
    resume_hash = Column(String(64), nullable=True)
    role_version = Column(String(10), default="v1")
    industry = Column(String(100), nullable=True)
    specialization = Column(String(100), nullable=True)
    experience_years = Column(Float, nullable=True)
    current_role = Column(String(100), nullable=True)
    generated_roles = Column(Text, nullable=True)  # JSON string
    search_strategy = Column(Text, nullable=True)  # JSON string
    skills_graph = Column(Text, nullable=True)  # JSON string
    resume_text = Column(Text, nullable=True)
    parsed_metadata = Column(Text, nullable=True) # JSON details
    created_at = Column(DateTime, default=datetime.utcnow)
    
    candidate = relationship("Candidate", back_populates="profiles")

class CandidateResume(Base):
    __tablename__ = "candidate_resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    resume_url = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    resume_type = Column(String(20), default="general")  # general | swe | ai | ds | ml
    is_active = Column(Boolean, default=False)
    
    candidate = relationship("Candidate", back_populates="resumes")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    type = Column(String, default="info") # info, alert, system
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="notifications")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="audit_logs")

class EmailNotification(Base):
    __tablename__ = "email_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    sender = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)
    
    candidate = relationship("Candidate")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    chat_id = Column(String, nullable=False)
    sender = Column(String, nullable=False)
    sender_name = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)
    
    candidate = relationship("Candidate")


class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    theme = Column(String, default="light")  # light, dark, system
    
    user = relationship("User", back_populates="preferences")


class CourseProgress(Base):
    __tablename__ = "course_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(String, nullable=False, index=True)
    video_progress = Column(Float, default=0.0)
    pdf_progress = Column(Float, default=0.0)
    quiz_progress = Column(Float, default=0.0)
    overall_progress = Column(Float, default=0.0)
    last_lesson_id = Column(String, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_course_progress_user_course", "user_id", "course_id"),
        UniqueConstraint("user_id", "course_id", name="uq_course_progress_user_course"),
    )


class LearningEvent(Base):
    __tablename__ = "learning_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    lesson_id = Column(String, nullable=True, index=True)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class VideoAnalytics(Base):
    __tablename__ = "video_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    lesson_id = Column(String, nullable=False)
    load_time = Column(Float, default=0.0)
    buffer_count = Column(Integer, default=0)
    buffer_duration = Column(Float, default=0.0)
    playback_failures = Column(Integer, default=0)
    device = Column(String, nullable=True)
    browser = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CourseAnalytics(Base):
    __tablename__ = "course_analytics"
    
    course_id = Column(String, primary_key=True, index=True)
    completion_rate = Column(Float, default=0.0)
    avg_watch_time = Column(Float, default=0.0)
    dropoff_point = Column(String, nullable=True)
    avg_quiz_score = Column(Float, default=0.0)
    certificate_rate = Column(Float, default=0.0)

class OTP(Base):
    __tablename__ = "otps"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp = Column(String, nullable=False)
    expiry_time = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AIMentorSession(Base):
    __tablename__ = "ai_mentor_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    metadata_json = Column(JSON, default=dict)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    is_archived = Column(Boolean, default=False)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Index("idx_ai_mentor_session_user", AIMentorSession.user_id)


class AIMentorMessage(Base):
    __tablename__ = "ai_mentor_messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("ai_mentor_sessions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String, nullable=False)  # "user" or "ai"
    message = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict)
    is_archived = Column(Boolean, default=False)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Index("idx_ai_mentor_message_session", AIMentorMessage.session_id)
Index("idx_ai_mentor_message_user", AIMentorMessage.user_id)


class AIMentorStudyPlan(Base):
    __tablename__ = "ai_mentor_study_plans"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    duration = Column(String, nullable=False)  # "7-day", "30-day", "90-day"
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

Index("idx_ai_mentor_studyplan_user", AIMentorStudyPlan.user_id)


class AIMentorInsight(Base):
    __tablename__ = "ai_mentor_insights"
    __table_args__ = (
        CheckConstraint("insight_type IN ('achievement','warning','recommendation')", name="chk_insight_type"),
    )
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    insight_type = Column(String, nullable=False)  # "achievement", "warning", "recommendation"
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

Index("idx_ai_mentor_insight_user", AIMentorInsight.user_id)


class AIMentorArtifact(Base):
    __tablename__ = "ai_mentor_artifacts"
    __table_args__ = (
        CheckConstraint("version > 0", name="chk_artifact_version"),
        CheckConstraint("artifact_type IN ('quiz','notes','challenge','questions')", name="chk_artifact_type"),
    )
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    artifact_type = Column(String, nullable=False)  # "quiz", "notes", "challenge", "questions"
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    metadata_json = Column(JSON, default=dict)
    is_archived = Column(Boolean, default=False)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Index("idx_ai_mentor_artifact_user", AIMentorArtifact.user_id)


class AIMentorUsage(Base):
    __tablename__ = "ai_mentor_usage"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String, nullable=False)
    prompt_chars = Column(Integer, default=0)
    completion_chars = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

Index("idx_ai_mentor_usage_user", AIMentorUsage.user_id)


class UserCareerProfile(Base):
    __tablename__ = "user_career_profiles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    career_goal = Column(String, default="Frontend Engineer")
    target_role = Column(String, default="Frontend Developer")
    target_level = Column(String, default="Mid-Level")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Index("idx_user_career_profile_user", UserCareerProfile.user_id)


class UserConsent(Base):
    __tablename__ = "user_consents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    consent_type = Column(String, nullable=False)
    granted = Column(Boolean, default=False, nullable=False)
    granted_at = Column(DateTime, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    consent_ref = Column(String, nullable=False, default=lambda: str(uuid.uuid4()))
    revoked_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Index("idx_user_consent_user_type", UserConsent.user_id, UserConsent.consent_type)


class MCPChatSession(Base):
    __tablename__ = "mcp_chat_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    mode = Column(String, default="general")
    is_pinned = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("MCPChatMessage", back_populates="session", cascade="all, delete-orphan")


class MCPChatMessage(Base):
    __tablename__ = "mcp_chat_messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("mcp_chat_sessions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String, nullable=False)  # "user" or "tush"
    text = Column(Text, nullable=False)
    actions = Column(JSON, default=list)
    action_cards = Column(JSON, default=list)
    memory_updated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("MCPChatSession", back_populates="messages")


Index("idx_mcp_chat_session_user", MCPChatSession.user_id)
Index("idx_mcp_chat_message_session", MCPChatMessage.session_id)
Index("idx_mcp_chat_message_user", MCPChatMessage.user_id)


class UserRefreshToken(Base):
    __tablename__ = "user_refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CandidateEmbedding(Base):
    __tablename__ = "candidate_embeddings"
    
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True)
    resume_id = Column(Integer, ForeignKey("candidate_resumes.id", ondelete="CASCADE"), nullable=True)
    embedding_model = Column(String(100), nullable=False)
    embedding_vector = Column(Text, nullable=False)  # JSON-serialized floats
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
