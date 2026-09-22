"""Tool contract tests: registry, LLM exposure and deterministic behaviour."""

from __future__ import annotations

from datetime import date, time

from app.agent.context import (
    MemoryItem,
    MemoryKind,
    PlanningContext,
    UserPreferences,
)
from app.agent.schemas import GeneratedTaskDraft
from app.agent.state import GoalInput
from app.agent.tools import default_registry
from app.agent.tools.memory_retriever import MemoryQuery, MemoryRetrieverInput
from app.agent.tools.rule_validator import RuleValidatorInput
from app.agent.tools.schedule_generator import ScheduleGeneratorInput
from app.agent.tools.task_decomposer import TaskDecomposerInput
from app.agent.tools.user_statistics import UserStatisticsInput
from app.agent.tools.workload_estimator import WorkloadEstimatorInput
from app.domain.models import Task
from app.domain.models.enums import CognitiveLoad, Priority
from app.domain.rules.base import RuleContext
from app.domain.scheduling.schedule_result import CandidateSchedule, ScheduledTask
from app.ml.base import FeedbackSignal

EXPECTED_TOOLS = {
    "memory_retriever",
    "plan_drafter",
    "rule_validator",
    "schedule_generator",
    "task_decomposer",
    "task_duration_predictor",
    "user_statistics",
    "workload_estimator",
}
#: Only language-understanding tools may ever be exposed to a model.
LLM_EXPOSED = {"task_decomposer", "workload_estimator", "plan_drafter"}


def test_registry_exposes_the_expected_tools() -> None:
    registry = default_registry()
    assert set(registry.names()) == EXPECTED_TOOLS
    assert {tool.name for tool in registry.llm_tools()} == LLM_EXPOSED


def test_every_tool_has_a_name_and_description() -> None:
    for tool in default_registry().all():
        assert tool.name
        assert tool.description


def test_deterministic_tools_are_not_llm_exposed() -> None:
    """Hard constraints, scheduling and DB lookups must never be model-driven."""
    registry = default_registry()
    for name in ("rule_validator", "schedule_generator", "user_statistics", "memory_retriever"):
        assert registry.get(name).llm_exposed is False


def test_task_decomposer_fallback_splits_description() -> None:
    tool = default_registry().get("task_decomposer")
    goal = GoalInput(title="高数", description="看课\n做例题\n做练习", subject="math")
    result = tool.run(TaskDecomposerInput(goals=[goal]))  # type: ignore[attr-defined]
    assert result.goals[0].subtasks == ["看课", "做例题", "做练习"]
    assert result.goals[0].goal_id == 1  # 1-based goal key


def test_workload_estimator_maps_cognitive_load() -> None:
    tool = default_registry().get("workload_estimator")
    goals = [
        GoalInput(title="数学", subject="math"),
        GoalInput(title="英语", subject="english"),
    ]
    result = tool.run(WorkloadEstimatorInput(goals=goals))  # type: ignore[attr-defined]
    assert result.items[0].cognitive_load is CognitiveLoad.HIGH
    assert result.items[1].cognitive_load is CognitiveLoad.MEDIUM
    for item in result.items:
        assert (
            item.video_minutes + item.reading_minutes + item.practice_minutes
            == item.total_minutes
        )


def test_schedule_generator_and_rule_validator_agree() -> None:
    registry = default_registry()
    task = Task(
        id=1,
        plan_id=0,
        title="A",
        estimated_duration=60,
        cognitive_load=CognitiveLoad.MEDIUM,
        order_index=0,
    )
    context = RuleContext(daily_limit_minutes=300, available_minutes_per_day=300)
    schedule = registry.get("schedule_generator").run(  # type: ignore[attr-defined]
        ScheduleGeneratorInput(tasks=[task], context=context)
    )
    validation = registry.get("rule_validator").run(  # type: ignore[attr-defined]
        RuleValidatorInput(schedule=schedule, context=context)
    )
    assert validation.passed is True


def test_rule_validator_flags_a_bad_schedule() -> None:
    day = date.today()
    bad = CandidateSchedule(
        start_date=day,
        end_date=day,
        tasks=[
            ScheduledTask(
                task_id=1,
                title="A",
                scheduled_date=day,
                start_time=time(7, 0),
                end_time=time(8, 0),
                duration_minutes=60,
                cognitive_load=CognitiveLoad.MEDIUM,
                priority=Priority.MEDIUM,
            )
        ],
    )
    context = RuleContext(day_start=time(8, 0), day_end=time(22, 0))
    validation = default_registry().get("rule_validator").run(  # type: ignore[attr-defined]
        RuleValidatorInput(schedule=bad, context=context)
    )
    assert validation.passed is False
    assert any(v.code == "outside_available_window" for v in validation.violations)


def test_memory_retriever_filters_by_kind() -> None:
    context = PlanningContext(
        user_id=1,
        semantic_memory=[MemoryItem(kind=MemoryKind.SEMANTIC, key="profile", summary="profile")],
        procedural_memory=[MemoryItem(kind=MemoryKind.PROCEDURAL, key="slot", summary="morning")],
    )
    tool = default_registry().get("memory_retriever")
    digest = tool.run(  # type: ignore[attr-defined]
        MemoryRetrieverInput(context=context, query=MemoryQuery(kind=MemoryKind.PROCEDURAL))
    )
    assert digest.procedural == ["morning"]
    assert digest.semantic == []


def test_user_statistics_summarises_feedback() -> None:
    context = PlanningContext(
        user_id=1,
        preferences=UserPreferences(daily_limit_minutes=120),
        recent_feedback=[
            FeedbackSignal(date=date.today(), completion_rate=0.4, stress_level=8, energy_level=3)
        ],
    )
    tool = default_registry().get("user_statistics")
    stats = tool.run(UserStatisticsInput(context=context))  # type: ignore[attr-defined]
    assert stats.days_with_feedback == 1
    assert stats.recent_completion_rate == 0.4
    assert stats.recent_stress == 8.0
    assert stats.daily_limit_minutes == 120


def test_tool_invoke_reports_failures_without_raising() -> None:
    tool = default_registry().get("task_decomposer")
    outcome = tool.invoke("not-a-payload")  # type: ignore[arg-type]
    assert outcome.ok is False
    assert outcome.error


def test_plan_drafter_never_emits_times() -> None:
    from app.agent.tools.plan_drafter import PlanDrafterInput, PlanDrafterMode

    tool = default_registry().get("plan_drafter")
    payload = PlanDrafterInput(
        mode=PlanDrafterMode.ADJUSTMENT,
        goals=[GoalInput(title="数学", subject="math")],
    )
    result = tool.run(payload)  # type: ignore[attr-defined]
    assert isinstance(result.tasks, list)
    for draft in result.tasks:
        assert isinstance(draft, GeneratedTaskDraft)
