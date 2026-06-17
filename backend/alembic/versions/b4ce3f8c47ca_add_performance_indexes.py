"""add_performance_indexes

Revision ID: b4ce3f8c47ca
Revises: 
Create Date: 2026-06-17 08:13:42.852705

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4ce3f8c47ca'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE INDEX IF NOT EXISTS idx_enrollments_user_id ON enrollments(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_progress_user ON user_progress(\"userId\")")
    op.execute("CREATE INDEX IF NOT EXISTS idx_topic_progress_user ON topic_progress(userid)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_module_progress_user ON module_progress(userid)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS idx_enrollments_user_id")
    op.execute("DROP INDEX IF EXISTS idx_user_progress_user")
    op.execute("DROP INDEX IF EXISTS idx_topic_progress_user")
    op.execute("DROP INDEX IF EXISTS idx_module_progress_user")


