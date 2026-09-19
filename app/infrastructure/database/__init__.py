"""Database package - public surface for persistence access.

Imports are order-safe: ``__init__`` pulls in the SQLAlchemy declarative base
and the session factory. ``init_db()`` additionally imports the ORM models so
``Base.metadata`` is fully populated before ``create_all`` runs.
"""

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import (
    SessionLocal,
    engine,
    init_db,
    session_scope,
)

__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "init_db",
    "session_scope",
]