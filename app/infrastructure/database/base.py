"""SQLAlchemy declarative base - single metadata registry for all ORM models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from sqlalchemy.orm import DeclarativeBase


def enum_values(enum_class: type[Enum]) -> list[Any]:
    """``values_callable`` helper for non-native SQLAlchemy enums.

    Stores the *values* of a string enum (e.g. ``"high"``) instead of the
    member *names* (e.g. ``"HIGH"``), so stored data survives member renames.
    """
    return [member.value for member in enum_class]


class Base(DeclarativeBase):
    """Typed declarative base shared by every ORM model in the project.

    Alembic reads ``Base.metadata`` as ``target_metadata``; ORM modules must
    be imported before migrations are generated (see ``alembic/env.py`` and
    ``session.init_db()``).
    """