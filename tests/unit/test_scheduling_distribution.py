"""Scheduling distribution, proactive chunking and soft time preferences."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta

from app.agent.nodes._shared import build_rule_context
from app.agent.schemas import GeneratedTaskDraft, PlanGenerationResult
from app.agent.state import GoalInput, PlannerRequest
from app.agent.tools.execution_chunker import chunk_long_drafts
from app.domain.models import Task
from app.domain.models.enums import CognitiveLoad, PlanningMode, Priority, TaskKind
from app.domain.rules.base import RuleContext
from app.domain.scheduling.scheduler import Scheduler

START = date(2026, 10, 26)


def _draft(
    title: str,
    minutes: int,
    *,
    goal_id: int,
    load: CognitiveLoad,
    occurrence: date | None = None,
    series_id: str | None = None,
    work_unit_key: str | None = None,
) -> GeneratedTaskDraft:
    return GeneratedTaskDraft(
        title=title,
        goal_id=goal_id,
        estimated_duration=minutes,
        cognitive_load=load,
        priority=Priority.MEDIUM,
        task_kind=TaskKind.ROUTINE if occurrence else TaskKind.ONE_OFF,
        series_id=series_id,
        occurrence_date=occurrence,
        work_unit_key=work_unit_key,
    )


def _tasks_from_drafts(drafts: list[GeneratedTaskDraft]) -> list[Task]:
    return [
        Task(
            id=draft.order_index + 1,
            plan_id=0,
            title=draft.title,
            goal_id=draft.goal_id,
            estimated_duration=draft.estimated_duration,
            cognitive_load=draft.cognitive_load,
            priority=draft.priority,
            task_kind=draft.task_kind,
            series_id=draft.series_id,
            occurrence_date=draft.occurrence_date,
            work_unit_key=draft.work_unit_key,
            chunk_index=draft.chunk_index,
            order_index=draft.order_index,
        )
        for draft in drafts
    ]


def _context(
    *,
    start: date,
    end: date,
    preferred_time_slots: dict[str, str] | None = None,
    fixed_events=None,
    high_cap: int = 2,
) -> RuleContext:
    return RuleContext(
        daily_limit_minutes=300,
        available_minutes_per_day=480,
        buffer_minutes=15,
        high_cognitive_max_per_day=high_cap,
        day_start=time(8, 0),
        day_end=time(22, 0),
        today=start,
        schedule_start=start,
        schedule_end=end,
        preferred_time_slots=preferred_time_slots or {},
        fixed_events=fixed_events or [],
    )


def test_long_project_units_are_proactively_chunked_with_exact_totals() -> None:
    drafts = [
        _draft(
            "math high",
            300,
            goal_id=2,
            load=CognitiveLoad.HIGH,
            work_unit_key="wg-2-project-0",
        ),
        _draft(
            "math medium",
            300,
            goal_id=2,
            load=CognitiveLoad.MEDIUM,
            work_unit_key="wg-2-project-1",
        ),
        _draft(
            "vocab",
            20,
            goal_id=1,
            load=CognitiveLoad.MEDIUM,
            occurrence=START,
            series_id="goal-1-routine",
        ),
    ]

    chunks = chunk_long_drafts(
        drafts, daily_limit_minutes=300, available_minutes_per_day=480
    )

    assert chunks is not None
    high = [d for d in chunks if d.work_unit_key == "wg-2-project-0"]
    medium = [d for d in chunks if d.work_unit_key == "wg-2-project-1"]
    vocab = [d for d in chunks if d.occurrence_date is not None]

    assert [d.estimated_duration for d in high] == [100, 100, 100]
    assert [d.estimated_duration for d in medium] == [75, 75, 75, 75]
    assert sum(d.estimated_duration for d in high) == 300
    assert sum(d.estimated_duration for d in medium) == 300
    assert len(vocab) == 1 and vocab[0].estimated_duration == 20
    assert all(d.parent_key for d in high + medium)
    assert [d.chunk_index for d in high] == [0, 1, 2]
    assert [d.chunk_index for d in medium] == [0, 1, 2, 3]


def test_proactive_chunks_distribute_project_work_before_series_end() -> None:
    english = [
        _draft(
            "vocab",
            20,
            goal_id=1,
            load=CognitiveLoad.MEDIUM,
            occurrence=START + timedelta(days=offset),
            series_id="goal-1-routine",
        )
        for offset in range(21)
    ]
    math = [
        _draft(
            "math high",
            300,
            goal_id=2,
            load=CognitiveLoad.HIGH,
            work_unit_key="wg-2-project-0",
        ),
        _draft(
            "math medium",
            300,
            goal_id=2,
            load=CognitiveLoad.MEDIUM,
            work_unit_key="wg-2-project-1",
        ),
    ]
    drafts = chunk_long_drafts(
        english + math, daily_limit_minutes=300, available_minutes_per_day=480
    )
    assert drafts is not None
    tasks = _tasks_from_drafts(drafts)
    earliest = {
        task.id: task.occurrence_date
        for task in tasks
        if task.occurrence_date is not None
    }
    last_english = max(earliest.values())
    context = _context(start=START, end=last_english)
    context = context.model_copy(
        update={
            "task_earliest_dates": earliest,
            "task_deadlines": dict(earliest),
        }
    )

    schedule = Scheduler().schedule(tasks, context)

    assert schedule.unscheduled_task_ids == []
    english_placed = [t for t in schedule.tasks if t.series_id is not None]
    math_placed = [t for t in schedule.tasks if t.goal_id == 2]
    assert len(english_placed) == 21
    assert len(math_placed) == 7
    assert sorted({t.scheduled_date for t in math_placed})[-1] <= last_english
    assert all(t.start_time != time(8, 0) for t in schedule.tasks)

    daily_minutes = Counter()
    high_count = Counter()
    by_day: dict[date, list] = {}
    for placed in schedule.tasks:
        daily_minutes[placed.scheduled_date] += placed.duration_minutes
        by_day.setdefault(placed.scheduled_date, []).append(placed)
        if placed.cognitive_load == CognitiveLoad.HIGH:
            high_count[placed.scheduled_date] += 1
    assert max(daily_minutes.values()) <= 300
    assert max(high_count.values(), default=0) <= 2
    for placed in by_day.values():
        ordered = sorted(placed, key=lambda item: item.start_time)
        for left, right in zip(ordered, ordered[1:], strict=False):
            left_end = left.start_time.hour * 60 + left.start_time.minute + left.duration_minutes
            right_start = right.start_time.hour * 60 + right.start_time.minute
            assert right_start - left_end >= 15


def test_occurrence_without_deadline_is_still_day_locked() -> None:
    day = START
    goal = GoalInput(
        title="vocab",
        planning_mode=PlanningMode.RECURRING,
        start_date=day,
        deadline=datetime.combine(day + timedelta(days=3), time.max),
    )
    request = PlannerRequest(
        user_id=1,
        goals=[goal],
        start_date=day,
        end_date=day + timedelta(days=3),
    )
    draft = _draft(
        "vocab",
        20,
        goal_id=1,
        load=CognitiveLoad.MEDIUM,
        occurrence=day,
        series_id="goal-1-routine",
    )
    state = {
        "request": request,
        "goals": [goal],
        "plan_draft": PlanGenerationResult(tasks=[draft]),
    }

    context = build_rule_context(state, [draft])

    assert context.task_earliest_dates[1] == day
    assert context.task_deadlines[1] == day


def test_no_explicit_preference_does_not_cluster_at_0800() -> None:
    tasks = [
        Task(
            id=index + 1,
            plan_id=0,
            title=f"medium {index}",
            estimated_duration=30,
            cognitive_load=CognitiveLoad.MEDIUM,
        )
        for index in range(5)
    ]

    schedule = Scheduler().schedule(tasks, _context(start=START, end=START))

    assert len(schedule.tasks) == 5
    assert all(placed.start_time >= time(9, 0) for placed in schedule.tasks)
    assert all(placed.start_time != time(8, 0) for placed in schedule.tasks)


def test_explicit_preferred_window_is_used_when_legal() -> None:
    task = Task(
        id=1,
        plan_id=0,
        title="evening study",
        estimated_duration=30,
        cognitive_load=CognitiveLoad.MEDIUM,
    )
    context = _context(
        start=START,
        end=START,
        preferred_time_slots={"medium": "evening"},
    )

    schedule = Scheduler().schedule([task], context)

    assert len(schedule.tasks) == 1
    assert schedule.tasks[0].start_time >= time(18, 0)
    assert schedule.tasks[0].end_time <= time(22, 0)


def test_preferred_window_falls_back_to_next_legal_slot() -> None:
    from app.domain.scheduling.schedule_result import FixedEvent

    task = Task(
        id=1,
        plan_id=0,
        title="afternoon study",
        estimated_duration=30,
        cognitive_load=CognitiveLoad.MEDIUM,
    )
    context = _context(
        start=START,
        end=START,
        preferred_time_slots={"medium": "afternoon"},
        fixed_events=[
            FixedEvent(
                date=START,
                start_time=time(12, 30),
                end_time=time(17, 0),
                title="blocked",
            )
        ],
    )

    schedule = Scheduler().schedule([task], context)

    assert len(schedule.tasks) == 1
    placed = schedule.tasks[0]
    assert placed.start_time >= time(17, 0)
    assert not (
        placed.start_time < time(17, 0) and placed.end_time > time(12, 30)
    )


def test_recurring_series_keeps_a_stable_habit_time() -> None:
    tasks = [
        Task(
            id=index + 1,
            plan_id=0,
            title="vocab",
            estimated_duration=20,
            cognitive_load=CognitiveLoad.MEDIUM,
            series_id="goal-1-routine",
            occurrence_date=START + timedelta(days=index),
        )
        for index in range(5)
    ]
    earliest = {task.id: task.occurrence_date for task in tasks}
    context = _context(
        start=START,
        end=START + timedelta(days=4),
        preferred_time_slots={"medium": "evening"},
    ).model_copy(
        update={"task_earliest_dates": earliest, "task_deadlines": dict(earliest)}
    )

    schedule = Scheduler().schedule(tasks, context)

    assert len(schedule.tasks) == 5
    assert {placed.start_time for placed in schedule.tasks} == {time(18, 0)}


def test_high_cognitive_hard_cap_and_spacing_still_win() -> None:
    tasks = [
        Task(
            id=index + 1,
            plan_id=0,
            title=f"high {index}",
            estimated_duration=60,
            cognitive_load=CognitiveLoad.HIGH,
        )
        for index in range(2)
    ]

    schedule = Scheduler().schedule(tasks, _context(start=START, end=START))

    assert len(schedule.tasks) == 2
    ordered = sorted(schedule.tasks, key=lambda item: item.start_time)
    first_end = (
        ordered[0].start_time.hour * 60
        + ordered[0].start_time.minute
        + ordered[0].duration_minutes
    )
    second_start = ordered[1].start_time.hour * 60 + ordered[1].start_time.minute
    assert second_start - first_end >= 30


def test_high_cognitive_cap_leaves_second_task_pending_with_reason() -> None:
    tasks = [
        Task(
            id=index + 1,
            plan_id=0,
            title=f"high {index}",
            estimated_duration=60,
            cognitive_load=CognitiveLoad.HIGH,
        )
        for index in range(2)
    ]

    schedule = Scheduler().schedule(
        tasks, _context(start=START, end=START, high_cap=1)
    )

    assert len(schedule.tasks) == 1
    assert len(schedule.unscheduled_task_ids) == 1
    reason = schedule.unscheduled_reasons[schedule.unscheduled_task_ids[0]]
    assert reason.code in {"HIGH_COGNITIVE_LIMIT", "NO_AVAILABLE_SLOT"}
