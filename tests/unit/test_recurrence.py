"""Unit tests for deterministic recurrence expansion."""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise

import pytest

from app.domain.recurrence import (
    RecurrenceError,
    RecurrenceFrequency,
    RecurrenceRule,
)


def test_daily_cross_month_is_inclusive() -> None:
    rule = RecurrenceRule(
        frequency=RecurrenceFrequency.DAILY,
        start_date=date(2026, 10, 26),
        end_date=date(2026, 11, 5),
        interval=1,
    )

    days = rule.occurrences()

    assert len(days) == 11
    assert days[0] == date(2026, 10, 26)
    assert days[-1] == date(2026, 11, 5)
    assert len(set(days)) == len(days)
    assert all(
        later - earlier == timedelta(days=1)
        for earlier, later in pairwise(days)
    )


def test_daily_long_span() -> None:
    rule = RecurrenceRule(
        frequency="daily",
        start_date=date(2026, 10, 26),
        end_date=date(2027, 7, 1),
        interval=1,
    )

    days = rule.occurrences()

    assert len(days) == 249
    assert days[0] == date(2026, 10, 26)
    assert days[-1] == date(2027, 7, 1)
    assert len(set(days)) == len(days)
    assert all(date(2026, 10, 26) <= day <= date(2027, 7, 1) for day in days)


def test_weekly_saturday_matches_known_dates() -> None:
    rule = RecurrenceRule(
        frequency=RecurrenceFrequency.WEEKLY,
        start_date=date(2026, 10, 26),
        end_date=date(2026, 12, 31),
        weekdays=(5,),
    )

    days = rule.occurrences()

    assert days[0] == date(2026, 10, 31)
    assert all(day.weekday() == 5 for day in days)
    assert days == [
        date(2026, 10, 31),
        date(2026, 11, 7),
        date(2026, 11, 14),
        date(2026, 11, 21),
        date(2026, 11, 28),
        date(2026, 12, 5),
        date(2026, 12, 12),
        date(2026, 12, 19),
        date(2026, 12, 26),
    ]


def test_weekly_biweekly_saturday() -> None:
    rule = RecurrenceRule(
        frequency=RecurrenceFrequency.WEEKLY,
        start_date=date(2026, 10, 26),
        end_date=date(2026, 12, 31),
        interval=2,
        weekdays=(5,),
    )

    assert rule.occurrences() == [
        date(2026, 10, 31),
        date(2026, 11, 14),
        date(2026, 11, 28),
        date(2026, 12, 12),
        date(2026, 12, 26),
    ]


def test_weekly_defaults_to_start_weekday() -> None:
    rule = RecurrenceRule(
        frequency=RecurrenceFrequency.WEEKLY,
        start_date=date(2026, 10, 28),
        end_date=date(2026, 11, 25),
    )

    days = rule.occurrences()

    assert days[0] == date(2026, 10, 28)
    assert all(day.weekday() == 2 for day in days)


def test_single_day_daily_range() -> None:
    rule = RecurrenceRule(
        frequency=RecurrenceFrequency.DAILY,
        start_date=date(2026, 10, 26),
        end_date=date(2026, 10, 26),
    )

    assert rule.occurrences() == [date(2026, 10, 26)]


def test_end_before_start_is_invalid() -> None:
    with pytest.raises(RecurrenceError):
        RecurrenceRule(
            frequency=RecurrenceFrequency.DAILY,
            start_date=date(2026, 11, 5),
            end_date=date(2026, 10, 26),
        )


def test_weekly_without_matching_weekday_is_invalid() -> None:
    rule = RecurrenceRule(
        frequency=RecurrenceFrequency.WEEKLY,
        start_date=date(2026, 10, 27),
        end_date=date(2026, 10, 28),
        weekdays=(5,),
    )

    with pytest.raises(RecurrenceError):
        rule.occurrences()


def test_invalid_interval_is_rejected() -> None:
    with pytest.raises(RecurrenceError):
        RecurrenceRule(
            frequency=RecurrenceFrequency.DAILY,
            start_date=date(2026, 10, 26),
            end_date=date(2026, 10, 27),
            interval=0,
        )


def test_invalid_weekday_is_rejected() -> None:
    with pytest.raises(RecurrenceError):
        RecurrenceRule(
            frequency=RecurrenceFrequency.WEEKLY,
            start_date=date(2026, 10, 26),
            end_date=date(2026, 12, 31),
            weekdays=(7,),
        )


def test_invalid_frequency_is_rejected() -> None:
    with pytest.raises(RecurrenceError):
        RecurrenceRule(
            frequency="monthly",
            start_date=date(2026, 10, 26),
            end_date=date(2026, 10, 27),
        )


def test_occurrence_cap_is_enforced_without_truncation() -> None:
    rule = RecurrenceRule(
        frequency=RecurrenceFrequency.DAILY,
        start_date=date(2018, 1, 1),
        end_date=date(2030, 1, 1),
    )

    with pytest.raises(RecurrenceError):
        rule.occurrences()


def test_contains() -> None:
    rule = RecurrenceRule(
        frequency=RecurrenceFrequency.WEEKLY,
        start_date=date(2026, 10, 26),
        end_date=date(2026, 12, 31),
        weekdays=(5,),
    )

    assert rule.contains(date(2026, 10, 31)) is True
    assert rule.contains(date(2026, 11, 1)) is False
    assert rule.contains(date(2025, 1, 1)) is False
