"""
VidyaMarg AI OS Models Package
Import all models here to register them with SQLAlchemy Base metadata.
"""
from app.core.database import Base
from app.models.models import *
from app.models.mcp_models import *
from app.models.pool_models import *
from app.models.workflow_models import *
from app.models.session_models import *
from app.models.memory_models import *

# Dynamically route legacy tables to archive schema to prevent public schema recreation
legacy_table_names = {
    # Phase 2 deleted tables
    "ai_interviews", "ai_interview_attempts", "final_ai_interviews", "final_ai_interview_attempts",
    "interviews", "interview_results", "assessments", "assessment_attempts",
    "written_assessments", "written_assessment_attempts", "final_assessments",
    "final_assessment_attempts", "screening_results", "agent_activities",
    "agent_memory", "vector_memory", "workflow_runs", "workflow_steps",
    "workflow_events", "browser_sessions", "browser_cookies", "application_history",
    "video_analytics", "readiness_scores", "career_health_snapshots",
    "mcp_chat_messages", "mcp_chat_sessions", "mcp_audit_logs",
    "search_history", "cleanup_audit_backup", "circuit_breaker_states",
    # Phase 3 archived tables (job feature removal)
    "jobs", "applications", "companies", "recruiters",
    "linkedin_hiring_posts", "job_sources", "job_matches",
    "saved_jobs", "telegram_sources", "job_source_tracking",
    "jobs_pool", "job_pool_matches", "recommendation_memories",
    "offers", "candidate_rankings", "fraud_logs",
    # Previously archived
    "agent_health", "ai_mentor_artifacts", "ai_mentor_insights", "ai_mentor_messages",
    "ai_mentor_sessions", "ai_mentor_study_plans", "ai_mentor_usage", "candidate_preferences",
    "categories", "company_intelligence_cache", "company_profiles",
    "course_analytics", "email_notifications",  "job_agent_logs",
    "job_pool_matches", "job_source_tracking", "learning_events", "linkedin_hiring_posts",
    "messages", "module_progress", "module_quiz_attempts", "module_quizzes",
    "topic_progress", "topic_quiz_attempts", "topic_quizzes", "user_career_profiles"
}

for table_key in list(Base.metadata.tables.keys()):
    table_obj = Base.metadata.tables[table_key]
    name_to_check = table_obj.name
    if name_to_check.startswith("legacy_"):
        base_name = name_to_check[7:]
    else:
        base_name = name_to_check

    if base_name in legacy_table_names or name_to_check in legacy_table_names:
        table_obj.schema = "archive"
        if not table_obj.name.startswith("legacy_"):
            table_obj.name = f"legacy_{table_obj.name}"

# Register before_create event listener to create schema for Postgres and bypass for SQLite
from sqlalchemy import event, text

@event.listens_for(Base.metadata, "before_create")
def before_create_tables(target, connection, **kw):
    is_sqlite = connection.dialect.name == "sqlite"
    if is_sqlite:
        for table in target.tables.values():
            table.schema = None
    else:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS archive;"))
