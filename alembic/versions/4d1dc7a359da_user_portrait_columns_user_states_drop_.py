"""user portrait columns, user_states, drop user_models

Revision ID: 4d1dc7a359da
Revises: d696086158be
Create Date: 2026-09-22 10:23:02.800255+00:00

MANUALLY REVIEWED / ADJUSTED
----------------------------
``alembic revision --autogenerate`` also emitted drops for
``checkpoints`` / ``checkpoint_blobs`` / ``checkpoint_writes`` /
``checkpoint_migrations``. Those tables belong to **LangGraph**
(created by ``PostgresSaver.setup()`` in ``app/agent/checkpointer.py``) and are
not part of ``Base.metadata``, so autogenerate wrongly treats them as removed.
Dropping them would break the preview/confirm flow, so every reference to them
was removed from both ``upgrade()`` and ``downgrade()``.

Business change:
* add ``users.mbti_type`` / ``mbti_dims`` / ``identity`` (static portrait)
* create ``user_states`` (adaptive portrait state, one row per user)
* drop ``user_models`` (retired: the portrait state replaces it)
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4d1dc7a359da"
down_revision: str | None = "d696086158be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("duration_factor", sa.Float(), nullable=False),
        sa.Column("completion_prob", sa.Float(), nullable=False),
        sa.Column("stress_baseline", sa.Float(), nullable=False),
        sa.Column("energy_drain_rate", sa.Float(), nullable=False),
        sa.Column("proactive_score", sa.Float(), nullable=False),
        sa.Column("procrastination_tendency", sa.Float(), nullable=False),
        sa.Column("preferred_time_slots", sa.JSON(), nullable=False),
        sa.Column("stress_response", sa.Float(), nullable=False),
        sa.Column("state_energy", sa.Float(), nullable=False),
        sa.Column("state_fatigue", sa.Float(), nullable=False),
        sa.Column("self_efficacy", sa.Float(), nullable=False),
        sa.Column("update_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_states_user_id"), "user_states", ["user_id"], unique=True)

    op.add_column("users", sa.Column("mbti_type", sa.String(length=4), nullable=True))
    op.add_column("users", sa.Column("mbti_dims", sa.JSON(), nullable=True))
    op.add_column("users", sa.Column("identity", sa.String(length=200), nullable=True))

    # Retired: the portrait state (user_states) is the single behavioural model.
    op.drop_table("user_models")


def downgrade() -> None:
    op.create_table(
        "user_models",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("model_version", sa.VARCHAR(length=64), autoincrement=False, nullable=False),
        sa.Column("duration_factors", postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False),
        sa.Column("completion_probability", postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False),
        sa.Column("stress_response", postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False),
        sa.Column("preferred_time_slots", postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False),
        sa.Column("sample_size", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("user_models_user_id_fkey")),
        sa.PrimaryKeyConstraint("id", name=op.f("user_models_pkey")),
        sa.UniqueConstraint("user_id", name=op.f("user_models_user_id_key")),
    )

    op.drop_column("users", "identity")
    op.drop_column("users", "mbti_dims")
    op.drop_column("users", "mbti_type")

    op.drop_index(op.f("ix_user_states_user_id"), table_name="user_states")
    op.drop_table("user_states")
