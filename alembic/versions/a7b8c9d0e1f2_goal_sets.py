"""goal sets and goals.goal_set_id

Revision ID: a7b8c9d0e1f2
Revises: f2b3c4d5e6a7
Create Date: 2026-10-26 00:00:00.000000+00:00

Additive change: a ``goal_sets`` table (目标集) and a nullable, indexed
``goals.goal_set_id`` foreign key (ON DELETE SET NULL). Existing goals keep
``goal_set_id = NULL`` so legacy rows remain readable and are not merged into
any set.

SQLite compatibility: the new column/FK is added through
``batch_alter_table`` (table recreate); the table itself is created normally.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f2b3c4d5e6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FK_NAME = "goals_goal_set_id_fkey"
_GOALS_INDEX = "ix_goals_goal_set_id"


def upgrade() -> None:
    op.create_table(
        "goal_sets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "archived",
                name="goalsetstatus",
                native_enum=False,
                length=32,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_goal_sets_user_id"), "goal_sets", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_goal_sets_status"), "goal_sets", ["status"], unique=False
    )

    with op.batch_alter_table("goals") as batch_op:
        batch_op.add_column(
            sa.Column("goal_set_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            _FK_NAME,
            "goal_sets",
            ["goal_set_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(_GOALS_INDEX, "goals", ["goal_set_id"], unique=False)


def downgrade() -> None:
    op.drop_index(_GOALS_INDEX, table_name="goals")
    with op.batch_alter_table("goals") as batch_op:
        batch_op.drop_constraint(_FK_NAME, type_="foreignkey")
        batch_op.drop_column("goal_set_id")

    op.drop_index(op.f("ix_goal_sets_status"), table_name="goal_sets")
    op.drop_index(op.f("ix_goal_sets_user_id"), table_name="goal_sets")
    op.drop_table("goal_sets")
