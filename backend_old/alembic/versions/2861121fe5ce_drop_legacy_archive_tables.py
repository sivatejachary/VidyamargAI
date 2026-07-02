"""drop_legacy_archive_tables

Revision ID: 2861121fe5ce
Revises: d5f303fbe12b
Create Date: 2026-06-23 11:06:41.465091

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2861121fe5ce'
down_revision: Union[str, Sequence[str], None] = 'd5f303fbe12b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    tables_to_drop = [
        "archive.legacy_module_quiz_attempts",
        "archive.legacy_module_quizzes",
        "archive.legacy_module_progress",
        "archive.legacy_topic_quiz_attempts",
        "archive.legacy_topic_quizzes",
        "archive.legacy_topic_progress",
        "archive.legacy_company_profiles",
        "archive.legacy_categories",
        "archive.legacy_job_agent_logs",
        "archive.legacy_workflow_events",
        "archive.legacy_workflow_steps",
        "archive.legacy_workflow_runs"
    ]
    for table in tables_to_drop:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


def downgrade() -> None:
    """Downgrade schema."""
    pass
