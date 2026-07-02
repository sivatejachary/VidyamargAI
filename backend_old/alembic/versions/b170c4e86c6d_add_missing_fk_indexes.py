"""add_missing_fk_indexes

Revision ID: b170c4e86c6d
Revises: 2861121fe5ce
Create Date: 2026-06-23 11:56:40.978798

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b170c4e86c6d'
down_revision: Union[str, Sequence[str], None] = '2861121fe5ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_legacy_email_notifications_candidate_id ON archive.legacy_email_notifications(candidate_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_legacy_messages_candidate_id ON archive.legacy_messages(candidate_id)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS idx_notifications_user_id")
    op.execute("DROP INDEX IF EXISTS archive.idx_legacy_email_notifications_candidate_id")
    op.execute("DROP INDEX IF EXISTS archive.idx_legacy_messages_candidate_id")
