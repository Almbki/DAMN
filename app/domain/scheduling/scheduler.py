"""Heuristic, deterministic scheduler - NO LLM calls allowed.

Algorithm (documented heuristic)
--------------------------------
1. Drop tasks in ``context.completed_task_ids``.
2. Order the rest by ``priority`` desc, then "deadline-having tasks first" and
   ``deadline`` asc, then cognitive load (HIGH first), then ``order_index``.
3. Build a finite horizon: ``start_date = today``, ``end_date = max(latest
   deadline, start + default_horizon_days)`` (always >= start).
4. Greedily place each task on the *first* day where every hard constraint
   holds; within that day evaluate **all** legal slots and choose the best
   soft-preference slot (user/load time window, stable series habit, spread)
   instead of blindly taking the first legal slot.
   * remaining capacity = ``min(daily_limit_minutes, available_minutes_per_day)``;
   * buffer ``>= context.buffer_minutes`` to both neighbouring tasks;
   * high-cognitive daily cap ``context.high_cognitive_max_per_day``;
   * conflicting-subject pairs (case-insensitive);
    * the ``[day_start, day_end]`` window;
    * no overlap with any ``RuleContext.fixed_events`` (imported courses etc.);
    * the 30-minute non-consecutive HIGH spacing rule, so the candidate is more
      likely to pass the rule engine unchanged.
5. Soft preferences only rank legal slots; hard constraints always win.
   Without an explicit preference, generic load windows are used: HIGH morning,
   MEDIUM afternoon, LOW late-afternoon, RESTORATIVE evening.
6. ``duration_minutes = task.predicted_duration or task.estimated_duration``;
   ``completion_probability = task.completion_probability or 1.0``.
7. Tasks that cannot be placed anywhere in the horizon are listed in
   ``CandidateSchedule.unscheduled_task_ids``.

The output is a *candidate*: the rule engine
(``app.domain.rules``) is the only authority on hard constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta

from app.domain.models import Task
from app.domain.models.enums import CognitiveLoad
from app.domain.rules.base import RuleContext
from app.domain.scheduling.constants import (
    DEFAULT_HORIZON_DAYS,
    GOAL_DAILY_CAPACITY_EXCEEDED,
)
from app.domain.scheduling.schedule_result import (
    CandidateSchedule,
    ScheduledTask,
    SchedulingFailure,
)

#: Minimum gap between two consecutive HIGH tasks (mirrors the rule module).
HIGH_GAP_MINUTES = 30
#: ``date`` sentinel used to push deadline-less tasks to the back of the sort.
_FAR_FUTURE = date.max


@dataclass
class SchedulerConfig:
    """Tunables of the heuristic scheduler.

    ``max_high_cognitive_per_day`` is informational: the authoritative high-
    cognitive cap always comes from ``RuleContext.high_cognitive_max_per_day``.
    """

    day_start: time = time(8, 0)
    day_end: time = time(22, 0)
    slot_minutes: int = 15
    max_high_cognitive_per_day: int = 2
    default_horizon_days: int = DEFAULT_HORIZON_DAYS


def _to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _from_minutes(minutes: int) -> time:
    minutes %= 24 * 60
    return time(minutes // 60, minutes % 60)


#: Cognitive-load sort weight - HIGH (0) before the rest.
_COGNITIVE_WEIGHT = {
    CognitiveLoad.HIGH: 0,
    CognitiveLoad.MEDIUM: 1,
    CognitiveLoad.LOW: 2,
    CognitiveLoad.RESTORATIVE: 3,
}

#: Generic soft windows, used only when the user has no explicit preference.
_TIME_OF_DAY_WINDOWS: dict[str, tuple[time, time]] = {
    "morning": (time(9, 0), time(12, 0)),
    "afternoon": (time(13, 0), time(17, 0)),
    "evening": (time(18, 0), time(22, 0)),
    "night": (time(20, 0), time(22, 0)),
}
_DEFAULT_LOAD_WINDOWS: dict[CognitiveLoad, tuple[time, time]] = {
    CognitiveLoad.HIGH: _TIME_OF_DAY_WINDOWS["morning"],
    CognitiveLoad.MEDIUM: _TIME_OF_DAY_WINDOWS["afternoon"],
    CognitiveLoad.LOW: (time(15, 0), time(19, 0)),
    CognitiveLoad.RESTORATIVE: (time(18, 0), time(21, 0)),
}


def default_horizon(
    tasks: list[Task],
    context: RuleContext,
    *,
    today: date | None = None,
) -> tuple[date, date]:
    """Compute the scheduling horizon for a task set.

    ``start_date`` is the explicit plan horizon start when provided, otherwise
    ``today``. ``end_date`` starts from the explicit plan horizon (or
    ``start + default_horizon_days``) and is extended by every task deadline,
    guaranteed never to be before ``start_date``.
    """
    start = context.schedule_start or today or date.today()
    end = context.schedule_end or (start + timedelta(days=DEFAULT_HORIZON_DAYS))
    for deadline in context.task_deadlines.values():
        if deadline > end:
            end = deadline
    if end < start:
        end = start
    return start, end


class Scheduler:
    """Deterministic greedy scheduler. Pure, synchronous, LLM-free."""

    def __init__(self, config: SchedulerConfig | None = None) -> None:
        self.config = config if config is not None else SchedulerConfig()

    def default_horizon(
        self, tasks: list[Task], context: RuleContext, *, today: date | None = None
    ) -> tuple[date, date]:
        """Instance wrapper around the module-level :func:`default_horizon`."""
        return default_horizon(tasks, context, today=today)

    def schedule(
        self, tasks: list[Task], context: RuleContext
    ) -> CandidateSchedule:
        start_date, end_date = self.default_horizon(
            tasks, context, today=context.today or date.today()
        )

        # (1) skip completed tasks; ids are required to place a task.
        eligible = [
            t for t in tasks if t.id is not None and t.id not in context.completed_task_ids
        ]

        # (2) deterministic priority order.
        ordered = sorted(eligible, key=lambda t: self._sort_key_for(t, context))

        placements: dict[date, list[ScheduledTask]] = {}
        day_minutes: dict[date, int] = {}
        day_high_count: dict[date, int] = {}
        goal_day_minutes: dict[tuple[int, date], int] = {}
        scheduled: list[ScheduledTask] = []
        unscheduled: list[int] = []
        unscheduled_reasons: dict[int, SchedulingFailure] = {}
        series_time: dict[str, time] = {}

        for task in ordered:
            assert task.id is not None  # guaranteed above, keep mypy happy
            duration = task.predicted_duration or task.estimated_duration
            probability = (
                task.completion_probability
                if task.completion_probability is not None
                else 1.0
            )

            day, slot_start = self._first_feasible(
                task,
                duration,
                context,
                start_date,
                end_date,
                placements,
                day_minutes,
                day_high_count,
                goal_day_minutes,
                series_time,
            )
            if day is None:
                unscheduled.append(task.id)
                unscheduled_reasons[task.id] = self._diagnose(
                    task,
                    duration,
                    context,
                    start_date,
                    end_date,
                    placements,
                    day_minutes,
                    day_high_count,
                    goal_day_minutes,
                )
                continue

            start_min = _to_minutes(slot_start)
            placed = ScheduledTask(
                task_id=task.id,
                title=task.title,
                goal_id=task.goal_id,
                scheduled_date=day,
                start_time=slot_start,
                end_time=_from_minutes(start_min + duration),
                duration_minutes=duration,
                cognitive_load=task.cognitive_load,
                priority=task.priority,
                completion_probability=probability,
                is_flexible=task.is_flexible,
                series_id=task.series_id,
                occurrence_date=task.occurrence_date,
            )
            placements.setdefault(day, []).append(placed)
            day_minutes[day] = day_minutes.get(day, 0) + duration
            if task.goal_id is not None:
                goal_key = (task.goal_id, day)
                goal_day_minutes[goal_key] = (
                    goal_day_minutes.get(goal_key, 0) + duration
                )
            if task.cognitive_load == CognitiveLoad.HIGH:
                day_high_count[day] = day_high_count.get(day, 0) + 1
            if task.series_id is not None and task.series_id not in series_time:
                # Keep a recurring habit at the first chosen time unless the
                # hard constraints force a different slot on a later day.
                series_time[task.series_id] = slot_start
            scheduled.append(placed)

        return CandidateSchedule(
            start_date=start_date,
            end_date=end_date,
            tasks=sorted(scheduled, key=lambda t: (t.scheduled_date, t.start_time)),
            unscheduled_task_ids=unscheduled,
            unscheduled_reasons=unscheduled_reasons,
        )

    def schedule_sequence(
        self,
        tasks: list[Task],
        context: RuleContext,
        *,
        occupied: CandidateSchedule | None = None,
    ) -> CandidateSchedule:
        """Place an ordered work-unit sequence, preserving input order.

        Used by execution-time LOCAL_RESCHEDULE: the semantic order is fixed by
        the caller (``work_unit`` / chunk order), unrelated plan tasks are passed
        as ``occupied`` busy intervals, and each task may only be placed on or
        after the previous sequence task's day. All hard-constraint math is the
        same ``_first_feasible`` / ``_best_slot`` path as a full plan.
        """
        start_date, end_date = self.default_horizon(
            tasks, context, today=context.today or date.today()
        )

        placements: dict[date, list[ScheduledTask]] = {}
        day_minutes: dict[date, int] = {}
        day_high_count: dict[date, int] = {}
        goal_day_minutes: dict[tuple[int, date], int] = {}
        series_time: dict[str, time] = {}
        for item in (occupied.tasks if occupied is not None else []):
            placements.setdefault(item.scheduled_date, []).append(item)
            day_minutes[item.scheduled_date] = (
                day_minutes.get(item.scheduled_date, 0) + item.duration_minutes
            )
            if item.goal_id is not None:
                key = (item.goal_id, item.scheduled_date)
                goal_day_minutes[key] = (
                    goal_day_minutes.get(key, 0) + item.duration_minutes
                )
            if item.cognitive_load == CognitiveLoad.HIGH:
                day_high_count[item.scheduled_date] = (
                    day_high_count.get(item.scheduled_date, 0) + 1
                )
            if item.series_id is not None and item.series_id not in series_time:
                series_time[item.series_id] = item.start_time

        scheduled: list[ScheduledTask] = []
        unscheduled: list[int] = []
        unscheduled_reasons: dict[int, SchedulingFailure] = {}
        cursor = start_date

        for index, task in enumerate(tasks):
            if task.id is None:
                continue
            duration = task.predicted_duration or task.estimated_duration
            base_earliest = context.task_earliest_dates.get(task.id, start_date)
            # Minimal-repair rule: never pull a later sequence task earlier than
            # its current placement, and never place it before the previous
            # sequence task. Overdue/backlog dates are already in the past, so
            # the cursor wins; future rhythm is preserved.
            original_day = task.scheduled_date or start_date
            earliest = max(base_earliest, cursor, original_day)
            local_context = context.model_copy(
                update={
                    "task_earliest_dates": {
                        **context.task_earliest_dates,
                        task.id: earliest,
                    }
                }
            )
            day, slot_start = self._first_feasible(
                task,
                duration,
                local_context,
                start_date,
                end_date,
                placements,
                day_minutes,
                day_high_count,
                goal_day_minutes,
                series_time,
            )
            if day is None:
                reason = self._diagnose(
                    task,
                    duration,
                    local_context,
                    start_date,
                    end_date,
                    placements,
                    day_minutes,
                    day_high_count,
                    goal_day_minutes,
                )
                unscheduled.append(task.id)
                unscheduled_reasons[task.id] = reason
                # The sequence is atomic: a blocked task also blocks everything
                # after it, so the caller can report one deterministic failure and
                # leave the persisted plan untouched.
                for leftover in tasks[index + 1 :]:
                    if leftover.id is None:
                        continue
                    unscheduled.append(leftover.id)
                    unscheduled_reasons[leftover.id] = SchedulingFailure(
                        code="SEQUENCE_BLOCKED",
                        message=(
                            f"Blocked by the unscheduled earlier sequence task "
                            f"{task.id}."
                        ),
                    )
                break

            start_min = _to_minutes(slot_start)
            placed = ScheduledTask(
                task_id=task.id,
                title=task.title,
                goal_id=task.goal_id,
                scheduled_date=day,
                start_time=slot_start,
                end_time=_from_minutes(start_min + duration),
                duration_minutes=duration,
                cognitive_load=task.cognitive_load,
                priority=task.priority,
                completion_probability=(
                    task.completion_probability
                    if task.completion_probability is not None
                    else 1.0
                ),
                is_flexible=task.is_flexible,
                series_id=task.series_id,
                occurrence_date=task.occurrence_date,
            )
            placements.setdefault(day, []).append(placed)
            day_minutes[day] = day_minutes.get(day, 0) + duration
            if task.goal_id is not None:
                key = (task.goal_id, day)
                goal_day_minutes[key] = goal_day_minutes.get(key, 0) + duration
            if task.cognitive_load == CognitiveLoad.HIGH:
                day_high_count[day] = day_high_count.get(day, 0) + 1
            if task.series_id is not None and task.series_id not in series_time:
                series_time[task.series_id] = slot_start
            scheduled.append(placed)
            cursor = day

        return CandidateSchedule(
            start_date=start_date,
            end_date=end_date,
            tasks=sorted(scheduled, key=lambda t: (t.scheduled_date, t.start_time)),
            unscheduled_task_ids=unscheduled,
            unscheduled_reasons=unscheduled_reasons,
        )

    # -- internals ---------------------------------------------------------

    def _sort_key_for(
        self, task: Task, context: RuleContext
    ) -> tuple[int, int, date, int, int]:
        deadline = None if task.id is None else context.task_deadlines.get(task.id)
        return (
            -int(task.priority),  # priority desc (CRITICAL=4 first)
            1 if deadline is None else 0,  # deadline-having tasks first
            deadline if deadline is not None else _FAR_FUTURE,  # deadline asc
            _COGNITIVE_WEIGHT[task.cognitive_load],  # HIGH first
            task.order_index,  # order_index asc
        )

    def _first_feasible(
        self,
        task: Task,
        duration: int,
        context: RuleContext,
        start_date: date,
        end_date: date,
        placements: dict[date, list[ScheduledTask]],
        day_minutes: dict[date, int],
        day_high_count: dict[date, int],
        goal_day_minutes: dict[tuple[int, date], int],
        series_time: dict[str, time],
    ) -> tuple[date | None, time | None]:
        capacity = min(
            context.daily_limit_minutes, context.available_minutes_per_day
        )
        high_cap = context.high_cognitive_max_per_day
        task_subject = context.task_subjects.get(task.id)
        is_high = task.cognitive_load == CognitiveLoad.HIGH

        # Series occurrences must never be pulled before their occurrence date.
        earliest = (
            context.task_earliest_dates.get(task.id, start_date)
            if task.id is not None
            else start_date
        )
        scan_start = max(start_date, earliest)
        # A materialized occurrence may never be placed after its own day: the
        # deadline is the occurrence date, so an over-capacity day must leave
        # it unscheduled instead of silently drifting to a later day. One-off
        # tasks keep the historical candidate behaviour; the rule engine (and
        # plan_repair) still catch/repair a missed one-off deadline.
        deadline = (
            context.task_deadlines.get(task.id) if task.id is not None else None
        )
        is_occurrence = task.occurrence_date is not None or task.series_id is not None
        scan_end = (
            min(end_date, deadline)
            if is_occurrence and deadline is not None
            else end_date
        )
        if scan_start > scan_end:
            return None, None

        span = (scan_end - scan_start).days
        for offset in range(span + 1):
            day = scan_start + timedelta(days=offset)

            # Fixed events consume usable capacity in addition to never being
            # overlapped (the slot check below enforces the latter).
            day_capacity = max(capacity - self._fixed_minutes_on(day, context), 0)
            if day_minutes.get(day, 0) + duration > day_capacity:
                continue
            if (
                task.goal_id is not None
                and goal_day_minutes.get((task.goal_id, day), 0) + duration
                > context.max_daily_minutes_per_goal
            ):
                continue
            if is_high and day_high_count.get(day, 0) >= high_cap:
                continue
            if self._subject_conflicts(day, task_subject, context, placements):
                continue

            slot_start = self._best_slot(
                day,
                task,
                duration,
                context,
                placements.get(day, []),
                series_time,
            )
            if slot_start is not None:
                return day, slot_start
        return None, None

    def _max_free_minutes(
        self,
        day: date,
        context: RuleContext,
        placed: list[ScheduledTask],
    ) -> int:
        """Largest contiguous free interval on ``day`` inside the usable window."""
        window_start = _to_minutes(context.day_start)
        window_end = _to_minutes(context.day_end)
        busy: list[tuple[int, int]] = []
        for event in context.fixed_events:
            if event.date == day:
                start = max(window_start, _to_minutes(event.start_time))
                end = min(window_end, _to_minutes(event.end_time))
                if end > start:
                    busy.append((start, end))
        for item in placed:
            start = max(window_start, _to_minutes(item.start_time))
            end = min(window_end, _to_minutes(item.end_time))
            if end > start:
                busy.append((start, end))
        if not busy:
            return max(0, window_end - window_start)
        busy.sort()
        best = 0
        cursor = window_start
        for start, end in busy:
            if start > cursor:
                best = max(best, start - cursor)
            cursor = max(cursor, end)
        best = max(best, window_end - cursor)
        return max(0, best)

    def max_contiguous_minutes(
        self,
        task: Task,
        context: RuleContext,
        schedule: CandidateSchedule | None = None,
    ) -> int:
        """Largest feasible block for ``task`` across the current horizon.

        Uses the current schedule's placements as busy intervals, so chunking is
        based on real free space rather than a static maximum.
        """
        start, end = self.default_horizon(
            [task], context, today=context.today or date.today()
        )
        earliest = (
            context.task_earliest_dates.get(task.id, start)
            if task.id is not None
            else start
        )
        scan_start = max(start, earliest)
        deadline = (
            context.task_deadlines.get(task.id) if task.id is not None else None
        )
        is_occurrence = task.occurrence_date is not None or task.series_id is not None
        scan_end = min(end, deadline) if is_occurrence and deadline else end
        if scan_start > scan_end:
            return 0

        placements: dict[date, list[ScheduledTask]] = {}
        day_minutes: dict[date, int] = {}
        day_high: dict[date, int] = {}
        goal_day_minutes: dict[tuple[int, date], int] = {}
        if schedule is not None:
            for item in schedule.tasks:
                placements.setdefault(item.scheduled_date, []).append(item)
                day_minutes[item.scheduled_date] = (
                    day_minutes.get(item.scheduled_date, 0) + item.duration_minutes
                )
                if item.goal_id is not None:
                    goal_key = (item.goal_id, item.scheduled_date)
                    goal_day_minutes[goal_key] = (
                        goal_day_minutes.get(goal_key, 0) + item.duration_minutes
                    )
                if item.cognitive_load == CognitiveLoad.HIGH:
                    day_high[item.scheduled_date] = (
                        day_high.get(item.scheduled_date, 0) + 1
                    )

        capacity = min(
            context.daily_limit_minutes, context.available_minutes_per_day
        )
        best = 0
        for offset in range((scan_end - scan_start).days + 1):
            day = scan_start + timedelta(days=offset)
            if (
                task.cognitive_load == CognitiveLoad.HIGH
                and day_high.get(day, 0) >= context.high_cognitive_max_per_day
            ):
                continue
            fixed = self._fixed_minutes_on(day, context)
            remaining = max(
                capacity - fixed - day_minutes.get(day, 0),
                0,
            )
            if task.goal_id is not None:
                remaining = min(
                    remaining,
                    max(
                        context.max_daily_minutes_per_goal
                        - goal_day_minutes.get((task.goal_id, day), 0),
                        0,
                    ),
                )
            free = self._max_free_minutes(day, context, placements.get(day, []))
            best = max(best, min(remaining, free))
        return best

    def _diagnose(
        self,
        task: Task,
        duration: int,
        context: RuleContext,
        start_date: date,
        end_date: date,
        placements: dict[date, list[ScheduledTask]],
        day_minutes: dict[date, int],
        day_high_count: dict[date, int],
        goal_day_minutes: dict[tuple[int, date], int],
    ) -> SchedulingFailure:
        earliest = (
            context.task_earliest_dates.get(task.id, start_date)
            if task.id is not None
            else start_date
        )
        scan_start = max(start_date, earliest)
        deadline = (
            context.task_deadlines.get(task.id) if task.id is not None else None
        )
        is_occurrence = task.occurrence_date is not None or task.series_id is not None
        scan_end = min(end_date, deadline) if is_occurrence and deadline else end_date
        if scan_start > scan_end:
            return SchedulingFailure(
                code="DEADLINE_CONFLICT",
                needed_minutes=duration,
                available_minutes=0,
                message="no day between earliest date and deadline",
            )

        capacity = min(
            context.daily_limit_minutes, context.available_minutes_per_day
        )
        high_cap = context.high_cognitive_max_per_day
        best_free = 0
        capacity_blocked = False
        high_blocked = False
        fixed_blocked = False
        goal_blocked = False
        goal_best_free = 0

        for offset in range((scan_end - scan_start).days + 1):
            day = scan_start + timedelta(days=offset)
            fixed = self._fixed_minutes_on(day, context)
            day_capacity = max(capacity - fixed - day_minutes.get(day, 0), 0)
            if duration > day_capacity:
                capacity_blocked = True
            if (
                task.cognitive_load == CognitiveLoad.HIGH
                and day_high_count.get(day, 0) >= high_cap
            ):
                high_blocked = True
                continue
            free = self._max_free_minutes(day, context, placements.get(day, []))
            goal_remaining = context.max_daily_minutes_per_goal
            if task.goal_id is not None:
                goal_remaining = max(
                    context.max_daily_minutes_per_goal
                    - goal_day_minutes.get((task.goal_id, day), 0),
                    0,
                )
                if duration > goal_remaining:
                    goal_blocked = True
            best_free = max(best_free, min(free, day_capacity))
            goal_best_free = max(
                goal_best_free, min(free, day_capacity, goal_remaining)
            )
            if context.fixed_events and free < duration:
                fixed_blocked = True

        if high_blocked and best_free < duration:
            return SchedulingFailure(
                code="HIGH_COGNITIVE_LIMIT",
                needed_minutes=duration,
                available_minutes=best_free,
                message="daily high-cognitive task cap reached",
            )
        if duration > capacity:
            return SchedulingFailure(
                code="DAILY_CAPACITY_EXCEEDED",
                needed_minutes=duration,
                available_minutes=best_free,
                message="task is longer than the daily capacity",
            )
        if (
            task.goal_id is not None
            and goal_blocked
            and best_free >= duration
            and goal_best_free < duration
        ):
            return SchedulingFailure(
                code=GOAL_DAILY_CAPACITY_EXCEEDED,
                needed_minutes=duration,
                available_minutes=goal_best_free,
                message=(
                    f"goal {task.goal_id} has less than {duration} minutes "
                    f"left on this day (cap "
                    f"{context.max_daily_minutes_per_goal})"
                ),
            )
        if best_free < duration:
            code = (
                "OCCURRENCE_DAY_CAPACITY"
                if is_occurrence
                else "FIXED_EVENT_CONFLICT"
                if fixed_blocked
                else "CONTIGUOUS_SLOT_TOO_SHORT"
            )
            return SchedulingFailure(
                code=code,
                needed_minutes=duration,
                available_minutes=best_free,
                message="no contiguous slot large enough",
            )
        if capacity_blocked:
            return SchedulingFailure(
                code="DAILY_CAPACITY_EXCEEDED",
                needed_minutes=duration,
                available_minutes=best_free,
                message="remaining daily capacity is insufficient",
            )
        return SchedulingFailure(
            code="NO_AVAILABLE_SLOT",
            needed_minutes=duration,
            available_minutes=best_free,
            message="no feasible slot found",
        )

    def _first_slot(
        self,
        day: date,
        task: Task,
        duration: int,
        context: RuleContext,
        placed_on_day: list[ScheduledTask],
    ) -> time | None:
        """Earliest slot (on ``slot_minutes`` boundaries) that satisfies the
        window, the buffer and the non-consecutive HIGH spacing rule."""
        start_bound = _to_minutes(context.day_start)
        not_before = context.not_before.get(day)
        if not_before is not None:
            start_bound = max(start_bound, _to_minutes(not_before))
        end_bound = _to_minutes(context.day_end)
        step = self.config.slot_minutes
        # Round "now" up to the next slot boundary instead of starting at an
        # arbitrary minute such as 15:07.
        if start_bound % step:
            start_bound += step - (start_bound % step)
        k = 0
        while start_bound + k * step + duration <= end_bound:
            slot = start_bound + k * step
            if self._slot_ok(slot, slot + duration, task, placed_on_day, context, day):
                return _from_minutes(slot)
            k += 1
        return None

    # -- soft time preferences -------------------------------------------
    @staticmethod
    def _parse_clock(value: str) -> time | None:
        try:
            hour, minute = value.strip().split(":", 1)
            return time(int(hour), int(minute))
        except (TypeError, ValueError):
            return None

    @classmethod
    def _parse_window(cls, raw: str | None) -> tuple[time, time] | None:
        if not raw:
            return None
        key = raw.strip().lower()
        if key in _TIME_OF_DAY_WINDOWS:
            return _TIME_OF_DAY_WINDOWS[key]
        if "-" in raw:
            start_raw, end_raw = raw.split("-", 1)
            start = cls._parse_clock(start_raw)
            end = cls._parse_clock(end_raw)
            if start is not None and end is not None and end > start:
                return start, end
        return None

    @classmethod
    def _preferred_window_for(
        cls, task: Task, context: RuleContext
    ) -> tuple[time, time]:
        raw = context.preferred_time_slots.get(task.cognitive_load.value)
        if raw is None:
            raw = context.preferred_time_slots.get("default")
        window = cls._parse_window(raw)
        if window is not None:
            return window
        return _DEFAULT_LOAD_WINDOWS.get(
            task.cognitive_load, _TIME_OF_DAY_WINDOWS["afternoon"]
        )

    @staticmethod
    def _soft_score(
        slot: int,
        duration: int,
        task: Task,
        placed_on_day: list[ScheduledTask],
        window_start: int,
        window_end: int,
        series_start: int | None,
    ) -> int:
        """Rank a legal slot. Lower is better; hard constraints already passed."""
        score = 0
        if slot < window_start:
            score += 2 * (window_start - slot)
        elif slot + duration > window_end:
            score += 2 * ((slot + duration) - window_end)
        if series_start is not None:
            # Strong stability for a recurring habit, but not a hard constraint.
            score += 4 * (abs(slot - series_start) // 15)
        if placed_on_day:
            same_load = [
                placed
                for placed in placed_on_day
                if placed.cognitive_load == task.cognitive_load
            ]
            if same_load:
                nearest = min(
                    abs(slot - _to_minutes(placed.start_time))
                    for placed in same_load
                )
                if nearest < 60:
                    score += 60 - nearest
            nearest_any = min(
                abs(slot - _to_minutes(placed.start_time))
                for placed in placed_on_day
            )
            if nearest_any < 30:
                score += 30 - nearest_any
        return score

    def _best_slot(
        self,
        day: date,
        task: Task,
        duration: int,
        context: RuleContext,
        placed_on_day: list[ScheduledTask],
        series_time: dict[str, time],
    ) -> time | None:
        """Best legal slot on this day under soft time preferences."""
        start_bound = _to_minutes(context.day_start)
        not_before = context.not_before.get(day)
        if not_before is not None:
            start_bound = max(start_bound, _to_minutes(not_before))
        end_bound = _to_minutes(context.day_end)
        step = self.config.slot_minutes
        if start_bound % step:
            start_bound += step - (start_bound % step)

        window_start, window_end = self._preferred_window_for(task, context)
        window_start_min = _to_minutes(window_start)
        window_end_min = _to_minutes(window_end)
        series_start = (
            series_time.get(task.series_id) if task.series_id is not None else None
        )
        series_start_min = (
            _to_minutes(series_start) if series_start is not None else None
        )

        best_slot: int | None = None
        best_score: int | None = None
        k = 0
        while start_bound + k * step + duration <= end_bound:
            slot = start_bound + k * step
            if self._slot_ok(
                slot, slot + duration, task, placed_on_day, context, day
            ):
                score = self._soft_score(
                    slot,
                    duration,
                    task,
                    placed_on_day,
                    window_start_min,
                    window_end_min,
                    series_start_min,
                )
                if (
                    best_score is None
                    or score < best_score
                    or (
                        score == best_score
                        and (best_slot is None or slot < best_slot)
                    )
                ):
                    best_slot = slot
                    best_score = score
            k += 1
        return _from_minutes(best_slot) if best_slot is not None else None

    @staticmethod
    def _fixed_minutes_on(day: date, context: RuleContext) -> int:
        """Minutes covered by fixed events inside the usable daily window."""
        if not context.fixed_events:
            return 0
        window_start = _to_minutes(context.day_start)
        window_end = _to_minutes(context.day_end)
        total = 0
        for event in context.fixed_events:
            if event.date != day:
                continue
            start = max(window_start, _to_minutes(event.start_time))
            end = min(window_end, _to_minutes(event.end_time))
            if end > start:
                total += end - start
        return total

    @staticmethod
    def _slot_ok(
        slot: int,
        end: int,
        task: Task,
        placed_on_day: list[ScheduledTask],
        context: RuleContext,
        day: date,
    ) -> bool:
        # A fixed event is immovable: reject any overlapping slot outright.
        for event in context.fixed_events:
            if event.date != day:
                continue
            if slot < _to_minutes(event.end_time) and _to_minutes(event.start_time) < end:
                return False

        ordered = sorted(placed_on_day, key=lambda t: t.start_time)
        prev_task: ScheduledTask | None = None
        nxt_task: ScheduledTask | None = None
        for placed in ordered:
            p_start = _to_minutes(placed.start_time)
            p_end = _to_minutes(placed.end_time)
            if p_end <= slot:
                prev_task = placed
            elif p_start >= end:
                nxt_task = placed
                break
            else:
                # Overlaps the candidate slot (neither fully before nor after).
                return False

        buffer = context.buffer_minutes
        if prev_task is not None and slot - _to_minutes(prev_task.end_time) < buffer:
            return False
        if nxt_task is not None and _to_minutes(nxt_task.start_time) - end < buffer:
            return False

        if task.cognitive_load == CognitiveLoad.HIGH:
            if (
                prev_task is not None
                and prev_task.cognitive_load == CognitiveLoad.HIGH
                and slot - _to_minutes(prev_task.end_time) < HIGH_GAP_MINUTES
            ):
                return False
            if (
                nxt_task is not None
                and nxt_task.cognitive_load == CognitiveLoad.HIGH
                and _to_minutes(nxt_task.start_time) - end < HIGH_GAP_MINUTES
            ):
                return False
        return True

    @staticmethod
    def _subject_conflicts(
        day: date,
        subject: str | None,
        context: RuleContext,
        placements: dict[date, list[ScheduledTask]],
    ) -> bool:
        if subject is None:
            return False
        subject_norm = subject.strip().lower()
        pairs = {
            (a.strip().lower(), b.strip().lower())
            for a, b in context.conflicting_subject_pairs
        }
        for placed in placements.get(day, []):
            other = context.task_subjects.get(placed.task_id)
            if other is None:
                continue
            other_norm = other.strip().lower()
            if (subject_norm, other_norm) in pairs or (
                other_norm,
                subject_norm,
            ) in pairs:
                return True
        return False