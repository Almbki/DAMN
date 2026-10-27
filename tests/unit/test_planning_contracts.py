"""Architecture contracts: explicit planning_mode, clarification, workload, 1:1."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.agent.schemas import (
    AnalyzedGoal,
    DecompositionStatus,
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
from app.agent.tools.task_decomposer import (
    TaskDecomposerInput,
    TaskDecomposerTool,
)
from app.agent.tools.workload_estimator import (
    WorkloadEstimatorInput,
    WorkloadEstimatorTool,
)
from app.domain.models.enums import GoalType, PlanningMode
from app.domain.recurrence import RecurrenceFrequency

MONDAY = date(2026, 1, 5)


def _decompose(goal: GoalInput):
    return TaskDecomposerTool(None).run(TaskDecomposerInput(goals=[goal])).goals[0]


# ---------------------------------------------------------------------------
# Explicit planning_mode authority
# ---------------------------------------------------------------------------
def test_explicit_one_off_keeps_internal_checklist_and_stays_one_off() -> None:
    goal = GoalInput(
        title="写实验报告",
        description="整理数据\n写报告\n检查格式",
        planning_mode=PlanningMode.ONE_OFF,
        goal_type=GoalType.SHORT_TERM,
    )

    analyzed = _decompose(goal)

    assert analyzed.goal_kind is GoalKind.ONE_OFF
    assert analyzed.subtasks == ["整理数据", "写报告", "检查格式"]
    assert analyzed.work_units == []
    assert analyzed.recurrence is None
    assert analyzed.decomposition_status is DecompositionStatus.READY


def test_explicit_recurring_is_opaque_and_ready() -> None:
    goal = GoalInput(
        title="背考研单词",
        description="新词\n复习\n遗忘曲线",
        planning_mode=PlanningMode.RECURRING,
        recurrence_frequency=RecurrenceFrequency.DAILY,
        daily_target_minutes=20,
    )

    analyzed = _decompose(goal)

    assert analyzed.goal_kind is GoalKind.RECURRING
    assert analyzed.subtasks == []
    assert analyzed.work_units == []
    assert analyzed.recurrence is not None
    assert analyzed.decomposition_status is DecompositionStatus.READY


def test_explicit_project_without_curriculum_needs_clarification() -> None:
    goal = GoalInput(
        title="30 天学高数",
        planning_mode=PlanningMode.PROJECT,
    )

    analyzed = _decompose(goal)

    assert analyzed.goal_kind is GoalKind.PROJECT
    assert analyzed.work_units == []
    assert analyzed.decomposition_status is DecompositionStatus.NEEDS_CLARIFICATION
    assert analyzed.missing_information


def test_explicit_project_with_clarified_curriculum_is_ready() -> None:
    goal = GoalInput(
        title="学高数",
        planning_mode=PlanningMode.PROJECT,
        estimated_minutes=60,
        clarifications={"curriculum": "极限;导数;积分"},
    )

    analyzed = _decompose(goal)

    assert analyzed.goal_kind is GoalKind.PROJECT
    assert [unit.title for unit in analyzed.work_units] == ["极限", "导数", "积分"]
    assert analyzed.decomposition_status is DecompositionStatus.READY


def test_explicit_project_recurring_is_project_plus_recurrence() -> None:
    goal = GoalInput(
        title="每天学高数",
        planning_mode=PlanningMode.PROJECT_RECURRING,
        recurrence_frequency=RecurrenceFrequency.DAILY,
        clarifications={"curriculum": "极限;导数"},
        estimated_minutes=60,
    )

    analyzed = _decompose(goal)

    assert analyzed.goal_kind is GoalKind.PROJECT
    assert [unit.title for unit in analyzed.work_units] == ["极限", "导数"]
    assert analyzed.recurrence is not None
    assert analyzed.recurrence.frequency is RecurrenceFrequency.DAILY


# ---------------------------------------------------------------------------
# Theoretical workload granularity
# ---------------------------------------------------------------------------
def test_project_theoretical_workload_is_per_work_unit() -> None:
    analysis = GoalAnalysisResult(
        goals=[
            AnalyzedGoal(
                goal_id=1,
                title="学高数",
                goal_kind=GoalKind.PROJECT,
                work_units=[
                    WorkUnit(title="极限", estimated_minutes=120),
                    WorkUnit(title="导数", estimated_minutes=90),
                ],
            )
        ]
    )
    goal = GoalInput(
        title="学高数",
        planning_mode=PlanningMode.PROJECT,
        start_date=MONDAY,
        deadline=datetime.combine(MONDAY + timedelta(days=10), time.max),
    )

    result = WorkloadEstimatorTool(None).run(
        WorkloadEstimatorInput(goals=[goal], goal_analysis=analysis)
    )

    assert len(result.items) == 2
    assert result.items[0].goal_id == 1
    assert result.items[0].work_unit_index == 0
    assert result.items[0].total_minutes == 120
    assert result.items[1].work_unit_index == 1
    assert result.items[1].total_minutes == 90


def test_recurring_theoretical_workload_is_one_occurrence() -> None:
    analysis = GoalAnalysisResult(
        goals=[
            AnalyzedGoal(
                goal_id=1,
                title="背单词",
                goal_kind=GoalKind.RECURRING,
                recurrence=RecurrenceSpec(frequency=RecurrenceFrequency.DAILY),
            )
        ]
    )
    goal = GoalInput(
        title="背单词",
        planning_mode=PlanningMode.RECURRING,
        daily_target_minutes=20,
    )

    result = WorkloadEstimatorTool(None).run(
        WorkloadEstimatorInput(goals=[goal], goal_analysis=analysis)
    )

    assert len(result.items) == 1
    assert result.items[0].total_minutes == 20
    assert result.items[0].subtasks == []


# ---------------------------------------------------------------------------
# PROJECT_RECURRING v1: work unit i -> occurrence i
# ---------------------------------------------------------------------------
def test_project_recurring_pairs_units_with_occurrence_dates() -> None:
    goal = GoalInput(
        title="每天学高数",
        planning_mode=PlanningMode.PROJECT_RECURRING,
        recurrence_frequency=RecurrenceFrequency.DAILY,
        start_date=MONDAY,
        deadline=datetime.combine(MONDAY + timedelta(days=3), time.max),
        daily_target_minutes=60,
    )
    analysis = GoalAnalysisResult(
        goals=[
            AnalyzedGoal(
                goal_id=1,
                title="每天学高数",
                goal_kind=GoalKind.PROJECT,
                recurrence=RecurrenceSpec(frequency=RecurrenceFrequency.DAILY),
                work_units=[
                    WorkUnit(title="极限", estimated_minutes=60),
                    WorkUnit(title="导数", estimated_minutes=60),
                    WorkUnit(title="积分", estimated_minutes=60),
                ],
            )
        ]
    )

    result = PlanDrafterTool(None).run(
        PlanDrafterInput(
            mode=PlanDrafterMode.INITIAL,
            goals=[goal],
            goal_analysis=analysis,
            theoretical={"items": []},
            start_date=MONDAY,
            end_date=MONDAY + timedelta(days=3),
        )
    )

    drafts = result.tasks
    assert [draft.title for draft in drafts] == ["极限", "导数", "积分"]
    assert [draft.occurrence_date for draft in drafts] == [
        MONDAY,
        MONDAY + timedelta(days=1),
        MONDAY + timedelta(days=2),
    ]
    assert {draft.series_id for draft in drafts} == {"goal-1-project"}
