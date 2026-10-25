"""persist generation jobs - externally applied revision (reconstructed)

Revision ID: persist_generation_jobs_20261025
Revises: adde00b2004f
Create Date: 2026-10-25 09:00:00.000000+00:00

This revision was applied to the shared PostgreSQL database by another
workspace; its migration file was not present in this checkout. It is
reconstructed from the live DDL so the local Alembic chain can resolve the
database head. On the already-stamped database this upgrade never runs; on a
fresh database it creates the same generation_jobs table.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'persist_generation_jobs_20261025'
down_revision: Union[str, None] = 'adde00b2004f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('generation_jobs',
    sa.Column('job_id', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('plan_id', sa.Integer(), nullable=True),
    sa.Column('result', sa.JSON(), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('events', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('job_id', name='generation_jobs_pkey'),
    )
    op.create_index(op.f('ix_generation_jobs_status'), 'generation_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_generation_jobs_user_id'), 'generation_jobs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_generation_jobs_user_id'), table_name='generation_jobs')
    op.drop_index(op.f('ix_generation_jobs_status'), table_name='generation_jobs')
    op.drop_table('generation_jobs')
