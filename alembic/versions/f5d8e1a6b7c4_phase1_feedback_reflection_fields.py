"""phase 1: four-section reflection fields

Revision ID: f5d8e1a6b7c4
Revises: e4c7d0f5a6b3
Create Date: 2026-10-25 08:30:00.000000+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f5d8e1a6b7c4'
down_revision: Union[str, None] = 'e4c7d0f5a6b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('feedbacks', sa.Column('day_review', sa.Text(), nullable=True))
    op.add_column('feedbacks', sa.Column('stuck_points', sa.Text(), nullable=True))
    op.add_column('feedbacks', sa.Column('state_review', sa.Text(), nullable=True))
    op.add_column('feedbacks', sa.Column('tomorrow_outlook', sa.Text(), nullable=True))
    op.add_column('feedbacks', sa.Column('day_closed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('feedbacks', 'day_closed_at')
    op.drop_column('feedbacks', 'tomorrow_outlook')
    op.drop_column('feedbacks', 'state_review')
    op.drop_column('feedbacks', 'stuck_points')
    op.drop_column('feedbacks', 'day_review')
