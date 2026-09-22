"""LangGraph checkpointer factory.

Preview/confirm/adjust relies on LangGraph's ``interrupt`` + checkpointing, so a
checkpointer is mandatory for the graphs.

Selection (``Settings.checkpointer_mode``):

* ``postgres`` - :class:`PostgresSaver` (default when ``DATABASE_URL`` is
  PostgreSQL). Tables are created with ``.setup()``.
* ``memory``   - :class:`InMemorySaver` (SQLite dev / tests).

Connection lifetime
-------------------
The Postgres saver is backed by a process-wide
:class:`psycopg_pool.ConnectionPool`, opened here and closed from the FastAPI
lifespan (``close_checkpointer``). Two rules matter:

* **Never hold a single ``Connection``.** Request handlers are synchronous and
  run in a threadpool; one libpq connection is not safe to share across threads.
  The pool hands each ``_cursor()`` call a checked-out connection.
* **Never let the pool object be garbage collected.** It must stay referenced for
  the whole process, otherwise its connections are closed underneath the saver.

The previous implementation called ``PostgresSaver.from_conn_string(dsn).__enter__()``
and dropped the context manager. ``from_conn_string`` is a generator-based
``@contextmanager``; when the manager was collected, its ``finally`` closed the
connection, so the next cursor raised
``psycopg.OperationalError: the connection is closed``.

If Postgres is selected but unreachable, the factory logs loudly and degrades to
in-memory so the API still starts - preview state then does not survive a
restart. The degradation is never silent.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

#: Selects the pool size for the LangGraph checkpointer. Kept modest: preview
#: traffic is low-volume and each generation holds a checkpoint cursor briefly.
_POOL_MIN_SIZE = 1
_POOL_MAX_SIZE = 10
_POOL_OPEN_TIMEOUT_SECONDS = 10.0

_checkpointer: Any | None = None
_checkpointer_pool: Any | None = None
_checkpointer_mode: str = "memory"
_checkpointer_lock = threading.Lock()


def _build_serde() -> Any:
    """Serializer for checkpoints.

    Our state is plain data (Pydantic models + enums), so the default
    ``JsonPlusSerializer`` cannot resolve every class. We allow the app's own
    modules explicitly-ish (``allowed_*_modules=True``) because the checkpoint
    store is our own database.

    HARDENING TODO: this permits deserialising arbitrary classes from the
    checkpoint DB. Before multi-tenant deployment, replace with an explicit
    allowlist of ``(module, attribute)`` pairs.
    """
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    return JsonPlusSerializer(
        pickle_fallback=False,
        allowed_json_modules=True,
        allowed_msgpack_modules=True,
    )


def _build_postgres(dsn: str) -> Any:
    """Build a PostgresSaver on a fresh, open, process-owned connection pool."""
    global _checkpointer_pool

    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg_pool import ConnectionPool

    # ``open=False`` then ``open(wait=True)`` makes an unreachable database fail
    # synchronously (so build_checkpointer can fall back to memory) instead of
    # surfacing later on the first request.
    pool = ConnectionPool(
        conninfo=dsn,
        min_size=_POOL_MIN_SIZE,
        max_size=_POOL_MAX_SIZE,
        open=False,
        # Match PostgresSaver.from_conn_string: autocommit + no prepared statements.
        kwargs={"autocommit": True, "prepare_threshold": 0},
        name="langgraph-checkpointer",
    )
    pool.open(wait=True, timeout=_POOL_OPEN_TIMEOUT_SECONDS)
    try:
        saver = PostgresSaver(pool, serde=_build_serde())
        saver.setup()
    except BaseException:
        pool.close()
        raise
    # Keep the pool referenced for the process lifetime; the saver alone is not a
    # reliable owner (the old code proved that).
    _checkpointer_pool = pool
    return saver


def build_checkpointer(settings: Settings | None = None) -> Any:
    """Create the best available checkpointer for the current settings."""
    global _checkpointer_mode
    settings = settings or get_settings()
    mode = settings.checkpointer_mode

    if mode == "postgres":
        try:
            saver = _build_postgres(settings.checkpointer_dsn)
            _checkpointer_mode = "postgres"
            logger.info("agent checkpointer: PostgresSaver")
            return saver
        except Exception as exc:  # noqa: BLE001 - degrade, but never silently
            logger.warning(
                "agent checkpointer: Postgres unavailable (%s: %s); "
                "falling back to in-memory - preview state will not survive a restart",
                type(exc).__name__,
                exc,
            )

    from langgraph.checkpoint.memory import InMemorySaver

    _checkpointer_mode = "memory"
    logger.info("agent checkpointer: InMemorySaver")
    return InMemorySaver(serde=_build_serde())


def get_checkpointer(settings: Settings | None = None) -> Any:
    """Process-wide cached checkpointer (thread-safe)."""
    global _checkpointer
    if _checkpointer is None:
        with _checkpointer_lock:
            if _checkpointer is None:
                _checkpointer = build_checkpointer(settings)
    return _checkpointer


def get_checkpointer_mode() -> str:
    """Which backend is actually in use (``postgres`` or ``memory``)."""
    return _checkpointer_mode


def close_checkpointer() -> None:
    """Release checkpointer resources (closes the Postgres pool).

    Safe to call in any mode and more than once. The next ``get_checkpointer``
    call rebuilds a fresh saver/pool.
    """
    global _checkpointer, _checkpointer_pool, _checkpointer_mode
    with _checkpointer_lock:
        pool = _checkpointer_pool
        _checkpointer = None
        _checkpointer_pool = None
        _checkpointer_mode = "memory"
    if pool is None:
        return
    try:
        pool.close()
        logger.info("agent checkpointer: connection pool closed")
    except Exception as exc:  # noqa: BLE001 - shutdown must not raise
        logger.warning("agent checkpointer: pool close failed: %s: %s", type(exc).__name__, exc)


def reset_checkpointer() -> None:
    """Drop the cached checkpointer (used by tests)."""
    close_checkpointer()


__all__ = [
    "build_checkpointer",
    "close_checkpointer",
    "get_checkpointer",
    "get_checkpointer_mode",
    "reset_checkpointer",
]
