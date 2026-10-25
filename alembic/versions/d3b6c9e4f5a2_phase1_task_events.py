"""phase 1: task_events table

Revision ID: d3b6c9e4f5a2
Revises: c2a5b8d3e4f1
Create Date: 2026-10-25 08:30:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd3b6c9e4f5a2'
down_revision: Union[str, None] = 'c2a5b8d3e4f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('task_events',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('event_type', sa.String(length=32), nullable=False),
    sa.Column('before', sa.JSON(), nullable=True),
    sa.Column('after', sa.JSON(), nullable=True),
    sa.Column('reason', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_events_created_at'), 'task_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_task_events_task_id'), 'task_events', ['task_id'], unique=False)
    op.create_index(op.f('ix_task_events_user_id'), 'task_events', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_task_events_user_id'), table_name='task_events')
    op.drop_index(op.f('ix_task_events_task_id'), table_name='task_events')
    op.drop_index(op.f('ix_task_events_created_at'), table_name='task_events')
    op.drop_table('task_events')
