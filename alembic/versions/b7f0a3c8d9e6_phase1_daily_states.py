"""phase 1: daily_states history table

Revision ID: b7f0a3c8d9e6
Revises: a6e9f2b7c8d5
Create Date: 2026-10-25 08:30:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7f0a3c8d9e6'
down_revision: Union[str, None] = 'a6e9f2b7c8d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('daily_states',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('fatigue', sa.Float(), nullable=False),
    sa.Column('stress', sa.Float(), nullable=False),
    sa.Column('self_efficacy', sa.Float(), nullable=False),
    sa.Column('fatigue_uncertainty', sa.Float(), nullable=False),
    sa.Column('stress_uncertainty', sa.Float(), nullable=False),
    sa.Column('self_efficacy_uncertainty', sa.Float(), nullable=False),
    sa.Column('evidence_availability', sa.String(length=32), server_default='none', nullable=False),
    sa.Column('evidence_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('conflict', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('next_day_prior', sa.JSON(), nullable=True),
    sa.Column('next_day_uncertainty', sa.JSON(), nullable=True),
    sa.Column('cold_start', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('gap_days', sa.Integer(), server_default='0', nullable=False),
    sa.Column('profile_json', sa.JSON(), nullable=True),
    sa.Column('model_version', sa.String(length=64), nullable=False),
    sa.Column('config_version', sa.String(length=64), nullable=False),
    sa.Column('artifact_hash', sa.String(length=64), nullable=False),
    sa.Column('data_origin', sa.String(length=16), server_default='real', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'date', name='uq_daily_states_user_date')
    )
    op.create_index(op.f('ix_daily_states_date'), 'daily_states', ['date'], unique=False)
    op.create_index(op.f('ix_daily_states_user_id'), 'daily_states', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_daily_states_user_id'), table_name='daily_states')
    op.drop_index(op.f('ix_daily_states_date'), table_name='daily_states')
    op.drop_table('daily_states')
