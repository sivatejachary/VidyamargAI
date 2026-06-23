"""drop_job_tables

Revision ID: d5f303fbe12b
Revises: b8e37daa1ace
Create Date: 2026-06-23 04:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd5f303fbe12b'
down_revision: Union[str, Sequence[str], None] = 'b8e37daa1ace'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop all job-related tables with CASCADE to clean up constraints automatically
    tables_to_drop = [
        "job_matches",
        "job_pool_matches",
        "saved_jobs",
        "telegram_sources",
        "linkedin_hiring_posts",
        "job_source_tracking",
        "job_sources",
        "jobs_pool",
        "candidate_rankings",
        "offers",
        "interview_results",
        "interviews",
        "fraud_logs",
        "assessment_attempts",
        "assessments",
        "screening_results",
        "applications",
        "jobs",
        "recruiters",
        "companies",
        # Auto apply tables from previous migration
        "application_status_history",
        "application_logs",
        "application_documents",
        "application_cover_letters",
        "application_audits",
        "application_answers",
        "application_tasks",
        "application_metrics",
        "application_runs",
        "application_accounts",
        "platform_health"
    ]
    
    for table in tables_to_drop:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


def downgrade() -> None:
    pass
