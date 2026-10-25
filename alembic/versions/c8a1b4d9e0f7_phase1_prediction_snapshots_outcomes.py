"""phase 1: prediction snapshots and outcomes

Revision ID: c8a1b4d9e0f7
Revises: b7f0a3c8d9e6
Create Date: 2026-10-25 08:30:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c8a1b4d9e0f7'
down_revision: Union[str, None] = 'b7f0a3c8d9e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('prediction_snapshots',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('plan_id', sa.Integer(), nullable=True),
    sa.Column('prediction_timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('trait', sa.JSON(), nullable=True),
    sa.Column('state', sa.JSON(), nullable=True),
    sa.Column('task', sa.JSON(), nullable=True),
    sa.Column('context', sa.JSON(), nullable=True),
    sa.Column('history', sa.JSON(), nullable=True),
    sa.Column('feature_snapshot', sa.JSON(), nullable=True),
    sa.Column('input_hash', sa.String(length=64), nullable=False),
    sa.Column('model_version', sa.String(length=64), nullable=False),
    sa.Column('config_version', sa.String(length=64), nullable=False),
    sa.Column('artifact_hash', sa.String(length=64), nullable=False),
    sa.Column('mode', sa.String(length=16), nullable=False),
    sa.Column('data_origin', sa.String(length=16), server_default='real', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prediction_snapshots_plan_id'), 'prediction_snapshots', ['plan_id'], unique=False)
    op.create_index(op.f('ix_prediction_snapshots_prediction_timestamp'), 'prediction_snapshots', ['prediction_timestamp'], unique=False)
    op.create_index(op.f('ix_prediction_snapshots_task_id'), 'prediction_snapshots', ['task_id'], unique=False)
    op.create_index(op.f('ix_prediction_snapshots_user_id'), 'prediction_snapshots', ['user_id'], unique=False)
    op.create_table('prediction_outcomes',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('snapshot_id', sa.Integer(), nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('completed', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('completion_ratio', sa.Float(), nullable=True),
    sa.Column('actual_duration_minutes', sa.Float(), nullable=True),
    sa.Column('outcome_timestamp', sa.DateTime(timezone=True), nullable=True),
    sa.Column('notes', sa.String(length=500), nullable=True),
    sa.Column('source', sa.String(length=16), server_default='execution', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['snapshot_id'], ['prediction_snapshots.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prediction_outcomes_snapshot_id'), 'prediction_outcomes', ['snapshot_id'], unique=True)
    op.create_index(op.f('ix_prediction_outcomes_task_id'), 'prediction_outcomes', ['task_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_prediction_outcomes_task_id'), table_name='prediction_outcomes')
    op.drop_index(op.f('ix_prediction_outcomes_snapshot_id'), table_name='prediction_outcomes')
    op.drop_table('prediction_outcomes')
    op.drop_index(op.f('ix_prediction_snapshots_user_id'), table_name='prediction_snapshots')
    op.drop_index(op.f('ix_prediction_snapshots_task_id'), table_name='prediction_snapshots')
    op.drop_index(op.f('ix_prediction_snapshots_prediction_timestamp'), table_name='prediction_snapshots')
    op.drop_index(op.f('ix_prediction_snapshots_plan_id'), table_name='prediction_snapshots')
    op.drop_table('prediction_snapshots')
