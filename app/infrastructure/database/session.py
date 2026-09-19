"""Engine, session factory and transactional session scope."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.infrastructure.database.base import Base

settings = get_settings()

_engine_kwargs: dict[str, Any] = {
    "echo": settings.db_echo,
    "future": True,
}

if settings.is_sqlite:
    # SQLite requires this when sessions cross threads (FastAPI threadpool).
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in settings.database_url:
        # Keep a single shared in-memory sqlite connection alive for tests and
        # short-lived processes.
        _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Open a transactional unit of work.

    Commits when the ``with`` block exits cleanly, rolls back on any exception
    and always closes the session. Services rely on this - repositories never
    commit on their own.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables.

    Imports the ORM model modules first so ``Base.metadata`` is fully
    populated, then runs ``create_all`` (idempotent - no data migration).
    """
    from app.infrastructure.database import models  # noqa: F401  (populate metadata)

    Base.metadata.create_all(bind=engine)