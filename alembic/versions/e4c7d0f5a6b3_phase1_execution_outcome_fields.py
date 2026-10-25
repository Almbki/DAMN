"""phase 1: execution outcome fields

Revision ID: e4c7d0f5a6b3
Revises: d3b6c9e4f5a2
Create Date: 2026-10-25 08:30:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e4c7d0f5a6b3'
down_revision: Union[str, None] = 'd3b6c9e4f5a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('task_executions', sa.Column('execution_status', sa.String(length=16), nullable=True))
    op.add_column('task_executions', sa.Column('failure_category', sa.String(length=32), nullable=True))
    op.add_column('task_executions', sa.Column('estimate_feedback', sa.String(length=16), nullable=True))
    # Backfill only rows that already carry an observed outcome (a start-only
    # row stays NULL: 'not observed' is not the same as 'not done').
    op.execute(
        """
        UPDATE task_executions
        SET execution_status = CASE
            WHEN completed THEN 'completed'
            WHEN completion_rate > 0 THEN 'partial'
            ELSE 'not_done'
        END
        WHERE execution_status IS NULL
          AND (completed OR finished_at IS NOT NULL
               OR completion_rate > 0 OR actual_duration IS NOT NULL)
        """
    )


def downgrade() -> None:
    op.drop_column('task_executions', 'estimate_feedback')
    op.drop_column('task_executions', 'failure_category')
    op.drop_column('task_executions', 'execution_status')
