"""Goal association, deadline and earliest-start constraints."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pytest

from app.agent.nodes._shared import build_rule_context, drafts_to_tasks
from app.agent.schemas import (
    AnalyzedGoal,
    GeneratedTaskDraft,
    GoalAnalysisResult,
    GoalKind,
    PlanGenerationResult,
    TaskKind,
)
from app.agent.state import GoalInput, PlannerRequest
from app.agent.tools.execution_chunker import chunk_unscheduled_drafts
from app.agent.tools.plan_drafter import PlanDrafterInput, PlanDrafterMode, PlanDrafterTool
from app.agent.tools.task_decomposer import TaskDecomposerInput, TaskDecomposerTool
from app.application.exceptions import DomainValidationError
from app.application.services.plan_service import _apply_date_constraints_to_goals
from app.domain.date_constraints import (
    DateConstraintError,
    parse_earliest_start,
    resolve_earliest_start,
)
from app.domain.models import Task
from app.domain.models.enums import PlanningMode
from app.domain.rules.base import RuleContext, RuleEngine, default_rules
from app.domain.rules.earliest_start import EarliestStartRule
from app.domain.scheduling.schedule_result import CandidateSchedule, ScheduledTask
from app.domain.scheduling.scheduler import Scheduler

TODAY = date(2026, 10, 26)
EARLIEST = date(2026, 11, 2)
DEADLINE = date(2026, 11, 7)


def _payload(goals: list[GoalInput], analysis=None) -> PlanDrafterInput:
    return PlanDrafterInput(
        mode=PlanDrafterMode.INITIAL,
        goals=goals,
        goal_analysis=analysis,
        theoretical={},
        start_date=TODAY,
        end_date=DEADLINE,
    )


def _draft(
    title: str,
    *,
    goal_id: int | None,
    deadline: date | None = None,
    minutes: int = 60,
) -> GeneratedTaskDraft:
    return GeneratedTaskDraft(
        title=title,
        goal_id=goal_id,
        estimated_duration=minutes,
        deadline=(
            datetime.combine(deadline, time.max) if deadline is not None else None
        ),
    )


def test_task_without_goal_id_fails_closed_with_multiple_goals() -> None:
    goals = [
        GoalInput(title="DAMN", existing_goal_id=185, deadline=datetime.combine(TODAY, time.max)),
        GoalInput(title="CET", existing_goal_id=186, deadline=datetime.combine(DEADLINE, time.max)),
    ]
    generated = PlanGenerationResult(tasks=[_draft("CET", goal_id=None, deadline=DEADLINE)])

    with pytest.raises(ValueError, match="no valid goal_id"):
        PlanDrafterTool._materialize(generated, _payload(goals))


def test_task_deadline_after_goal_deadline_fails_closed() -> None:
    goals = [
        GoalInput(title="DAMN", existing_goal_id=185, deadline=datetime.combine(TODAY, time.max)),
        GoalInput(title="CET", existing_goal_id=186, deadline=datetime.combine(DEADLINE, time.max)),
    ]
    # CET task (deadline 11-07) incorrectly assigned to the DAMN goal (10-26).
    generated = PlanGenerationResult(
        tasks=[_draft("CET", goal_id=1, deadline=DEADLINE)]
    )

    with pytest.raises(ValueError, match="after goal"):
        PlanDrafterTool._materialize(generated, _payload(goals))


def test_different_goals_keep_distinct_work_unit_keys() -> None:
    goals = [
        GoalInput(title="DAMN", existing_goal_id=185, deadline=datetime.combine(TODAY, time.max)),
        GoalInput(title="CET", existing_goal_id=186, deadline=datetime.combine(DEADLINE, time.max)),
    ]
    generated = PlanGenerationResult(
        tasks=[
            _draft("DAMN", goal_id=1, deadline=TODAY),
            _draft("CET", goal_id=2, deadline=DEADLINE),
        ]
    )

    drafts = PlanDrafterTool._materialize(generated, _payload(goals)).tasks

    assert [draft.work_unit_key for draft in drafts] == [
        "wg-185-one_off",
        "wg-186-one_off",
    ]
    assert [draft.title for draft in drafts] == ["DAMN", "CET"]


def test_analyzed_earliest_start_is_applied_to_one_off_draft() -> None:
    goal = GoalInput(
        title="CET",
        existing_goal_id=186,
        deadline=datetime.combine(DEADLINE, time.max),
    )
    analysis = GoalAnalysisResult(
        goals=[
            AnalyzedGoal(
                goal_id=1,
                title="CET",
                goal_kind=GoalKind.ONE_OFF,
                earliest_start_date=EARLIEST,
            )
        ]
    )
    generated = PlanGenerationResult(
        tasks=[_draft("CET", goal_id=1, deadline=DEADLINE)]
    )

    drafts = PlanDrafterTool._materialize(
        generated, _payload([goal], analysis)
    ).tasks

    assert len(drafts) == 1
    assert drafts[0].earliest_start_date == EARLIEST
    assert drafts[0].deadline.date() == DEADLINE


def test_chunks_keep_earliest_start_and_work_unit_key() -> None:
    draft = _draft("CET", goal_id=1, minutes=120).model_copy(
        update={
            "order_index": 0,
            "task_kind": TaskKind.ONE_OFF,
            "work_unit_key": "wg-186-one_off",
            "earliest_start_date": EARLIEST,
        }
    )

    chunks = chunk_unscheduled_drafts([draft], {1}, daily_limit_minutes=60)

    assert chunks is not None
    assert len(chunks) >= 2
    assert sum(chunk.estimated_duration for chunk in chunks) == 120
    assert {chunk.earliest_start_date for chunk in chunks} == {EARLIEST}
    assert {chunk.work_unit_key for chunk in chunks} == {"wg-186-one_off"}
    assert len({chunk.parent_key for chunk in chunks}) == 1


def test_scheduler_and_earliest_rule_respect_11_02_to_11_07() -> None:
    task = Task(id=1, plan_id=0, title="CET", estimated_duration=60)
    context = RuleContext(
        daily_limit_minutes=300,
        available_minutes_per_day=480,
        buffer_minutes=15,
        high_cognitive_max_per_day=2,
        day_start=time(8, 0),
        day_end=time(22, 0),
        today=TODAY,
        task_earliest_dates={1: EARLIEST},
        task_deadlines={1: DEADLINE},
    )

    schedule = Scheduler().schedule([task], context)

    assert len(schedule.tasks) == 1
    assert schedule.tasks[0].scheduled_date == EARLIEST
    assert EARLIEST <= schedule.tasks[0].scheduled_date <= DEADLINE
    assert EarliestStartRule().validate(schedule, context) == []

# ---------------------------------------------------------------------------
# Deterministic explicit-date parsing (never LLM-only)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("安排在2026-11-01之后", date(2026, 11, 2)),
        ("安排在11月1日之后", date(2026, 11, 2)),
        ("不早于 2026-11-01", date(2026, 11, 1)),
        ("从 2026-11-02 开始", date(2026, 11, 2)),
        ("after 2026-11-01", date(2026, 11, 2)),
        ("not before 2026-11-02", date(2026, 11, 2)),
        ("2026年11月1日以后", date(2026, 11, 2)),
        ("2026/11/01之后", date(2026, 11, 2)),
    ],
)
def test_explicit_date_expressions(text: str, expected: date) -> None:
    assert parse_earliest_start(text, deadline=DEADLINE, reference=TODAY) == expected


def test_omitted_year_uses_deadline_year() -> None:
    # deadline 2027-01-05 + "12月20日之后" must mean 2026-12-21, not 2027.
    assert (
        parse_earliest_start(
            "12月20日之后",
            deadline=date(2027, 1, 5),
            reference=TODAY,
        )
        == date(2026, 12, 21)
    )


def test_false_positive_date_words_are_not_constraints() -> None:
    # The date is a deadline/mention; the later "after/for later" wording is
    # not attached to it, so it must not become an earliest-start constraint.
    for text in (
        "11\u67087\u65e5\u622a\u6b62\uff0c\u4e4b\u540e\u518d\u8bf4",
        "11\u67087\u65e5\u4e4b\u524d\u5b8c\u6210\uff0c\u4e4b\u540e\u590d\u4e60",
        "2026-11-07 \u622a\u6b62\uff0c\u4e4b\u540e\u590d\u76d8",
        "11\u67087\u65e5\u524d\u5b8c\u6210\uff1b\u4e4b\u540e\u6bcf\u5929\u590d\u4e60",
    ):
        assert parse_earliest_start(text, deadline=DEADLINE, reference=TODAY) is None


def test_cet_name_with_digits_and_slash_is_not_a_date() -> None:
    assert (
        parse_earliest_start(
            "CET4/6 \u711a\u8bc0", deadline=DEADLINE, reference=TODAY
        )
        is None
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("11\u67081\u53f7\u4e4b\u540e", date(2026, 11, 2)),
        ("\u4e0d\u65e9\u4e8e 11\u67081\u53f7", date(2026, 11, 1)),
        ("\u4ece 11\u67081\u53f7 \u5f00\u59cb", date(2026, 11, 1)),
    ],
)
def test_hao_day_suffix_parses(text: str, expected: date) -> None:
    assert parse_earliest_start(text, deadline=DEADLINE, reference=TODAY) == expected


def test_structured_deadline_alone_does_not_create_earliest() -> None:
    goal = GoalInput(
        title="CET4/6 \u711a\u8bc0",
        deadline=datetime.combine(DEADLINE, time.max),
        planning_mode=PlanningMode.ONE_OFF,
    )
    normalised = _apply_date_constraints_to_goals([goal], reference=TODAY)
    assert normalised[0].start_date is None


def test_partial_date_with_constraint_fails_closed_with_source() -> None:
    with pytest.raises(DateConstraintError, match="goal id=188"):
        parse_earliest_start(
            "11\u6708\u4e4b\u540e",
            deadline=DEADLINE,
            reference=TODAY,
            source="goal id=188 title='CET4/6'",
        )


def test_invalid_calendar_error_includes_source() -> None:
    with pytest.raises(DateConstraintError, match="goal id=188"):
        parse_earliest_start(
            "2026-02-30 \u4e4b\u540e",
            deadline=DEADLINE,
            reference=TODAY,
            source="goal id=188 title='CET4/6'",
        )


def test_plain_date_mention_is_not_a_constraint() -> None:
    assert parse_earliest_start("截止2026-11-07", deadline=DEADLINE, reference=TODAY) is None


def test_unparseable_explicit_constraint_fails_closed() -> None:
    with pytest.raises(DateConstraintError):
        parse_earliest_start("安排在 2026-02-30 之后", deadline=DEADLINE, reference=TODAY)
    with pytest.raises(DateConstraintError):
        parse_earliest_start("安排在 11月32日 之后", deadline=DEADLINE, reference=TODAY)


def test_earliest_after_deadline_fails_closed() -> None:
    with pytest.raises(DateConstraintError, match="after deadline"):
        resolve_earliest_start(
            date(2026, 11, 10),
            text=None,
            deadline=DEADLINE,
            reference=TODAY,
        )


def test_text_date_becomes_structured_goal_start_and_stays_goal_scoped() -> None:
    goals = [
        GoalInput(
            title="为同学撰写 CET4/6 焚决",
            description="安排在11月1日之后",
            existing_goal_id=186,
            deadline=datetime.combine(DEADLINE, time.max),
            planning_mode=PlanningMode.ONE_OFF,
        ),
        GoalInput(
            title="完成 DAMN 项目省赛版本开发",
            existing_goal_id=185,
            deadline=datetime.combine(TODAY + timedelta(days=1), time.max),
            planning_mode=PlanningMode.ONE_OFF,
        ),
    ]

    normalised = _apply_date_constraints_to_goals(goals, reference=TODAY)

    assert normalised[0].start_date == EARLIEST
    assert normalised[1].start_date is None


def test_contradictory_structured_date_fails_closed() -> None:
    goal = GoalInput(
        title="CET",
        start_date=date(2026, 11, 10),
        deadline=datetime.combine(DEADLINE, time.max),
    )
    with pytest.raises(DomainValidationError, match="after deadline"):
        _apply_date_constraints_to_goals([goal], reference=TODAY)


def test_cet_earliest_never_leaks_to_damn_and_scheduler_enforces_it() -> None:
    goals = [
        GoalInput(
            title="完成 DAMN 项目省赛版本开发",
            existing_goal_id=185,
            deadline=datetime.combine(TODAY + timedelta(days=1), time.max),
            planning_mode=PlanningMode.ONE_OFF,
        ),
        GoalInput(
            title="为同学撰写 CET4/6 焚决",
            description="安排在11月1日之后",
            existing_goal_id=186,
            deadline=datetime.combine(DEADLINE, time.max),
            planning_mode=PlanningMode.ONE_OFF,
        ),
    ]
    analysis = TaskDecomposerTool(None).run(TaskDecomposerInput(goals=goals))
    assert analysis.goals[0].earliest_start_date is None
    assert analysis.goals[1].earliest_start_date == EARLIEST

    generated = PlanGenerationResult(
        tasks=[
            _draft("DAMN", goal_id=1, deadline=TODAY),
            _draft("CET", goal_id=2, deadline=DEADLINE),
        ]
    )
    drafts = PlanDrafterTool._materialize(
        generated, _payload(goals, analysis)
    ).tasks
    assert drafts[0].earliest_start_date is None
    assert drafts[1].earliest_start_date == EARLIEST

    request = PlannerRequest(
        user_id=1, goals=goals, start_date=TODAY, end_date=DEADLINE
    )
    state = {
        "request": request,
        "goals": goals,
        "plan_draft": PlanGenerationResult(tasks=drafts),
    }
    context = build_rule_context(state, drafts)
    assert context.task_earliest_dates == {2: EARLIEST}

    schedule = Scheduler().schedule(drafts_to_tasks(drafts), context)
    by_id = {task.task_id: task for task in schedule.tasks}
    assert by_id[1].scheduled_date < EARLIEST
    assert EARLIEST <= by_id[2].scheduled_date <= DEADLINE
    assert EarliestStartRule().validate(schedule, context) == []


def test_rule_engine_rejects_any_schedule_before_earliest() -> None:
    context = RuleContext(
        daily_limit_minutes=300,
        available_minutes_per_day=480,
        buffer_minutes=15,
        high_cognitive_max_per_day=2,
        day_start=time(8, 0),
        day_end=time(22, 0),
        today=TODAY,
        task_earliest_dates={1: EARLIEST},
        task_deadlines={1: DEADLINE},
    )
    schedule = CandidateSchedule(
        start_date=TODAY,
        end_date=DEADLINE,
        tasks=[
            ScheduledTask(
                task_id=1,
                title="CET",
                scheduled_date=TODAY,
                start_time=time(8, 0),
                end_time=time(9, 0),
                duration_minutes=60,
            )
        ],
    )

    violations = RuleEngine(default_rules()).hard_violations(schedule, context)

    assert any(violation.code == "earliest_start" for violation in violations)
