"""persist generation jobs

Revision ID: persist_generation_jobs_20261025
Revises: remove_legacy_mbti_20261025
Create Date: 2026-10-25

Makes async plan-generation jobs durable: status, result, error and the
serialized agent-event history now survive a process restart. The in-process
worker/channel registry still exists for live SSE, but a restart can replay the
persisted terminal state (and orphaned running jobs are failed at startup).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "persist_generation_jobs_20261025"
down_revision: str | None = "remove_legacy_mbti_20261025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generation_jobs",
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index(
        op.f("ix_generation_jobs_user_id"),
        "generation_jobs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generation_jobs_status"),
        "generation_jobs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_generation_jobs_status"), table_name="generation_jobs")
    op.drop_index(op.f("ix_generation_jobs_user_id"), table_name="generation_jobs")
    op.drop_table("generation_jobs")
