"""phase 1: task record-layer fields

Revision ID: b1f4a7c2d9e3
Revises: adde00b2004f
Create Date: 2026-10-25 08:30:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b1f4a7c2d9e3'
down_revision: Union[str, None] = 'persist_generation_jobs_20261025'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('deadline', sa.Date(), nullable=True))
    op.add_column('tasks', sa.Column('earliest_start_date', sa.Date(), nullable=True))
    op.add_column('tasks', sa.Column('difficulty', sa.Integer(), nullable=True))
    op.add_column('tasks', sa.Column('task_type', sa.String(length=64), nullable=True))
    op.add_column('tasks', sa.Column('value_score', sa.Integer(), nullable=True))
    op.add_column('tasks', sa.Column('completion_criterion', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'completion_criterion')
    op.drop_column('tasks', 'value_score')
    op.drop_column('tasks', 'task_type')
    op.drop_column('tasks', 'difficulty')
    op.drop_column('tasks', 'earliest_start_date')
    op.drop_column('tasks', 'deadline')
