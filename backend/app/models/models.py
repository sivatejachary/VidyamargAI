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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
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
    
    status = Column(String, default="Registered") # Registered, Complete, Applied, Offer, etc.
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
    applications = relationship("Application", back_populates="candidate")

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    resume_text = Column(Text, nullable=True)
    parsed_metadata = Column(Text, nullable=True) # JSON details
    created_at = Column(DateTime, default=datetime.utcnow)
    
    candidate = relationship("Candidate", back_populates="profiles")

class CandidateResume(Base):
    __tablename__ = "candidate_resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    resume_url = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    candidate = relationship("Candidate", back_populates="resumes")
    applications = relationship("Application", back_populates="resume")

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    required_skills = Column(String, nullable=False) # Comma separated
    experience_level = Column(String, nullable=False)
    salary_range = Column(String, nullable=True)
    location = Column(String, nullable=False)
    department = Column(String, nullable=False)
    status = Column(String, default="active")  # active, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    recruiter_id = Column(Integer, ForeignKey("recruiters.id"), nullable=True)
    
    applications = relationship("Application", back_populates="job")
    assessments = relationship("Assessment", back_populates="job")
    company = relationship("Company", back_populates="jobs")
    recruiter = relationship("Recruiter", back_populates="jobs")
    sources = relationship("JobSource", back_populates="job")
    matches = relationship("JobMatch", back_populates="job")
    saved_by = relationship("SavedJob", back_populates="job")

    @property
    def company_logo(self):
        return self.company.logo_url if self.company else None

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("candidate_resumes.id"), nullable=True)
    status = Column(String, default="applied") # applied, screening, assessment, interview, ranking, recommendation, offer, onboarding, hired, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    resume = relationship("CandidateResume", back_populates="applications")
    
    screening_results = relationship("ScreeningResult", back_populates="application")
    assessment_attempts = relationship("AssessmentAttempt", back_populates="application")
    interviews = relationship("Interview", back_populates="application")
    rankings = relationship("CandidateRanking", back_populates="application")
    offers = relationship("Offer", back_populates="application")

class ScreeningResult(Base):
    __tablename__ = "screening_results"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    skill_match = Column(Float, default=0.0)
    experience_match = Column(Float, default=0.0)
    education_match = Column(Float, default=0.0)
    project_match = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    decision = Column(String, nullable=False) # shortlist, reject
    raw_reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    application = relationship("Application", back_populates="screening_results")

class Assessment(Base):
    __tablename__ = "assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    title = Column(String, nullable=False)
    mcqs = Column(Text, nullable=False) # JSON String
    coding_challenges = Column(Text, nullable=False) # JSON String
    english_test = Column(Text, nullable=False) # JSON String
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="assessments")
    attempts = relationship("AssessmentAttempt", back_populates="assessment")

class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    status = Column(String, default="started") # started, completed
    answers = Column(Text, nullable=True) # JSON String
    score = Column(Float, default=0.0)
    passed = Column(Boolean, default=False)
    proctoring_violations = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    application = relationship("Application", back_populates="assessment_attempts")
    assessment = relationship("Assessment", back_populates="attempts")
    fraud_logs = relationship("FraudLog", back_populates="attempt")

class FraudLog(Base):
    __tablename__ = "fraud_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("assessment_attempts.id"), nullable=False)
    event_type = Column(String, nullable=False) # tab_switch, face_missing, multiple_faces, eye_away, copy_paste
    screenshot_url = Column(String, nullable=True)
    fraud_score = Column(Float, default=0.0)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    attempt = relationship("AssessmentAttempt", back_populates="fraud_logs")

class Interview(Base):
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    scheduled_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="scheduled") # scheduled, active, completed
    recording_url = Column(String, nullable=True)
    transcript = Column(Text, nullable=True) # JSON String list of dialogue
    questions = Column(Text, nullable=True) # JSON String list of generated questions
    current_question_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    application = relationship("Application", back_populates="interviews")
    results = relationship("InterviewResult", back_populates="interview")

class InterviewResult(Base):
    __tablename__ = "interview_results"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    technical_score = Column(Float, default=0.0)
    communication_score = Column(Float, default=0.0)
    confidence_score = Column(Float, default=0.0)
    thinking_score = Column(Float, default=0.0)
    problem_solving_score = Column(Float, default=0.0)
    fraud_score = Column(Float, default=0.0)
    final_score = Column(Float, default=0.0)
    report_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    interview = relationship("Interview", back_populates="results")

