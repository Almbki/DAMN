"""Request-local goal references vs. persisted goal ids."""

from __future__ import annotations

from datetime import date, datetime, time

import pytest

from app.agent.goal_identity import goal_id_map_for, goal_index_for_ref
from app.agent.nodes._shared import drafts_to_tasks
from app.agent.schemas import (
    AnalyzedGoal,
    GeneratedTaskDraft,
    GoalAnalysisResult,
    GoalKind,
    PlanGenerationResult,
    RecurrenceSpec,
)
from app.agent.state import GoalInput
from app.agent.tools.plan_drafter import (
    PlanDrafterInput,
    PlanDrafterMode,
    PlanDrafterTool,
)
from app.domain.models.enums import PlanningMode, TaskKind
from app.domain.recurrence import RecurrenceFrequency

TODAY = date(2026, 10, 26)
DEADLINE = date(2026, 11, 7)
#: Deliberately non-contiguous database ids, all larger than the request size.
DB_IDS = [178, 185, 186, 205, 240]


def _goals() -> list[GoalInput]:
    return [
        GoalInput(
            title=f"goal-{goal_id}",
            existing_goal_id=goal_id,
            deadline=datetime.combine(DEADLINE, time.max),
        )
        for goal_id in DB_IDS
    ]


def _payload(goals: list[GoalInput], analysis=None) -> PlanDrafterInput:
    return PlanDrafterInput(
        mode=PlanDrafterMode.INITIAL,
        goals=goals,
        goal_analysis=analysis,
        theoretical={},
        start_date=TODAY,
        end_date=DEADLINE,
    )


def _draft(goal_ref: int | None, *, title: str = "task") -> GeneratedTaskDraft:
    return GeneratedTaskDraft(title=title, goal_id=goal_ref, estimated_duration=60)


def test_real_database_ids_map_to_request_indices() -> None:
    goals = _goals()
    analysis = GoalAnalysisResult(
        goals=[
            AnalyzedGoal(
                goal_id=178,  # real database id echoed by the model
                title="goal-178",
                goal_kind=GoalKind.ONE_OFF,
                earliest_start_date=date(2026, 11, 2),
            )
        ]
    )
    generated = PlanGenerationResult(
        tasks=[_draft(178, title="a"), _draft(185, title="b"), _draft(1, title="c")]
    )

    drafts = PlanDrafterTool._materialize(
        generated, _payload(goals, analysis)
    ).tasks

    by_title = {draft.title: draft for draft in drafts}
    assert sorted(draft.goal_id for draft in drafts) == [1, 1, 2]
    assert by_title["a"].goal_id == 1
    assert by_title["b"].goal_id == 2
    assert by_title["c"].goal_id == 1
    assert by_title["a"].work_unit_key == "wg-178-one_off"
    assert by_title["b"].work_unit_key == "wg-185-one_off"
    assert by_title["c"].work_unit_key == "wg-178-one_off"
    # Real-id analysis is recovered instead of silently dropping its facts.
    assert by_title["a"].earliest_start_date == date(2026, 11, 2)


def test_unknown_goal_ref_fails_closed() -> None:
    goals = _goals()
    with pytest.raises(ValueError, match="invalid goal_id 999"):
        PlanDrafterTool._materialize(
            PlanGenerationResult(tasks=[_draft(999)]), _payload(goals)
        )


def test_missing_goal_ref_fails_closed_with_multiple_goals() -> None:
    goals = _goals()
    with pytest.raises(ValueError, match="no valid goal_id"):
        PlanDrafterTool._materialize(
            PlanGenerationResult(tasks=[_draft(None)]), _payload(goals)
        )


def test_identity_map_builds_index_to_persisted_id() -> None:
    assert goal_id_map_for(_goals()) == {
        1: 178,
        2: 185,
        3: 186,
        4: 205,
        5: 240,
    }
    assert goal_index_for_ref(178, _goals()) == 1
    assert goal_index_for_ref(5, _goals()) == 5
    assert goal_index_for_ref(999, _goals()) is None


def test_drafts_to_tasks_maps_local_indices_to_real_goal_ids() -> None:
    drafts = PlanDrafterTool._materialize(
        PlanGenerationResult(tasks=[_draft(178), _draft(240)]),
        _payload(_goals()),
    ).tasks

    tasks = drafts_to_tasks(drafts, goal_id_map=goal_id_map_for(_goals()))

    assert [task.goal_id for task in tasks] == [178, 240]


def test_recurring_goal_with_large_real_id_keeps_its_identity() -> None:
    goals = _goals()
    goals[0] = GoalInput(
        title="背考研英语单词",
        existing_goal_id=178,
        planning_mode=PlanningMode.RECURRING,
        recurrence_frequency=RecurrenceFrequency.DAILY,
        task_kind=TaskKind.ROUTINE,
        start_date=TODAY,
        deadline=datetime.combine(TODAY.replace(day=29), time.max),
        daily_target_minutes=20,
    )
    analysis = GoalAnalysisResult(
        goals=[
            AnalyzedGoal(
                goal_id=178,
                title="背考研英语单词",
                goal_kind=GoalKind.RECURRING,
                recurrence=RecurrenceSpec(frequency=RecurrenceFrequency.DAILY),
            )
        ]
    )
    drafts = PlanDrafterTool._materialize(
        PlanGenerationResult(tasks=[_draft(178, title="背考研英语单词")]),
        _payload(goals, analysis),
    ).tasks

    assert len(drafts) == 4
    assert {draft.goal_id for draft in drafts} == {1}
    assert {draft.series_id for draft in drafts} == {"goal-1-routine"}
    assert all(draft.work_unit_key is None for draft in drafts)
    assert all(draft.task_kind.value == "routine" for draft in drafts)


def test_multiple_goals_do_not_share_work_unit_identity() -> None:
    goals = _goals()
    generated = PlanGenerationResult(
        tasks=[
            _draft(178, title="a"),
            _draft(185, title="b"),
            _draft(186, title="c"),
            _draft(205, title="d"),
            _draft(240, title="e"),
        ]
    )

    drafts = PlanDrafterTool._materialize(generated, _payload(goals)).tasks

    assert [draft.work_unit_key for draft in drafts] == [
        "wg-178-one_off",
        "wg-185-one_off",
        "wg-186-one_off",
        "wg-205-one_off",
        "wg-240-one_off",
    ]
    assert len({draft.work_unit_key for draft in drafts}) == 5
    assert [draft.goal_id for draft in drafts] == [1, 2, 3, 4, 5]
