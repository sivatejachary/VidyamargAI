"""add_curriculum_indexes

Revision ID: c9f2
Revises: 9af693bf860a
Create Date: 2026-06-17 09:57:00.862090

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9f2'
down_revision: Union[str, Sequence[str], None] = '9af693bf860a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Disable transaction block for concurrent index creation
disable_ddl_transaction = True


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_enrollments_course_user ON enrollments(user_id, course_id)")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_modules_course_unlock ON modules(courseid, unlockorder)")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_topics_module_no ON topics(moduleid, topicno)")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_topics_moduleid ON topics(moduleid)")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lessons_topicid ON lessons(topicid)")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pdfs_topicid ON pdfs(topicid)")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_quizzes_module ON quizzes(\"moduleId\")")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_written_assessments_module ON written_assessments(moduleid)")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_progress_user_course ON user_progress(\"userId\", \"courseId\")")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_progress_user_module ON user_progress(\"userId\", \"moduleId\")")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC)")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_applications_status ON applications(status)")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interviews_status ON interviews(status)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_enrollments_course_user")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_modules_course_unlock")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_topics_module_no")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_topics_moduleid")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_lessons_topicid")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_pdfs_topicid")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_quizzes_module")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_written_assessments_module")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_user_progress_user_course")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_user_progress_user_module")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_audit_logs_timestamp")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_applications_status")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_interviews_status")
