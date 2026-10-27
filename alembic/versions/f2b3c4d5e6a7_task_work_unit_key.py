"""task stable work-unit key

Revision ID: f2b3c4d5e6a7
Revises: c7a1e2f3b4d5
Create Date: 2026-10-26 00:00:00.000000+00:00

Additive, nullable cross-version work-unit identity. Existing rows are
backfilled from the stable fields that already exist: real goal_id + project
series index for project work units, and goal_id for one-off units. Recurring
occurrences intentionally stay NULL (they are not execution-chunked).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "f2b3c4d5e6a7"
down_revision: Union[str, None] = "c7a1e2f3b4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks", sa.Column("work_unit_key", sa.String(length=128), nullable=True)
    )
    op.create_index(
        op.f("ix_tasks_work_unit_key"), "tasks", ["work_unit_key"], unique=False
    )
    op.get_bind().execute(
        text(
            """
            UPDATE tasks SET work_unit_key = CASE
              WHEN goal_id IS NULL THEN NULL
              WHEN series_id LIKE '%-project'
                THEN 'wg-' || goal_id || '-project-' || COALESCE(series_index, 0)
              WHEN task_kind = 'one_off' AND series_id IS NULL
                THEN 'wg-' || goal_id || '-one_off'
              ELSE NULL
            END
            WHERE work_unit_key IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tasks_work_unit_key"), table_name="tasks")
    op.drop_column("tasks", "work_unit_key")
