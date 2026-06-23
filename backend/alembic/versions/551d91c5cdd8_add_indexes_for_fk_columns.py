"""add_indexes_for_fk_columns

Revision ID: 551d91c5cdd8
Revises: b170c4e86c6d
Create Date: 2026-06-23 12:43:07.881783

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '551d91c5cdd8'
down_revision: Union[str, Sequence[str], None] = 'b170c4e86c6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE INDEX IF NOT EXISTS idx_legacy_application_history_resume_id ON archive.legacy_application_history(resume_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_legacy_video_analytics_user_id ON archive.legacy_video_analytics(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_candidate_embeddings_resume_id ON candidate_embeddings(resume_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_enrollments_course_id ON enrollments(course_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_project_submissions_project_id ON project_submissions(project_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_projects_courseid ON projects(courseid)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS archive.idx_legacy_application_history_resume_id")
    op.execute("DROP INDEX IF EXISTS archive.idx_legacy_video_analytics_user_id")
    op.execute("DROP INDEX IF EXISTS idx_audit_logs_user_id")
    op.execute("DROP INDEX IF EXISTS idx_candidate_embeddings_resume_id")
    op.execute("DROP INDEX IF EXISTS idx_enrollments_course_id")
    op.execute("DROP INDEX IF EXISTS idx_project_submissions_project_id")
    op.execute("DROP INDEX IF EXISTS idx_projects_courseid")
