"""Repository base class shared by all implementations."""

from __future__ import annotations

from sqlalchemy.orm import Session


class RepositoryBase:
    """Session-bound persistence helper.

    Repositories NEVER commit/rollback - the service layer owns transactions
    via ``session_scope()``. Only ``session.flush()`` is used so callers can
    read back freshly generated primary keys and server defaults within the
    same unit of work.
    """

    def __init__(self, session: Session) -> None:
        self._session = session