"""add_updated_at_to_courses

Revision ID: 9af693bf860a
Revises: b4ce3f8c47ca
Create Date: 2026-06-17 08:21:24.773195

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9af693bf860a'
down_revision: Union[str, Sequence[str], None] = 'b4ce3f8c47ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE courses ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE courses DROP COLUMN IF EXISTS updated_at")

