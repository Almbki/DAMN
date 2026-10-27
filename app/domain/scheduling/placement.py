"""Deterministic time-placement helpers for execution-time MOVE operations."""

from __future__ import annotations

from datetime import time

#: The coarse placement grid used by drag-and-drop. Task detail edits remain
#: precise (any minute).
GRID_MINUTES = 30


def time_to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def minutes_to_time(total: int) -> time:
    total %= 24 * 60
    return time(total // 60, total % 60)


def snap_time_to_grid(value: time, grid_minutes: int = GRID_MINUTES) -> time:
    """Snap to the nearest grid line, half-up (14:15 -> 14:30).

    The last grid line of the day is the upper clamp, so a late-evening time can
    never wrap to 00:00. Placement validation still rejects a block that does not
    fit before ``day_end``.
    """
    if grid_minutes <= 0:
        raise ValueError("grid_minutes must be positive")
    total = time_to_minutes(value)
    snapped = ((total + grid_minutes // 2) // grid_minutes) * grid_minutes
    last_grid = (24 * 60 // grid_minutes - 1) * grid_minutes
    return minutes_to_time(min(snapped, last_grid))


def add_minutes(value: time, minutes: int) -> time:
    """Add minutes without wrapping silently past midnight."""
    return minutes_to_time(time_to_minutes(value) + minutes)


__all__ = [
    "GRID_MINUTES",
    "add_minutes",
    "minutes_to_time",
    "snap_time_to_grid",
    "time_to_minutes",
]
