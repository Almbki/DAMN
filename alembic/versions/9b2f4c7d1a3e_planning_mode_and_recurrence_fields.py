"""planning mode and recurrence fields

Revision ID: 9b2f4c7d1a3e
Revises: persist_generation_jobs_20261025
Create Date: 2026-10-26 00:00:00.000000+00:00

Adds the product-level ``planning_mode`` (one_off / recurring / project /
project_recurring) and explicit cadence fields to ``goals``, then backfills
existing rows from the legacy ``goal_type`` / ``task_kind`` /
``recurrence_weekdays`` values.

NOTE: the development Postgres instance currently reports a stale Alembic
revision (``49623649564a``) that is not present in this repository. The columns
were applied to that instance directly; this migration is the canonical chain
for a clean checkout / deployment.
"""
from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "9b2f4c7d1a3e"
down_revision: Union[str, None] = "persist_generation_jobs_20261025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _weekdays(value: object) -> list[int]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return []
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for day in value:
        try:
            number = int(day)
        except (TypeError, ValueError):
            continue
        if 0 <= number <= 6:
            result.append(number)
    return result


def upgrade() -> None:
    op.add_column("goals", sa.Column("planning_mode", sa.String(length=32), nullable=True))
    op.add_column(
        "goals", sa.Column("recurrence_frequency", sa.String(length=16), nullable=True)
    )
    op.add_column("goals", sa.Column("recurrence_interval", sa.Integer(), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(
        text(
            "select id, goal_type, task_kind, recurrence_weekdays "
            "from goals"
        )
    ).mappings().all()

    for row in rows:
        weekdays = _weekdays(row["recurrence_weekdays"])
        goal_type = row["goal_type"]
        task_kind = row["task_kind"]
        if task_kind == "one_off":
            mode = "one_off"
        elif goal_type == "project" and weekdays:
            mode = "project_recurring"
        elif goal_type == "project":
            mode = "project"
        elif task_kind in ("routine", "long_term"):
            mode = "recurring"
        elif goal_type in ("habit", "long_term"):
            mode = "recurring"
        else:
            mode = "one_off"

        if mode in ("recurring", "project_recurring"):
            frequency = "weekly" if 0 < len(weekdays) < 7 else "daily"
        else:
            frequency = None

        bind.execute(
            text(
                "update goals set planning_mode=:mode, "
                "recurrence_frequency=:frequency, "
                "recurrence_interval=coalesce(recurrence_interval, 1) "
                "where id=:id"
            ),
            {"mode": mode, "frequency": frequency, "id": row["id"]},
        )

    bind.execute(text("update goals set recurrence_interval=1 where recurrence_interval is null"))


def downgrade() -> None:
    op.drop_column("goals", "recurrence_interval")
    op.drop_column("goals", "recurrence_frequency")
    op.drop_column("goals", "planning_mode")
