"""Heuristic, deterministic scheduler - NO LLM calls allowed.

Algorithm (documented heuristic)
--------------------------------
1. Drop tasks in ``context.completed_task_ids``.
2. Order the rest by ``priority`` desc, then "deadline-having tasks first" and
   ``deadline`` asc, then cognitive load (HIGH first), then ``order_index``.
3. Build a finite horizon: ``start_date = today``, ``end_date = max(latest
   deadline, start + default_horizon_days)`` (always >= start).
4. Greedily place each task on the *first* day where every hard constraint
   holds; within that day take the *first* slot on ``slot_minutes`` boundaries
   that satisfies:
   * remaining capacity = ``min(daily_limit_minutes, available_minutes_per_day)``;
   * buffer ``>= context.buffer_minutes`` to both neighbouring tasks;
   * high-cognitive daily cap ``context.high_cognitive_max_per_day``;
   * conflicting-subject pairs (case-insensitive);
   * the ``[day_start, day_end]`` window;
   * the 30-minute non-consecutive HIGH spacing rule, so the candidate is more
     likely to pass the rule engine unchanged.
5. Earliest slot wins; because HIGH tasks sort first and slots are scanned
   earliest-first, HIGH tasks are naturally biased toward the morning.
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
from app.domain.scheduling.schedule_result import CandidateSchedule, ScheduledTask

#: Default horizon length (days past ``start_date``) when no deadline is longer.
DEFAULT_HORIZON_DAYS = 14
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


def default_horizon(
    tasks: list[Task],
    context: RuleContext,
    *,
    today: date | None = None,
) -> tuple[date, date]:
    """Compute the scheduling horizon for a task set.

    ``start_date`` is ``today`` (or ``datetime.date.today()`` when omitted);
    ``end_date`` is ``max(latest deadline, start + default_horizon_days)``,
    guaranteed never to be before ``start_date``.
    """
    start = today or date.today()
    end = start + timedelta(days=DEFAULT_HORIZON_DAYS)
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
        start_date, end_date = self.default_horizon(tasks, context)

        # (1) skip completed tasks; ids are required to place a task.
        eligible = [
            t for t in tasks if t.id is not None and t.id not in context.completed_task_ids
        ]

        # (2) deterministic priority order.
        ordered = sorted(eligible, key=lambda t: self._sort_key_for(t, context))

        placements: dict[date, list[ScheduledTask]] = {}
        day_minutes: dict[date, int] = {}
        day_high_count: dict[date, int] = {}
        scheduled: list[ScheduledTask] = []
        unscheduled: list[int] = []

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
            )
            if day is None:
                unscheduled.append(task.id)
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
            )
            placements.setdefault(day, []).append(placed)
            day_minutes[day] = day_minutes.get(day, 0) + duration
            if task.cognitive_load == CognitiveLoad.HIGH:
                day_high_count[day] = day_high_count.get(day, 0) + 1
            scheduled.append(placed)

        return CandidateSchedule(
            start_date=start_date,
            end_date=end_date,
            tasks=sorted(scheduled, key=lambda t: (t.scheduled_date, t.start_time)),
            unscheduled_task_ids=unscheduled,
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
    ) -> tuple[date | None, time | None]:
        capacity = min(
            context.daily_limit_minutes, context.available_minutes_per_day
        )
        high_cap = context.high_cognitive_max_per_day
        task_subject = context.task_subjects.get(task.id)
        is_high = task.cognitive_load == CognitiveLoad.HIGH

        span = (end_date - start_date).days
        for offset in range(span + 1):
            day = start_date + timedelta(days=offset)

            if day_minutes.get(day, 0) + duration > capacity:
                continue
            if is_high and day_high_count.get(day, 0) >= high_cap:
                continue
            if self._subject_conflicts(day, task_subject, context, placements):
                continue

            slot_start = self._first_slot(
                day, task, duration, context, placements.get(day, [])
            )
            if slot_start is not None:
                return day, slot_start
        return None, None

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
        end_bound = _to_minutes(context.day_end)
        step = self.config.slot_minutes
        k = 0
        while start_bound + k * step + duration <= end_bound:
            slot = start_bound + k * step
            if self._slot_ok(slot, slot + duration, task, placed_on_day, context):
                return _from_minutes(slot)
            k += 1
        return None

    @staticmethod
    def _slot_ok(
        slot: int,
        end: int,
        task: Task,
        placed_on_day: list[ScheduledTask],
        context: RuleContext,
    ) -> bool:
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


def schedule_tasks(
    tasks: list[Task],
    context: RuleContext,
    config: SchedulerConfig | None = None,
) -> CandidateSchedule:
    """Convenience wrapper: ``Scheduler(config).schedule(tasks, context)``."""
    return Scheduler(config).schedule(tasks, context)