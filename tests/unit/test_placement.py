"""30-minute drag grid snapping (single rule for every platform)."""

from __future__ import annotations

from datetime import time

import pytest

from app.domain.scheduling.placement import (
    add_minutes,
    snap_time_to_grid,
    time_to_minutes,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (time(14, 0), time(14, 0)),
        (time(14, 14), time(14, 0)),
        (time(14, 15), time(14, 30)),  # half-up boundary
        (time(14, 16), time(14, 30)),
        (time(14, 30), time(14, 30)),
        (time(14, 44), time(14, 30)),
        (time(14, 46), time(15, 0)),
        (time(9, 29), time(9, 30)),
    ],
)
def test_snap_time_to_nearest_thirty_minutes(value: time, expected: time) -> None:
    assert snap_time_to_grid(value) == expected


def test_snap_does_not_wrap_past_midnight() -> None:
    assert snap_time_to_grid(time(23, 50)) == time(23, 30)


def test_duration_does_not_need_to_align_to_the_grid() -> None:
    start = snap_time_to_grid(time(9, 31))
    assert start == time(9, 30)
    assert add_minutes(start, 75) == time(10, 45)
    assert time_to_minutes(start) == 9 * 60 + 30
