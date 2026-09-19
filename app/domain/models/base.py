"""Shared base class for domain entities."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict


def utcnow() -> datetime:
    """Timezone-aware ``now`` used as a default for domain models."""
    return datetime.now(UTC)


class DomainModel(BaseModel):
    """Base class for every domain entity.

    ``from_attributes`` lets repositories convert an ORM row directly:
    ``User.model_validate(orm_user)``.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, use_enum_values=False)
