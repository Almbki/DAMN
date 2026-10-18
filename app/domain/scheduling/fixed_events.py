"""Fixed calendar events (courses / exams / busy blocks).

The scheduler and the rule engine consume :class:`FixedEvent` values: concrete
``(date, start_time, end_time)`` intervals. Imported :class:`ScheduleEvent`
rows may recur weekly, so this module expands them for a rolling window and
answers the overlap questions the import report needs.
"""

from __future__ import annotations

from datetime import date, time, timedelta

from app.domain.models.schedule_event import ScheduleEvent
from app.domain.scheduling.schedule_result import FixedEvent


def _weekday_set(event: ScheduleEvent) -> set[int] | None:
    """``None`` means "every day" (a bounded non-recurring event)."""
    if event.weekdays:
        return {int(day) for day in event.weekdays}
    return None


def _bounds(event: ScheduleEvent) -> tuple[date | None, date | None]:
    start = event.start_date
    end = event.end_date or event.start_date
    return start, end


def event_occurs_on(event: ScheduleEvent, day: date) -> bool:
    """Does ``event`` happen on ``day``?"""
    start, end = _bounds(event)
    if start is not None and day < start:
        return False
    if end is not None and day > end:
        return False
    weekdays = _weekday_set(event)
    if weekdays is None:
        # Non-recurring: the event covers [start, end] (a single day when equal).
        return start is not None
    return day.weekday() in weekdays


def expand_fixed_events(
    events: list[ScheduleEvent], start: date, end: date
) -> list[FixedEvent]:
    """Expand events into concrete occurrences inside ``[start, end]``."""
    expanded: list[FixedEvent] = []
    if end < start:
        return expanded

    for event in events:
        if event.deleted_at is not None:
            continue
        if event.start_time is None or event.end_time is None:
            continue

        if event.weekdays:
            first = max(start, event.start_date) if event.start_date else start
            last = min(end, event.end_date) if event.end_date else end
            if last < first:
                continue
            for offset in range((last - first).days + 1):
                day = first + timedelta(days=offset)
                if event_occurs_on(event, day):
                    expanded.append(
                        FixedEvent(
                            date=day,
                            start_time=event.start_time,
                            end_time=event.end_time,
                            title=event.title,
                        )
                    )
        else:
            first, last = _bounds(event)
            if first is None:
                continue
            last = last or first
            first = max(first, start)
            last = min(last, end)
            for offset in range(max((last - first).days + 1, 0)):
                day = first + timedelta(days=offset)
                expanded.append(
                    FixedEvent(
                        date=day,
                        start_time=event.start_time,
                        end_time=event.end_time,
                        title=event.title,
                    )
                )

    expanded.sort(key=lambda item: (item.date, item.start_time, item.end_time))
    return expanded


def time_overlap(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    """Half-open interval overlap: touching endpoints do not conflict."""
    return a_start < b_end and b_start < a_end


def _range_intersection(
    a: ScheduleEvent, b: ScheduleEvent
) -> tuple[date | None, date | None, bool]:
    """Return ``(low, high, disjoint)`` for the overlapping date range."""
    a_start, a_end = _bounds(a)
    b_start, b_end = _bounds(b)
    lows = [value for value in (a_start, b_start) if value is not None]
    highs = [value for value in (a_end, b_end) if value is not None]
    low = max(lows) if lows else None
    high = min(highs) if highs else None
    if low is not None and high is not None and low > high:
        return low, high, True
    return low, high, False


def events_overlap(a: ScheduleEvent, b: ScheduleEvent) -> bool:
    """Do two (possibly recurring) events ever share a date and time?"""
    if not time_overlap(a.start_time, a.end_time, b.start_time, b.end_time):
        return False

    a_days = _weekday_set(a)
    b_days = _weekday_set(b)
    # A bounded event with no weekday list happens every day in its range.
    if a_days is None and a.start_date is None:
        return False
    if b_days is None and b.start_date is None:
        return False

    low, high, disjoint = _range_intersection(a, b)
    if disjoint:
        return False

    # Days both sides can occur on. ``None`` on both sides = any day.
    if a_days is not None and b_days is not None:
        days = a_days & b_days
        if not days:
            return False
    else:
        days = a_days if a_days is not None else b_days
        if days is None:
            return True

    if low is None or high is None:
        # At least one side is open-ended: the matching weekday recurs forever.
        return True

    for offset in range(7):
        day = low + timedelta(days=offset)
        if day > high:
            break
        if day.weekday() in days:
            return True
    return False


__all__ = [
    "event_occurs_on",
    "events_overlap",
    "expand_fixed_events",
    "time_overlap",
]
