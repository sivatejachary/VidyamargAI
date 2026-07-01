"""add_monitoring_and_history_tables

Revision ID: 4dba31fca1f5
Revises: 8e4cd1f45df3
Create Date: 2026-07-01 21:26:17.489356

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4dba31fca1f5'
down_revision: Union[str, Sequence[str], None] = '8e4cd1f45df3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('agent_execution_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.String(length=50), nullable=False),
    sa.Column('plan_dag', sa.JSON(), nullable=False),
    sa.Column('execution_steps', sa.JSON(), nullable=True),
    sa.Column('confidence_score', sa.Float(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('error_log', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_execution_history_id'), 'agent_execution_history', ['id'], unique=False)
    op.create_index(op.f('ix_agent_execution_history_session_id'), 'agent_execution_history', ['session_id'], unique=False)
    
    op.create_table('background_monitoring_tasks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('query', sa.String(), nullable=False),
    sa.Column('schedule', sa.String(), nullable=False),
    sa.Column('last_run_at', sa.DateTime(), nullable=True),
    sa.Column('next_run_at', sa.DateTime(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('task_metadata', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_background_monitoring_tasks_id'), 'background_monitoring_tasks', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_background_monitoring_tasks_id'), table_name='background_monitoring_tasks')
    op.drop_table('background_monitoring_tasks')
    op.drop_index(op.f('ix_agent_execution_history_session_id'), table_name='agent_execution_history')
    op.drop_index(op.f('ix_agent_execution_history_id'), table_name='agent_execution_history')
    op.drop_table('agent_execution_history')