class CandidateRanking(Base):
    __tablename__ = "candidate_rankings"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    resume_score = Column(Float, default=0.0)
    assessment_score = Column(Float, default=0.0)
    interview_score = Column(Float, default=0.0)
    fraud_penalty = Column(Float, default=0.0)
    final_score = Column(Float, default=0.0)
    rank = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    application = relationship("Application", back_populates="rankings")

class Offer(Base):
    __tablename__ = "offers"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    offer_url = Column(String, nullable=True)
    salary_offered = Column(Float, nullable=False)
    status = Column(String, default="pending") # pending, accepted, rejected
    sent_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)
    
    application = relationship("Application", back_populates="offers")

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
    chat_id = Column(String, nullable=False) # recruiter_sophia, hiring_team, mentor_srinivasan, team_alpha, support
    sender = Column(String, nullable=False) # user, recruiter, mentor, other, support
    sender_name = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)
    
    candidate = relationship("Candidate")


class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    logo_url = Column(String, nullable=True)
    website = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    jobs = relationship("Job", back_populates="company")
    recruiters = relationship("Recruiter", back_populates="company")


class Recruiter(Base):
    __tablename__ = "recruiters"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    profile_url = Column(String, nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="recruiters")
    jobs = relationship("Job", back_populates="recruiter")
    linkedin_posts = relationship("LinkedInHiringPost", back_populates="recruiter")


class LinkedInHiringPost(Base):
    __tablename__ = "linkedin_hiring_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    post_url = Column(String, unique=True, index=True, nullable=False)
    posted_date = Column(DateTime, default=datetime.utcnow)
    raw_text = Column(Text, nullable=False)
    extracted_title = Column(String, nullable=True)
    extracted_company = Column(String, nullable=True)
    extracted_location = Column(String, nullable=True)
    extracted_skills = Column(String, nullable=True)
    extracted_experience = Column(String, nullable=True)
    extracted_salary = Column(String, nullable=True)
    extracted_contact_email = Column(String, nullable=True)
    extracted_apply_link = Column(String, nullable=True)
    recruiter_id = Column(Integer, ForeignKey("recruiters.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    recruiter = relationship("Recruiter", back_populates="linkedin_posts")


class JobSource(Base):
    __tablename__ = "job_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    source_platform = Column(String, nullable=False) # e.g. LinkedIn, Indeed, Naukri, Swiggy Careers
    source_url = Column(String, nullable=False)
    posted_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    job = relationship("Job", back_populates="sources")


class JobMatch(Base):
    __tablename__ = "job_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    skill_match = Column(Float, default=0.0)
    experience_match = Column(Float, default=0.0)
    education_match = Column(Float, default=0.0)
    project_match = Column(Float, default=0.0)
    certification_match = Column(Float, default=0.0)
    location_match = Column(Float, default=0.0)
    match_score = Column(Float, default=0.0)
    skills_gap = Column(Text, nullable=True) # comma separated skills missing
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    job = relationship("Job", back_populates="matches")
    candidate = relationship("Candidate")


class SearchHistory(Base):
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    query = Column(String, nullable=False)
    searched_at = Column(DateTime, default=datetime.utcnow)
    
    candidate = relationship("Candidate")


class SavedJob(Base):
    __tablename__ = "saved_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    saved_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="saved_by")
    candidate = relationship("Candidate")


class JobAgentRun(Base):
    __tablename__ = "job_agent_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    status = Column(String, default="running")  # running, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    candidate = relationship("Candidate")
    logs = relationship("JobAgentLog", back_populates="run", cascade="all, delete-orphan")


class JobAgentLog(Base):
    __tablename__ = "job_agent_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("job_agent_runs.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    status = Column(String, default="info")  # info, success, warning, error
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    run = relationship("JobAgentRun", back_populates="logs")


class TelegramSource(Base):
    __tablename__ = "telegram_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_name = Column(String, unique=True, index=True, nullable=False)
    active = Column(Boolean, default=True)
    last_checked = Column(DateTime, nullable=True)


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
        # Compound index for efficient per-user curriculum progress lookups
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
    consent_type = Column(String, nullable=False)  # "account_access", "app_submission", "resume_upload", "data_storage"
    granted = Column(Boolean, default=False, nullable=False)
    granted_at = Column(DateTime, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    consent_ref = Column(String, nullable=False, default=lambda: str(uuid.uuid4()))
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







