"""LangGraph checkpointer factory.

Preview/confirm/adjust relies on LangGraph's ``interrupt`` + checkpointing, so a
checkpointer is mandatory for the graphs.

Selection (``Settings.checkpointer_mode``):

* ``postgres`` - :class:`PostgresSaver` (default when ``DATABASE_URL`` is
  PostgreSQL). Tables are created with ``.setup()``.
* ``memory``   - :class:`InMemorySaver` (SQLite dev / tests).

If Postgres is selected but unreachable, the factory logs loudly and degrades to
in-memory so the API still starts - preview state then does not survive a
restart. The degradation is never silent.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_checkpointer: Any | None = None
_checkpointer_mode: str = "memory"


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
    from langgraph.checkpoint.postgres import PostgresSaver

    manager = PostgresSaver.from_conn_string(dsn)
    saver = manager.__enter__()
    saver.serde = _build_serde()
    saver.setup()
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
    """Process-wide cached checkpointer."""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = build_checkpointer(settings)
    return _checkpointer


def get_checkpointer_mode() -> str:
    """Which backend is actually in use (``postgres`` or ``memory``)."""
    return _checkpointer_mode


def reset_checkpointer() -> None:
    """Drop the cached checkpointer (used by tests)."""
    global _checkpointer
    _checkpointer = None


__all__ = [
    "build_checkpointer",
    "get_checkpointer",
    "get_checkpointer_mode",
    "reset_checkpointer",
]
