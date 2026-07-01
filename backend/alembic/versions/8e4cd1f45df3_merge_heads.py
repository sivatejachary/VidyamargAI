"""merge heads

Revision ID: 8e4cd1f45df3
Revises: 551d91c5cdd8, a1b2c3d4e5f6
Create Date: 2026-07-01 21:17:09.028935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e4cd1f45df3'
down_revision: Union[str, Sequence[str], None] = ('551d91c5cdd8', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
