"""Regression tests for deterministic long-term recurrence materialization.

Covers the P0 scenarios: cross-month daily, the full 2026-10-26 -> 2027-07-01
lifecycle, one-off, finite project, weekly, capacity, boundaries and the
series-consistency rule.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pytest

from app.agent.nodes._shared import drafts_to_tasks
from app.agent.schemas import (
    AnalyzedGoal,
    GoalAnalysisResult,
    GoalKind,
    RecurrenceSpec,
    WorkUnit,
)
from app.agent.state import GoalInput
from app.agent.tools.plan_drafter import (
    PlanDrafterInput,
    PlanDrafterMode,
    PlanDrafterTool,
)
from app.domain.models import Task
from app.domain.models.enums import GoalType, TaskKind
from app.domain.recurrence import (
    RecurrenceError,
    RecurrenceFrequency,
    SeriesSpec,
)
from app.domain.rules.base import RuleContext
from app.domain.rules.recurrence_consistency import RecurrenceConsistencyRule
from app.domain.scheduling.schedule_result import CandidateSchedule, ScheduledTask
from app.domain.scheduling.scheduler import Scheduler

LONG_START = date(2026, 10, 26)
LONG_END = date(2027, 7, 1)


def _item(total: int = 420) -> dict:
    return {
        "title": "背考研英语单词",
        "learning_content": "背单词",
        "subtasks": ["过一遍词表"],
        "video_minutes": 0,
        "reading_minutes": 0,
        "practice_minutes": total,
        "total_minutes": total,
        "difficulty": 2.0,
        "cognitive_load": "medium",
    }


def _analysis(
    *,
    goal_kind: GoalKind,
    recurrence: RecurrenceSpec | None = None,
    work_units: list[WorkUnit] | None = None,
) -> GoalAnalysisResult:
    return GoalAnalysisResult(
        goals=[
            AnalyzedGoal(
                goal_id=1,
                title="目标",
                goal_kind=goal_kind,
                recurrence=recurrence,
                work_units=work_units or [],
            )
        ]
    )


def _payload(
    goal: GoalInput,
    *,
    analysis: GoalAnalysisResult | None = None,
    start: date | None = None,
    end: date | None = None,
) -> PlanDrafterInput:
    return PlanDrafterInput(
        mode=PlanDrafterMode.INITIAL,
        goals=[goal],
        goal_analysis=analysis,
        theoretical={"items": [_item()]},
        start_date=start or goal.start_date or LONG_START,
        end_date=end or (goal.deadline.date() if goal.deadline else LONG_END),
    )


def _run(payload: PlanDrafterInput):
    return PlanDrafterTool(None).run(payload)


def _context_for(tasks: list[Task], *, today: date | None = None) -> RuleContext:
    return RuleContext(
        daily_limit_minutes=300,
        buffer_minutes=15,
        high_cognitive_max_per_day=2,
        available_minutes_per_day=480,
        day_start=time(8, 0),
        day_end=time(22, 0),
        # Fixed-date tests must not depend on the wall clock: an occurrence whose
        # own day is "yesterday" is legitimately unschedulable in production.
        today=today,
        task_earliest_dates={
            task.id: task.occurrence_date
            for task in tasks
            if task.id is not None and task.occurrence_date is not None
        },
        task_deadlines={
            task.id: task.occurrence_date
            for task in tasks
            if task.id is not None and task.occurrence_date is not None
        },
    )


# ---------------------------------------------------------------------------
# 1. Cross-month daily
# ---------------------------------------------------------------------------
def test_cross_month_daily_goal_gets_one_occurrence_per_day() -> None:
    start = date(2026, 10, 26)
    end = date(2026, 11, 5)
    goal = GoalInput(
        title="背诵考研英语单词",
        task_kind=TaskKind.ROUTINE,
        start_date=start,
        deadline=datetime.combine(end, time.max),
        daily_target_minutes=20,
    )

    result = _run(_payload(goal, start=start, end=end))
    drafts = result.tasks

    expected = [start + timedelta(days=offset) for offset in range(11)]
    assert [draft.occurrence_date for draft in drafts] == expected
    assert len({draft.occurrence_date for draft in drafts}) == 11
    assert result.series_specs == [
        SeriesSpec(
            series_id="goal-1-routine",
            start_date=start,
            end_date=end,
            frequency=RecurrenceFrequency.DAILY,
            interval=1,
            weekdays=[],
        )
    ]

    tasks = drafts_to_tasks(drafts)
    schedule = Scheduler().schedule(tasks, _context_for(tasks, today=start))
    assert schedule.unscheduled_task_ids == []
    assert [task.scheduled_date for task in schedule.tasks] == expected
    assert {task.scheduled_date for task in schedule.tasks} != {start}


# ---------------------------------------------------------------------------
# 2. Long span: full lifecycle to 2027-07-01
# ---------------------------------------------------------------------------
def test_long_span_goal_covers_the_full_end_date() -> None:
    goal = GoalInput(
        title="每天背考研英语单词",
        start_date=LONG_START,
        deadline=datetime.combine(LONG_END, time.max),
        daily_target_minutes=20,
    )
    # The semantic classification comes from goal_analysis; no task_kind needed.
    analysis = _analysis(
        goal_kind=GoalKind.RECURRING,
        recurrence=RecurrenceSpec(frequency=RecurrenceFrequency.DAILY),
    )

    result = _run(_payload(goal, analysis=analysis))
    drafts = result.tasks
    dates = [draft.occurrence_date for draft in drafts]

    assert len(drafts) == 249
    assert dates[0] == LONG_START
    assert dates[-1] == LONG_END
    assert len(set(dates)) == 249
    assert result.series_specs[0].end_date == LONG_END
    # No "Day N" title enumeration is needed or produced by deterministic code.
    assert {draft.title for draft in drafts} == {"背考研英语单词"}


def test_llm_classification_without_task_kind_is_enough() -> None:
    """A goal created from free text (no task_kind) must still recur."""
    goal = GoalInput(
        title="每天背考研英语单词",
        goal_type=GoalType.OTHER,
        start_date=LONG_START,
        deadline=datetime.combine(LONG_END, time.max),
        daily_target_minutes=20,
    )
    analysis = _analysis(
        goal_kind=GoalKind.RECURRING,
        recurrence=RecurrenceSpec(frequency="daily"),
    )

    drafts = _run(_payload(goal, analysis=analysis)).tasks

    assert len(drafts) == 249
    assert drafts[0].occurrence_date == LONG_START
    assert drafts[-1].occurrence_date == LONG_END


# ---------------------------------------------------------------------------
# 3. One-off
# ---------------------------------------------------------------------------
def test_one_off_goal_is_not_turned_into_recurrence() -> None:
    goal = GoalInput(
        title="10月30日前完成实验报告",
        goal_type=GoalType.SHORT_TERM,
        deadline=datetime.combine(date(2026, 10, 30), time.max),
    )
    analysis = _analysis(goal_kind=GoalKind.ONE_OFF)

    result = _run(_payload(goal, analysis=analysis))
    drafts = result.tasks

    assert len(drafts) == 1
    assert drafts[0].task_kind is TaskKind.ONE_OFF
    assert drafts[0].occurrence_date is None
    assert drafts[0].series_id is None
    assert result.series_specs == []


# ---------------------------------------------------------------------------
# 4. Finite project / curriculum
# ---------------------------------------------------------------------------
def test_project_goal_becomes_finite_work_units_not_daily_copies() -> None:
    topics = ["极限", "导数", "微分", "积分", "多元函数"]
    goal = GoalInput(
        title="学完高等数学",
        goal_type=GoalType.LONG_TERM,
        task_kind=TaskKind.LONG_TERM,
        start_date=LONG_START,
        deadline=datetime.combine(LONG_END, time.max),
        estimated_minutes=600,
    )
    analysis = _analysis(
        goal_kind=GoalKind.PROJECT,
        work_units=[
            WorkUnit(title=topic, estimated_minutes=120) for topic in topics
        ],
    )

    drafts = _run(_payload(goal, analysis=analysis)).tasks

    assert [draft.title for draft in drafts] == topics
    assert len(drafts) == len(topics)
    assert all(draft.occurrence_date is None for draft in drafts)
    assert all(draft.task_kind is TaskKind.ONE_OFF for draft in drafts)
    assert {draft.series_id for draft in drafts} == {"goal-1-project"}
    # The original bug copied the same task 249 times; this must never happen.
    assert len(drafts) != 249


# ---------------------------------------------------------------------------
# 5. Weekly recurrence
# ---------------------------------------------------------------------------
def test_weekly_goal_lands_on_the_requested_weekday() -> None:
    start = date(2026, 10, 26)  # Monday
    end = date(2026, 12, 31)
    goal = GoalInput(
        title="每周六做一次英语模拟题",
        task_kind=TaskKind.ROUTINE,
        start_date=start,
        deadline=datetime.combine(end, time.max),
        recurrence_weekdays=[5],  # Saturday
    )

    drafts = _run(_payload(goal, start=start, end=end)).tasks
    dates = [draft.occurrence_date for draft in drafts]

    assert dates[0] == date(2026, 10, 31)
    assert all(day is not None and day.weekday() == 5 for day in dates)
    assert all(day <= end for day in dates)


# ---------------------------------------------------------------------------
# 6. Capacity
# ---------------------------------------------------------------------------
def test_recurring_occurrences_never_move_and_respect_daily_capacity() -> None:
    start = date.today() + timedelta(days=1)
    end = start + timedelta(days=6)
    goal = GoalInput(
        title="每日背单词",
        task_kind=TaskKind.ROUTINE,
        start_date=start,
        deadline=datetime.combine(end, time.max),
        daily_target_minutes=60,
    )
    drafts = _run(_payload(goal, start=start, end=end)).tasks
    tasks = drafts_to_tasks(drafts)

    # A 90-minute one-off on the first occurrence day competes for capacity.
    extra = Task(
        id=len(tasks) + 1,
        plan_id=0,
        title="实验报告",
        estimated_duration=90,
        occurrence_date=None,
    )
    tasks.append(extra)
    context = _context_for(tasks)
    context = context.model_copy(
        update={
            "daily_limit_minutes": 120,
            "available_minutes_per_day": 120,
            "task_earliest_dates": {
                **context.task_earliest_dates,
                extra.id: start,
            },
            "task_deadlines": {
                **context.task_deadlines,
                extra.id: start,
            },
        }
    )

    schedule = Scheduler().schedule(tasks, context)

    assert all(
        minutes <= 120 for minutes in schedule.daily_minutes().values()
    )
    for placed in schedule.tasks:
        if placed.occurrence_date is not None:
            assert placed.scheduled_date == placed.occurrence_date
    # Capacity can leave work unplaced, but it must never move an occurrence.
    assert schedule.unscheduled_task_ids


# ---------------------------------------------------------------------------
# 7. Boundaries and fail-closed expansion
# ---------------------------------------------------------------------------
def test_single_day_boundary_is_inclusive() -> None:
    day = date(2026, 10, 26)
    goal = GoalInput(
        title="一天任务",
        task_kind=TaskKind.ROUTINE,
        start_date=day,
        deadline=datetime.combine(day, time.max),
        daily_target_minutes=20,
    )

    drafts = _run(_payload(goal, start=day, end=day)).tasks

    assert len(drafts) == 1
    assert drafts[0].occurrence_date == day


def test_invalid_range_fails_closed_in_the_drafter() -> None:
    goal = GoalInput(
        title="倒序",
        task_kind=TaskKind.ROUTINE,
        start_date=date(2026, 11, 5),
        deadline=datetime.combine(date(2026, 10, 26), time.max),
    )

    with pytest.raises(RecurrenceError):
        _run(_payload(goal, start=date(2026, 11, 5), end=date(2026, 10, 26)))


# ---------------------------------------------------------------------------
# 8. Series consistency rule
# ---------------------------------------------------------------------------
def _placed(
    task_id: int,
    day: date,
    *,
    occurrence: date | None = None,
    series_id: str | None = "s1",
) -> ScheduledTask:
    return ScheduledTask(
        task_id=task_id,
        title="task",
        scheduled_date=day,
        start_time=time(9, 0),
        end_time=time(10, 0),
        duration_minutes=60,
        series_id=series_id,
        occurrence_date=occurrence,
    )


def _schedule(*tasks: ScheduledTask) -> CandidateSchedule:
    days = [task.scheduled_date for task in tasks] or [date(2026, 10, 26)]
    return CandidateSchedule(
        start_date=min(days),
        end_date=max(days),
        tasks=list(tasks),
    )


def test_rule_flags_duplicate_occurrences() -> None:
    day = date(2026, 10, 26)
    schedule = _schedule(_placed(1, day, occurrence=day), _placed(2, day, occurrence=day))
    violations = RecurrenceConsistencyRule().validate(schedule, RuleContext())

    assert "recurrence_duplicate" in {v.code for v in violations}


def test_rule_flags_wrong_day_occurrences() -> None:
    day = date(2026, 10, 26)
    schedule = _schedule(_placed(1, day + timedelta(days=1), occurrence=day))
    violations = RecurrenceConsistencyRule().validate(schedule, RuleContext())

    assert "recurrence_wrong_day" in {v.code for v in violations}


def test_rule_flags_incomplete_series() -> None:
    start = date(2026, 10, 26)
    end = date(2026, 10, 28)
    schedule = _schedule(_placed(1, start, occurrence=start))
    context = RuleContext(
        series_specs={
            "s1": SeriesSpec(
                series_id="s1",
                start_date=start,
                end_date=end,
                frequency=RecurrenceFrequency.DAILY,
            )
        },
        series_occurrences={"s1": {start}},  # missing 10-27 and 10-28
    )

    violations = RecurrenceConsistencyRule().validate(schedule, context)

    assert "recurrence_incomplete" in {v.code for v in violations}


def test_rule_accepts_a_complete_series() -> None:
    start = date(2026, 10, 26)
    end = date(2026, 10, 27)
    schedule = _schedule(
        _placed(1, start, occurrence=start),
        _placed(2, end, occurrence=end),
    )
    context = RuleContext(
        series_specs={
            "s1": SeriesSpec(
                series_id="s1",
                start_date=start,
                end_date=end,
                frequency=RecurrenceFrequency.DAILY,
            )
        },
        series_occurrences={"s1": {start, end}},
    )

    assert RecurrenceConsistencyRule().validate(schedule, context) == []
