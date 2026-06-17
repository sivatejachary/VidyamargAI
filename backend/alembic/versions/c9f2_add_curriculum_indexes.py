"""add_curriculum_indexes

Revision ID: c9f2
Revises: 9af693bf860a
Create Date: 2026-06-17 09:57:00.862090

NOTE: Uses raw psycopg2 in autocommit mode because
      CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c9f2'
down_revision: Union[str, Sequence[str], None] = '9af693bf860a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Must be True — CONCURRENTLY cannot run inside a transaction block
disable_ddl_transaction = True

_INDEXES_UP = [
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_enrollments_course_user ON enrollments(user_id, course_id)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_modules_course_unlock ON modules(courseid, unlockorder)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_topics_module_no ON topics(moduleid, topicno)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_topics_moduleid ON topics(moduleid)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lessons_topicid ON lessons(topicid)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pdfs_topicid ON pdfs(topicid)",
    'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_quizzes_module ON quizzes("moduleId")',
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_written_assessments_module ON written_assessments(moduleid)",
    'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_progress_user_course ON user_progress("userId", "courseId")',
    'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_progress_user_module ON user_progress("userId", "moduleId")',
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_applications_status ON applications(status)",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interviews_status ON interviews(status)",
]

_INDEXES_DOWN = [
    "DROP INDEX CONCURRENTLY IF EXISTS idx_enrollments_course_user",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_modules_course_unlock",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_topics_module_no",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_topics_moduleid",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_lessons_topicid",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_pdfs_topicid",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_quizzes_module",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_written_assessments_module",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_user_progress_user_course",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_user_progress_user_module",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_audit_logs_timestamp",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_applications_status",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_interviews_status",
]


def _run_statements(stmts):
    """Execute statements outside any transaction using raw psycopg2 autocommit."""
    bind = op.get_bind()
    # Get the underlying psycopg2 connection and enable autocommit
    raw_conn = bind.connection.dbapi_connection
    old_isolation = raw_conn.isolation_level
    raw_conn.set_isolation_level(0)  # ISOLATION_LEVEL_AUTOCOMMIT
    try:
        cur = raw_conn.cursor()
        for stmt in stmts:
            print(f"  > {stmt[:80]}...")
            cur.execute(stmt)
        cur.close()
    finally:
        raw_conn.set_isolation_level(old_isolation)


def upgrade() -> None:
    """Create all curriculum performance indexes concurrently."""
    _run_statements(_INDEXES_UP)


def downgrade() -> None:
    """Drop all curriculum performance indexes concurrently."""
    _run_statements(_INDEXES_DOWN)
