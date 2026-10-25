"""Tests for one-off / long-term / routine task splitting.

The split happens in the deterministic ``plan_drafter`` fallback: a long-term
goal with a date range becomes one occurrence per matching day instead of one
giant task, while one-off goals keep the historical single-draft shape.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.agent.nodes._shared import drafts_to_tasks
from app.agent.state import GoalInput
from app.agent.tools.plan_drafter import PlanDrafterInput, PlanDrafterMode, PlanDrafterTool
from app.domain.models.enums import CognitiveLoad, GoalType, Priority, TaskKind
from app.domain.rules.base import RuleContext, RuleEngine
from app.domain.rules.earliest_start import EarliestStartRule
from app.domain.scheduling.schedule_result import CandidateSchedule, ScheduledTask
from app.domain.scheduling.scheduler import Scheduler

MONDAY = date(2026, 1, 5)


def _item(title: str = "高等数学复习", total: int = 420) -> dict:
    return {
        "title": title,
        "learning_content": "看课\n做例题\n做练习",
        "subtasks": ["看课", "做例题", "做练习"],
        "video_minutes": 60,
        "reading_minutes": 60,
        "practice_minutes": 300,
        "total_minutes": total,
        "difficulty": 4.0,
        "cognitive_load": CognitiveLoad.HIGH.value,
    }


def _payload(goal: GoalInput, *, start: date = MONDAY, end: date | None = None) -> PlanDrafterInput:
    return PlanDrafterInput(
        mode=PlanDrafterMode.INITIAL,
        goals=[goal],
        theoretical={"items": [_item()]},
        start_date=start,
        end_date=end or (start + timedelta(days=6)),
    )


def _drafts(payload: PlanDrafterInput):
    return PlanDrafterTool(None).run(payload).tasks


def test_long_term_goal_splits_into_one_occurrence_per_day() -> None:
    goal = GoalInput(
        title="高等数学复习",
        goal_type=GoalType.LONG_TERM,
        start_date=MONDAY,
        deadline=datetime.combine(MONDAY + timedelta(days=6), time.max),
        daily_target_minutes=60,
        subject="math",
        priority=Priority.HIGH,
    )

    drafts = _drafts(_payload(goal))

    assert len(drafts) == 7
    assert {draft.series_id for draft in drafts} == {"goal-1-long_term"}
    assert [draft.series_index for draft in drafts] == list(range(7))
    assert [draft.occurrence_date for draft in drafts] == [
        MONDAY + timedelta(days=offset) for offset in range(7)
    ]
    assert {draft.task_kind for draft in drafts} == {TaskKind.LONG_TERM}
    assert {draft.is_flexible for draft in drafts} == {False}
    # Daily quota, not the whole 420-minute theoretical workload.
    assert {draft.estimated_duration for draft in drafts} == {60}
    assert {draft.predicted_duration for draft in drafts} == {60}
    # The usual standards / subject / priority survive the split.
    assert all(draft.standards == [] for draft in drafts)
    assert {draft.subject for draft in drafts} == {"math"}
    assert {int(draft.priority) for draft in drafts} == {int(Priority.HIGH)}
    assert {draft.order_index for draft in drafts} == set(range(7))


def test_long_term_goal_with_supplement_keeps_substeps() -> None:
    goal = GoalInput(
        title="with supplement",
        description="watch\npractice\nreview",
        goal_type=GoalType.LONG_TERM,
        start_date=MONDAY,
        deadline=datetime.combine(MONDAY + timedelta(days=6), time.max),
        daily_target_minutes=60,
        subject="math",
        priority=Priority.HIGH,
    )

    drafts = _drafts(_payload(goal))

    assert all(draft.standards for draft in drafts)


def test_one_off_goal_stays_a_single_task() -> None:
    goal = GoalInput(
        title="去超市买酱油",
        goal_type=GoalType.SHORT_TERM,
        deadline=datetime.combine(MONDAY + timedelta(days=6), time.max),
    )

    drafts = _drafts(_payload(goal))

    assert len(drafts) == 1
    assert drafts[0].task_kind is TaskKind.ONE_OFF
    assert drafts[0].series_id is None
    assert drafts[0].occurrence_date is None
    # Legacy total (sum of video/reading/practice), not a daily quota.
    assert drafts[0].estimated_duration == 420


def test_recurrence_weekdays_filters_occurrence_days() -> None:
    goal = GoalInput(
        title="健身",
        goal_type=GoalType.HABIT,
        start_date=MONDAY,
        deadline=datetime.combine(MONDAY + timedelta(days=6), time.max),
        recurrence_weekdays=[0, 2, 4],  # Mon / Wed / Fri
    )

    drafts = _drafts(_payload(goal))

    assert [draft.occurrence_date for draft in drafts] == [
        date(2026, 1, 5),
        date(2026, 1, 7),
        date(2026, 1, 9),
    ]
    assert [draft.series_index for draft in drafts] == [0, 1, 2]
    assert {draft.task_kind for draft in drafts} == {TaskKind.ROUTINE}


def test_invalid_range_falls_back_to_one_off() -> None:
    goal = GoalInput(
        title="倒序日期",
        goal_type=GoalType.LONG_TERM,
        start_date=MONDAY + timedelta(days=5),
        deadline=datetime.combine(MONDAY, time.max),
    )

    drafts = _drafts(_payload(goal))

    assert len(drafts) == 1
    assert drafts[0].task_kind is TaskKind.LONG_TERM
    assert drafts[0].series_id is None


def test_explicit_task_kind_overrides_goal_type() -> None:
    goal = GoalInput(
        title="每日阅读",
        goal_type=GoalType.SHORT_TERM,
        task_kind=TaskKind.ROUTINE,
        start_date=MONDAY,
        deadline=datetime.combine(MONDAY + timedelta(days=2), time.max),
    )

    drafts = _drafts(_payload(goal))

    assert len(drafts) == 3
    assert {draft.task_kind for draft in drafts} == {TaskKind.ROUTINE}


def _scheduler_context(tasks) -> RuleContext:
    return RuleContext(
        daily_limit_minutes=300,
        buffer_minutes=15,
        high_cognitive_max_per_day=2,
        available_minutes_per_day=480,
        day_start=time(8, 0),
        day_end=time(22, 0),
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


def test_occurrences_are_scheduled_on_their_own_date() -> None:
    start = date.today()
    goal = GoalInput(
        title="高等数学复习",
        goal_type=GoalType.LONG_TERM,
        start_date=start,
        deadline=datetime.combine(start + timedelta(days=6), time.max),
        daily_target_minutes=60,
        subject="math",
    )
    drafts = _drafts(_payload(goal, start=start, end=start + timedelta(days=6)))
    tasks = drafts_to_tasks(drafts)
    context = _scheduler_context(tasks)

    schedule = Scheduler().schedule(tasks, context)

    assert schedule.unscheduled_task_ids == []
    assert {task.task_id: task.scheduled_date for task in schedule.tasks} == {
        task.id: task.occurrence_date for task in tasks
    }
    assert RuleEngine().hard_violations(schedule, context) == []


def _placed(day: date) -> ScheduledTask:
    return ScheduledTask(
        task_id=1,
        title="task",
        scheduled_date=day,
        start_time=time(9, 0),
        end_time=time(10, 0),
        duration_minutes=60,
    )


def test_earliest_start_rule_rejects_an_early_occurrence() -> None:
    earliest = MONDAY
    schedule = CandidateSchedule(
        start_date=earliest - timedelta(days=1),
        end_date=earliest,
        tasks=[_placed(earliest - timedelta(days=1))],
    )
    context = RuleContext(task_earliest_dates={1: earliest})

    violations = EarliestStartRule().validate(schedule, context)

    assert [violation.code for violation in violations] == ["earliest_start"]
    assert "earliest_start" in {rule.name for rule in RuleEngine().rules}


def test_scheduler_never_scans_before_the_earliest_date() -> None:
    future = date.today() + timedelta(days=3)
    task = drafts_to_tasks(
        [_draft_for_scheduler(order_index=0, occurrence=future)]
    )[0]
    context = RuleContext(
        daily_limit_minutes=300,
        buffer_minutes=15,
        high_cognitive_max_per_day=2,
        available_minutes_per_day=480,
        day_start=time(8, 0),
        day_end=time(22, 0),
        task_earliest_dates={task.id: future},
        task_deadlines={task.id: future},
    )

    schedule = Scheduler().schedule([task], context)

    assert len(schedule.tasks) == 1
    # Without the earliest-date guard the greedy scheduler would pick today.
    assert schedule.tasks[0].scheduled_date == future


def _draft_for_scheduler(*, order_index: int, occurrence: date):
    from app.agent.schemas import GeneratedTaskDraft

    return GeneratedTaskDraft(
        title="series",
        estimated_duration=60,
        order_index=order_index,
        occurrence_date=occurrence,
        deadline=datetime.combine(occurrence, time.max),
        task_kind=TaskKind.LONG_TERM,
        series_id="goal-1-long_term",
        series_index=0,
        is_flexible=False,
    )


def test_goal_id_zero_is_treated_as_no_goal() -> None:
    task = drafts_to_tasks([_draft_for_scheduler(order_index=0, occurrence=date.today())])[0]
    assert task.goal_id is None
