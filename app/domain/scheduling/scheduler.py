"""Heuristic, deterministic scheduler - NO LLM calls allowed.

Algorithm (documented heuristic)
--------------------------------
1. Drop tasks in context.completed_task_ids.
2. Daily base capacity is min(daily_limit_minutes,
   available_minutes_per_day - fixed_event_minutes). daily_limit_minutes stays
   the hard per-day upper bound; fixed events also block slots outright.
3. Pack in this order (each day keeps a burst reserve free):
   pinned tasks (is_flexible=False), long-term tasks that reached
   long_term_max_wait_days, remaining long-term tasks (under their daily
   floor), deadline tasks inside deadline_acceleration_days (most urgent
   first), same-day chores (low priority / restorative), then everything else.
4. Greedily place each task on the first feasible day/slot that satisfies the
   hard constraints mirrored by the rule engine: daily capacity, buffer,
   high-cognitive spacing/cap, subject conflicts, fixed events, earliest date
   and the daily window. A future deadline bounds the days a task is tried on;
   an already-overdue deadline keeps the legacy behaviour so the rule engine
   can flag it and plan_repair can act.
5. Tasks that cannot be placed are reported in
   CandidateSchedule.unscheduled_reasons / unscheduled_tasks with a machine
   readable reason (capacity, deadline, long_term_wait, no_slot) instead of
   being silently dropped.

The output is a *candidate*: the rule engine (app.domain.rules) is the only
authority on hard constraints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time, timedelta

from app.domain.models import Task
from app.domain.models.enums import CognitiveLoad, Priority, TaskKind
from app.domain.rules.base import RuleContext
from app.domain.scheduling.constants import DEFAULT_HORIZON_DAYS
from app.domain.scheduling.daily_plan import (
    REASON_CAPACITY,
    REASON_DEADLINE,
    REASON_LONG_TERM_WAIT,
    REASON_NO_SLOT,
    DailyPlan,
    UnscheduledTask,
)
from app.domain.scheduling.schedule_result import CandidateSchedule, ScheduledTask

#: Minimum gap between two consecutive HIGH tasks (mirrors the rule module).
HIGH_GAP_MINUTES = 30
#: Date sentinel used to push deadline-less tasks to the back of the sort.
_FAR_FUTURE = date.max


@dataclass
class SchedulerConfig:
    """Tunables of the heuristic scheduler.

    max_high_cognitive_per_day is informational: the authoritative high-
    cognitive cap always comes from RuleContext.high_cognitive_max_per_day.
    The phase-4 knobs default to the documented values and may be overridden by
    settings when the deployment adds the matching fields.
    """

    day_start: time = time(8, 0)
    day_end: time = time(22, 0)
    slot_minutes: int = 15
    max_high_cognitive_per_day: int = 2
    default_horizon_days: int = DEFAULT_HORIZON_DAYS
    #: Minutes kept free every day for unexpected work before flexible tasks.
    burst_reserve_minutes: int = 60
    #: Daily minutes protected for long-term work when such tasks exist.
    long_term_daily_floor_minutes: int = 30
    #: A deadline inside this many days enters the accelerated packing group.
    deadline_acceleration_days: int = 3
    #: Long-term tasks waiting at least this many days move to the front.
    long_term_max_wait_days: int = 7

    @classmethod
    def from_settings(cls) -> SchedulerConfig:
        """Build the config from defaults plus optional settings overrides.

        The settings fields are looked up defensively so the scheduler keeps
        working on deployments whose Settings predates phase 4.
        """
        from app.core.config import get_settings

        settings = get_settings()
        return cls(
            burst_reserve_minutes=max(
                cls._int_setting(
                    settings,
                    "scheduler_burst_reserve_minutes",
                    "burst_reserve_minutes",
                    default=60,
                ),
                0,
            ),
            long_term_daily_floor_minutes=max(
                cls._int_setting(
                    settings,
                    "scheduler_long_term_daily_floor_minutes",
                    "long_term_daily_floor_minutes",
                    default=30,
                ),
                0,
            ),
            deadline_acceleration_days=max(
                cls._int_setting(
                    settings,
                    "scheduler_deadline_acceleration_days",
                    "deadline_acceleration_days",
                    default=3,
                ),
                0,
            ),
            long_term_max_wait_days=max(
                cls._int_setting(
                    settings,
                    "scheduler_long_term_max_wait_days",
                    "long_term_max_wait_days",
                    default=7,
                ),
                0,
            ),
        )

    @staticmethod
    def _int_setting(
        settings: object, *names: str, default: int
    ) -> int:
        """First defined settings attribute among the accepted field names."""
        for name in names:
            value = getattr(settings, name, None)
            if value is not None:
                return int(value)  # type: ignore[arg-type]
        return default


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


@dataclass
class _PackingState:
    """Mutable bookkeeping for one scheduling run (never leaves the method)."""

    base_capacity: dict[date, int] = field(default_factory=dict)
    placements: dict[date, list[ScheduledTask]] = field(default_factory=dict)
    minutes: dict[date, int] = field(default_factory=dict)
    #: Minutes of pinned (is_flexible=False) tasks per day.
    pinned_minutes: dict[date, int] = field(default_factory=dict)
    #: Minutes of *flexible* long-term tasks per day.
    long_term_minutes: dict[date, int] = field(default_factory=dict)
    has_long_term_tasks: bool = False


def default_horizon(
    tasks: list[Task],
    context: RuleContext,
    *,
    today: date | None = None,
) -> tuple[date, date]:
    """Compute the scheduling horizon for a task set.

    start_date is today (or datetime.date.today() when omitted); end_date is
    max(latest deadline, start + default_horizon_days), guaranteed never to be
    before start_date.
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
        self.config = config if config is not None else SchedulerConfig.from_settings()

    def default_horizon(
        self, tasks: list[Task], context: RuleContext, *, today: date | None = None
    ) -> tuple[date, date]:
        """Instance wrapper around the module-level default_horizon."""
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

        state = _PackingState(
            has_long_term_tasks=any(
                t.task_kind is TaskKind.LONG_TERM for t in eligible
            ),
            base_capacity=self._base_capacities(start_date, end_date, context),
        )

        # (2) deterministic packing order.
        ordered = sorted(
            eligible, key=lambda t: self._sort_key_for(t, context, start_date)
        )

        scheduled: list[ScheduledTask] = []
        unscheduled: list[int] = []
        unscheduled_reasons: dict[int, str] = {}
        unscheduled_tasks: list[UnscheduledTask] = []

        for task in ordered:
            assert task.id is not None  # guaranteed above, keep mypy happy
            duration = task.predicted_duration or task.estimated_duration
            probability = (
                task.completion_probability
                if task.completion_probability is not None
                else 1.0
            )

            day, slot_start = self._first_feasible(
                task, duration, context, start_date, end_date, state
            )
            if day is None:
                reason = self._unscheduled_reason(
                    task, duration, context, start_date, end_date, state
                )
                unscheduled.append(task.id)
                unscheduled_reasons[task.id] = reason
                unscheduled_tasks.append(
                    UnscheduledTask(
                        task_id=task.id,
                        date=self._unscheduled_date(
                            task, context, start_date, end_date
                        ),
                        reason=reason,
                    )
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
            )
            state.placements.setdefault(day, []).append(placed)
            state.minutes[day] = state.minutes.get(day, 0) + duration
            if not task.is_flexible:
                state.pinned_minutes[day] = (
                    state.pinned_minutes.get(day, 0) + duration
                )
            elif task.task_kind is TaskKind.LONG_TERM:
                state.long_term_minutes[day] = (
                    state.long_term_minutes.get(day, 0) + duration
                )
            scheduled.append(placed)

        daily_plans = [
            self._daily_plan(day, context, state)
            for day in (
                start_date + timedelta(days=offset)
                for offset in range((end_date - start_date).days + 1)
            )
        ]

        return CandidateSchedule(
            start_date=start_date,
            end_date=end_date,
            tasks=sorted(scheduled, key=lambda t: (t.scheduled_date, t.start_time)),
            unscheduled_task_ids=unscheduled,
            unscheduled_reasons=unscheduled_reasons,
            unscheduled_tasks=unscheduled_tasks,
            daily_plans=daily_plans,
        )

    # -- internals ---------------------------------------------------------

    def _sort_key_for(
        self,
        task: Task,
        context: RuleContext,
        start_date: date | None = None,
    ) -> tuple[int, date, int, int, int]:
        start = start_date or context.today or date.today()
        task_id = task.id
        deadline = None if task_id is None else context.task_deadlines.get(task_id)
        waited = self._wait_days(task, context, start)
        is_long_term = task.task_kind is TaskKind.LONG_TERM

        if not task.is_flexible:
            group = 0  # pinned work cannot move
        elif is_long_term and waited >= self.config.long_term_max_wait_days:
            group = 1  # waited long enough: jump ahead of other flexible work
        elif is_long_term:
            group = 2  # protect the long-term daily floor
        elif (
            deadline is not None
            and (deadline - start).days <= self.config.deadline_acceleration_days
        ):
            group = 3  # deadline acceleration window
        elif (
            task.priority is Priority.LOW
            or task.cognitive_load is CognitiveLoad.RESTORATIVE
        ):
            group = 4  # same-day chores / light restorative work
        else:
            group = 5

        return (
            group,
            deadline if deadline is not None else _FAR_FUTURE,
            -int(task.priority),
            _COGNITIVE_WEIGHT[task.cognitive_load],
            task.order_index,
        )

    def _wait_days(self, task: Task, context: RuleContext, start: date) -> int:
        """How many days a task has already been waiting (0 when not started)."""
        if task.id is None:
            return 0
        earliest = context.task_earliest_dates.get(task.id)
        if earliest is None:
            return 0
        return max((start - earliest).days, 0)

    def _base_capacities(
        self, start_date: date, end_date: date, context: RuleContext
    ) -> dict[date, int]:
        """Physical per-day capacity after fixed events and the daily limit."""
        return {
            day: self._base_capacity(day, context)
            for day in (
                start_date + timedelta(days=offset)
                for offset in range((end_date - start_date).days + 1)
            )
        }

    def _base_capacity(self, day: date, context: RuleContext) -> int:
        fixed = self._fixed_minutes_on(day, context)
        available = context.available_minutes_per_day - fixed
        return max(min(context.daily_limit_minutes, available), 0)

    def _first_feasible(
        self,
        task: Task,
        duration: int,
        context: RuleContext,
        start_date: date,
        end_date: date,
        state: _PackingState,
    ) -> tuple[date | None, time | None]:
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

        # A future deadline is a hard bound for the scheduler; an overdue one is
        # still attempted so the rule engine can flag it for plan_repair.
        deadline = context.task_deadlines.get(task.id) if task.id is not None else None
        scan_end = end_date
        if deadline is not None and deadline >= start_date:
            scan_end = min(end_date, deadline)
        if scan_start > scan_end:
            return None, None

        span = (scan_end - scan_start).days
        for offset in range(span + 1):
            day = scan_start + timedelta(days=offset)

            if not self._fits_capacity(task, duration, day, state):
                continue
            if is_high and self._high_count(day, state) >= high_cap:
                continue
            if self._subject_conflicts(day, task_subject, context, state.placements):
                continue

            slot_start = self._first_slot(
                day, task, duration, context, state.placements.get(day, [])
            )
            if slot_start is not None:
                return day, slot_start
        return None, None

    def _fits_capacity(
        self,
        task: Task,
        duration: int,
        day: date,
        state: _PackingState,
    ) -> bool:
        """Whether the task fits the day after fixed load, reserve and floor."""
        return self._remaining_minutes(task, day, state) >= duration

    def _remaining_minutes(
        self,
        task: Task,
        day: date,
        state: _PackingState,
    ) -> int:
        """Capacity still usable by this task on the day (reserve included)."""
        base = state.base_capacity.get(day, 0)
        total = state.minutes.get(day, 0)
        if not task.is_flexible:
            return max(base - total, 0)

        reserve = self.config.burst_reserve_minutes
        if task.task_kind is TaskKind.LONG_TERM:
            return max(base - total - reserve, 0)

        pinned = state.pinned_minutes.get(day, 0)
        long_term = state.long_term_minutes.get(day, 0)
        floor = 0
        if state.has_long_term_tasks:
            floor = max(self.config.long_term_daily_floor_minutes, long_term)
        other_flexible = total - pinned - long_term
        limit = max(base - reserve - pinned - floor, 0)
        return max(limit - other_flexible, 0)

    @staticmethod
    def _high_count(day: date, state: _PackingState) -> int:
        return sum(
            1
            for placed in state.placements.get(day, [])
            if placed.cognitive_load == CognitiveLoad.HIGH
        )

    def _first_slot(
        self,
        day: date,
        task: Task,
        duration: int,
        context: RuleContext,
        placed_on_day: list[ScheduledTask],
    ) -> time | None:
        """Earliest slot on slot_minutes boundaries that satisfies the window,
        the buffer and the non-consecutive HIGH spacing rule."""
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

    # -- reporting ---------------------------------------------------------

    def _daily_plan(
        self, day: date, context: RuleContext, state: _PackingState
    ) -> DailyPlan:
        capacity = state.base_capacity.get(day, 0)
        placed = sorted(
            state.placements.get(day, []),
            key=lambda item: (item.start_time, item.task_id),
        )
        reasons = [
            f"daily_limit={context.daily_limit_minutes}",
            f"available={context.available_minutes_per_day}",
        ]
        fixed = self._fixed_minutes_on(day, context)
        if fixed:
            reasons.append(f"fixed_events={fixed}")
        if self.config.burst_reserve_minutes:
            reasons.append(f"burst_reserve={self.config.burst_reserve_minutes}")
        if state.has_long_term_tasks and self.config.long_term_daily_floor_minutes:
            reasons.append(
                f"long_term_floor={self.config.long_term_daily_floor_minutes}"
            )
        if capacity <= 0:
            reasons.append("no_capacity")
        return DailyPlan(
            date=day,
            capacity_minutes=capacity,
            used_minutes=sum(item.duration_minutes for item in placed),
            task_ids=[item.task_id for item in placed],
            reasons=reasons,
        )

    def _unscheduled_reason(
        self,
        task: Task,
        duration: int,
        context: RuleContext,
        start_date: date,
        end_date: date,
        state: _PackingState,
    ) -> str:
        task_id = task.id
        earliest = (
            context.task_earliest_dates.get(task_id, start_date)
            if task_id is not None
            else start_date
        )
        scan_start = max(start_date, earliest)
        deadline = context.task_deadlines.get(task_id) if task_id is not None else None
        horizon_end = end_date
        if deadline is not None and deadline >= start_date:
            horizon_end = min(end_date, deadline)
        if scan_start > horizon_end:
            return REASON_DEADLINE if deadline is not None else REASON_CAPACITY

        if (
            task.task_kind is TaskKind.LONG_TERM
            and self._wait_days(task, context, start_date)
            >= self.config.long_term_max_wait_days
        ):
            return REASON_LONG_TERM_WAIT

        candidate_days = [
            scan_start + timedelta(days=offset)
            for offset in range((horizon_end - scan_start).days + 1)
        ]
        # A future deadline that excluded days which still have room is the
        # reason, not raw capacity.
        if deadline is not None and start_date <= deadline < end_date:
            later_days = [
                deadline + timedelta(days=offset)
                for offset in range(1, (end_date - deadline).days + 1)
            ]
            if any(
                self._remaining_minutes(task, day, state) >= duration
                for day in later_days
            ):
                return REASON_DEADLINE

        if not any(
            self._remaining_minutes(task, day, state) >= duration
            for day in candidate_days
        ):
            return REASON_CAPACITY
        return REASON_NO_SLOT

    def _unscheduled_date(
        self,
        task: Task,
        context: RuleContext,
        start_date: date,
        end_date: date,
    ) -> date:
        """Last day the scheduler considered before giving up."""
        task_id = task.id
        deadline = context.task_deadlines.get(task_id) if task_id is not None else None
        if deadline is not None and deadline >= start_date:
            return min(end_date, deadline)
        return end_date
