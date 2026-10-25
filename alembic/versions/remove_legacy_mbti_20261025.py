"""remove legacy MBTI columns from users

Revision ID: remove_legacy_mbti_20261025
Revises: adde00b2004f
Create Date: 2026-10-25

MBTI is no longer a persisted profile/agent concept. ``users.identity`` is
retained as the free-text self description; only the two MBTI columns are
dropped. Batch operations keep the migration SQLite-compatible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "remove_legacy_mbti_20261025"
down_revision: str | None = "adde00b2004f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("mbti_dims")
        batch_op.drop_column("mbti_type")


def downgrade() -> None:
    # Safe downgrade: re-add the columns as nullable so existing rows stay valid.
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("mbti_type", sa.String(length=4), nullable=True))
        batch_op.add_column(sa.Column("mbti_dims", sa.JSON(), nullable=True))
