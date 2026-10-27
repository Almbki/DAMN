"""Deterministic recurrence expansion. NO LLM, NO regex, NO title parsing."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from pydantic import BaseModel, Field

MAX_OCCURRENCES_PER_SERIES = 2000

__all__ = [
    "MAX_OCCURRENCES_PER_SERIES",
    "RecurrenceError",
    "RecurrenceFrequency",
    "RecurrenceRule",
    "SeriesSpec",
]


class RecurrenceError(ValueError):
    """Raised when a recurrence rule is invalid or cannot be materialized."""


class RecurrenceFrequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"


class SeriesSpec(BaseModel):
    """Deterministic description of one materialized series.

    Produced by the plan drafter (never by the LLM) and consumed by the rule
    engine to check duplicate / wrong-day / incomplete occurrences.
    """

    series_id: str
    start_date: date
    end_date: date
    frequency: RecurrenceFrequency
    interval: int = Field(default=1, ge=1)
    weekdays: list[int] = Field(default_factory=list)


@dataclass(frozen=True)
class RecurrenceRule:
    """An inclusive, deterministic recurrence over calendar dates."""

    frequency: RecurrenceFrequency | str
    start_date: date
    end_date: date
    interval: int = 1
    weekdays: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        try:
            frequency = RecurrenceFrequency(self.frequency)
        except ValueError as exc:
            raise RecurrenceError(
                f"invalid recurrence frequency: {self.frequency!r}"
            ) from exc
        object.__setattr__(self, "frequency", frequency)

        if self.interval < 1:
            raise RecurrenceError(f"interval must be >= 1, got {self.interval}")
        if self.end_date < self.start_date:
            raise RecurrenceError(
                f"end_date {self.end_date} is before start_date {self.start_date}"
            )
        for weekday in self.weekdays:
            if not 0 <= weekday <= 6:
                raise RecurrenceError(
                    f"weekday must be in 0..6 (Monday=0), got {weekday}"
                )

        if frequency is RecurrenceFrequency.WEEKLY and not self.weekdays:
            object.__setattr__(self, "weekdays", (self.start_date.weekday(),))

    def _iter_occurrences(self) -> Iterator[date]:
        if self.frequency is RecurrenceFrequency.DAILY:
            current = self.start_date
            step = timedelta(days=self.interval)
            while current <= self.end_date:
                yield current
                current += step
            return

        weekdays = set(self.weekdays)
        anchor_monday = self.start_date - timedelta(days=self.start_date.weekday())
        current = self.start_date
        while current <= self.end_date:
            if current.weekday() in weekdays:
                week_monday = current - timedelta(days=current.weekday())
                week_index = (week_monday - anchor_monday).days // 7
                if week_index % self.interval == 0:
                    yield current
            current += timedelta(days=1)

    def occurrences(self) -> list[date]:
        """Return every occurrence in ascending order (inclusive of both bounds)."""
        result: list[date] = []
        for day in self._iter_occurrences():
            if len(result) >= MAX_OCCURRENCES_PER_SERIES:
                raise RecurrenceError(
                    "recurrence would exceed "
                    f"{MAX_OCCURRENCES_PER_SERIES} occurrences"
                )
            result.append(day)
        if not result:
            raise RecurrenceError(
                f"recurrence {self.frequency.value} rule has no occurrences "
                f"between {self.start_date} and {self.end_date}"
            )
        return result

    def contains(self, day: date) -> bool:
        """Return True iff ``day`` is an occurrence; out-of-range days are False."""
        try:
            return day in self.occurrences()
        except RecurrenceError:
            return False
