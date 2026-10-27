"""Canonical product-clock helpers.

All execution-lifecycle decisions (OVERDUE / MISSED / feedback obligations) must
use the product's local calendar date, never ``datetime.utcnow().date()``. v1 has
one server-side product timezone (``APP_TIMEZONE``); per-user timezones are not
persisted yet.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import get_settings


def _resolve_zone(tz_name: str | None) -> ZoneInfo:
    name = tz_name or get_settings().app_timezone
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        # Never crash a lifecycle decision on a bad IANA name: fall back to the
        # host's local zone, which is the pre-existing behaviour.
        return datetime.now().astimezone().tzinfo or UTC  # type: ignore[return-value]


def local_date_at(instant: datetime, tz_name: str | None = None) -> date:
    """Calendar date of an aware/naive UTC instant in the product timezone."""
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    return instant.astimezone(_resolve_zone(tz_name)).date()


def local_now(tz_name: str | None = None) -> datetime:
    return datetime.now(_resolve_zone(tz_name))


def local_today(tz_name: str | None = None) -> date:
    """The product's current calendar date."""
    return local_now(tz_name).date()
