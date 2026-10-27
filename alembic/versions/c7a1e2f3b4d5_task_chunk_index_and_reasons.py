"""task chunk index and final scheduling reasons

Revision ID: c7a1e2f3b4d5
Revises: 9b2f4c7d1a3e
Create Date: 2026-10-26 00:00:00.000000+00:00

Additive only: execution chunk order + final deterministic scheduling reason.
Existing rows remain valid (all columns nullable).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c7a1e2f3b4d5"
down_revision: Union[str, None] = "9b2f4c7d1a3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("chunk_index", sa.Integer(), nullable=True))
    op.add_column(
        "tasks", sa.Column("scheduling_reason", sa.String(length=32), nullable=True)
    )
    op.add_column(
        "tasks", sa.Column("scheduling_detail", sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("tasks", "scheduling_detail")
    op.drop_column("tasks", "scheduling_reason")
    op.drop_column("tasks", "chunk_index")
