"""phase 1: evidence_items table

Revision ID: a6e9f2b7c8d5
Revises: f5d8e1a6b7c4
Create Date: 2026-10-25 08:30:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a6e9f2b7c8d5'
down_revision: Union[str, None] = 'f5d8e1a6b7c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('evidence_items',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('feedback_id', sa.Integer(), nullable=True),
    sa.Column('task_id', sa.Integer(), nullable=True),
    sa.Column('reflection_field', sa.String(length=32), nullable=False),
    sa.Column('evidence_type', sa.String(length=32), nullable=False),
    sa.Column('direction', sa.String(length=16), nullable=False),
    sa.Column('strength', sa.String(length=16), nullable=False),
    sa.Column('period', sa.String(length=16), nullable=False),
    sa.Column('cause_category', sa.String(length=32), nullable=True),
    sa.Column('voluntary', sa.Boolean(), nullable=True),
    sa.Column('evidence_text', sa.String(length=500), nullable=False),
    sa.Column('extractor', sa.String(length=64), nullable=False),
    sa.Column('extractor_version', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['feedback_id'], ['feedbacks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidence_items_feedback_id'), 'evidence_items', ['feedback_id'], unique=False)
    op.create_index(op.f('ix_evidence_items_task_id'), 'evidence_items', ['task_id'], unique=False)
    op.create_index(op.f('ix_evidence_items_user_id'), 'evidence_items', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_evidence_items_user_id'), table_name='evidence_items')
    op.drop_index(op.f('ix_evidence_items_task_id'), table_name='evidence_items')
    op.drop_index(op.f('ix_evidence_items_feedback_id'), table_name='evidence_items')
    op.drop_table('evidence_items')
