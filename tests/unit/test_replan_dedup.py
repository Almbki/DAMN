"""Cross-version work-unit identity and replan remaining-work dedup."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.agent.schemas import (
    AnalyzedGoal,
    GoalAnalysisResult,
    GoalKind,
    WorkUnit,
)
from app.agent.state import GoalInput
from app.agent.tools.plan_drafter import (
    PlanDrafterInput,
    PlanDrafterMode,
    PlanDrafterTool,
)
from app.domain.models.enums import PlanningMode
from app.domain.recurrence import RecurrenceFrequency

MONDAY = date(2026, 1, 5)


def _analysis(
    kind: GoalKind, units: list[WorkUnit] | None = None
) -> GoalAnalysisResult:
    return GoalAnalysisResult(
        goals=[
            AnalyzedGoal(
                goal_id=1,
                title="big",
                goal_kind=kind,
                work_units=units or [],
            )
        ]
    )


def _run(goal: GoalInput, analysis, theoretical, **kwargs):
    return PlanDrafterTool(None).run(
        PlanDrafterInput(
            mode=PlanDrafterMode.INITIAL,
            goals=[goal],
            goal_analysis=analysis,
            theoretical=theoretical,
            start_date=goal.start_date or MONDAY,
            end_date=(
                goal.deadline.date()
                if goal.deadline is not None
                else MONDAY
            ),
            **kwargs,
        )
    ).tasks


def _goal(existing_goal_id: int, mode: PlanningMode, days: int = 3) -> GoalInput:
    return GoalInput(
        title="big",
        planning_mode=mode,
        existing_goal_id=existing_goal_id,
        start_date=MONDAY,
        deadline=datetime.combine(MONDAY + timedelta(days=days), time.max),
        estimated_minutes=240,
    )


def test_partial_one_off_deducts_completed_minutes() -> None:
    drafts = _run(
        _goal(7, PlanningMode.ONE_OFF),
        _analysis(GoalKind.ONE_OFF),
        {"items": [{"title": "big", "goal_id": 1, "total_minutes": 240}]},
        completed_work_by_unit={"wg-7-one_off": 120},
    )

    assert len(drafts) == 1
    assert drafts[0].work_unit_key == "wg-7-one_off"
    assert drafts[0].estimated_duration == 120


def test_fully_completed_work_unit_is_not_regenerated() -> None:
    drafts = _run(
        _goal(7, PlanningMode.ONE_OFF),
        _analysis(GoalKind.ONE_OFF),
        {"items": [{"title": "big", "goal_id": 1, "total_minutes": 240}]},
        completed_work_unit_keys={"wg-7-one_off"},
    )

    assert drafts == []


def test_partial_project_keeps_only_unfinished_work_unit() -> None:
    analysis = _analysis(
        GoalKind.PROJECT,
        [
            WorkUnit(title="A", estimated_minutes=120),
            WorkUnit(title="B", estimated_minutes=120),
        ],
    )
    drafts = _run(
        _goal(7, PlanningMode.PROJECT),
        analysis,
        {"items": []},
        completed_work_by_unit={"wg-7-project-0": 120},
    )

    assert [draft.work_unit_key for draft in drafts] == ["wg-7-project-1"]
    assert drafts[0].estimated_duration == 120
    assert drafts[0].title == "B"


def test_same_title_in_another_goal_is_not_merged() -> None:
    drafts = _run(
        _goal(8, PlanningMode.ONE_OFF),
        _analysis(GoalKind.ONE_OFF),
        {"items": [{"title": "big", "goal_id": 1, "total_minutes": 240}]},
        completed_work_by_unit={"wg-7-one_off": 120},
    )

    assert len(drafts) == 1
    assert drafts[0].work_unit_key == "wg-8-one_off"
    assert drafts[0].estimated_duration == 240


def test_recurring_is_not_deduped_as_a_one_off_work_unit() -> None:
    goal = GoalInput(
        title="daily",
        planning_mode=PlanningMode.RECURRING,
        existing_goal_id=7,
        recurrence_frequency=RecurrenceFrequency.DAILY,
        start_date=MONDAY,
        deadline=datetime.combine(MONDAY + timedelta(days=1), time.max),
        daily_target_minutes=20,
    )
    drafts = _run(
        goal,
        _analysis(GoalKind.RECURRING),
        {"items": []},
        completed_work_by_unit={"wg-7-one_off": 120},
    )

    assert len(drafts) == 2
    assert all(draft.work_unit_key is None for draft in drafts)
