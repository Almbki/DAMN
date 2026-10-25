"""phase 1: task_dependencies table

Revision ID: c2a5b8d3e4f1
Revises: b1f4a7c2d9e3
Create Date: 2026-10-25 08:30:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c2a5b8d3e4f1'
down_revision: Union[str, None] = 'b1f4a7c2d9e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('task_dependencies',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('depends_on_task_id', sa.Integer(), nullable=False),
    sa.Column('dependency_type', sa.String(length=16), server_default='hard', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['depends_on_task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('task_id', 'depends_on_task_id', name='uq_task_dependencies_pair')
    )
    op.create_index(op.f('ix_task_dependencies_depends_on_task_id'), 'task_dependencies', ['depends_on_task_id'], unique=False)
    op.create_index(op.f('ix_task_dependencies_task_id'), 'task_dependencies', ['task_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_task_dependencies_task_id'), table_name='task_dependencies')
    op.drop_index(op.f('ix_task_dependencies_depends_on_task_id'), table_name='task_dependencies')
    op.drop_table('task_dependencies')
