"""Agent tools.

``llm_exposed=True`` tools may be bound to a model's tool-calling interface.
Deterministic capabilities (scheduling, rule validation, statistics, memory
lookup, ML adapters) are deliberately ``False`` - the LLM must never decide
hard constraints or read the database.
"""

from __future__ import annotations

from app.agent.llm import StructuredLLM
from app.agent.tools.base import BaseTool, ToolRegistry, ToolResult
from app.agent.tools.memory_retriever import MemoryRetrieverTool
from app.agent.tools.plan_drafter import PlanDrafterMode, PlanDrafterTool
from app.agent.tools.rule_validator import RuleValidatorTool
from app.agent.tools.schedule_generator import ScheduleGeneratorTool
from app.agent.tools.task_decomposer import TaskDecomposerTool
from app.agent.tools.task_duration_predictor import TaskDurationPredictorTool
from app.agent.tools.user_statistics import UserStatisticsTool
from app.agent.tools.workload_estimator import WorkloadEstimatorTool
from app.domain.rules.base import RuleEngine
from app.domain.scheduling.scheduler import Scheduler
from app.ml.predictors import PredictorSet


def default_registry(
    *,
    llm: StructuredLLM | None = None,
    predictors: PredictorSet | None = None,
    scheduler: Scheduler | None = None,
    rule_engine: RuleEngine | None = None,
) -> ToolRegistry:
    """Build the standard tool set wired to the injected collaborators."""
    registry = ToolRegistry()
    for tool in (
        TaskDecomposerTool(llm),
        WorkloadEstimatorTool(llm),
        PlanDrafterTool(llm),
        ScheduleGeneratorTool(scheduler),
        RuleValidatorTool(rule_engine),
        UserStatisticsTool(),
        MemoryRetrieverTool(),
        TaskDurationPredictorTool(predictors),
    ):
        registry.register(tool)
    return registry


__all__ = [
    "BaseTool",
    "MemoryRetrieverTool",
    "PlanDrafterMode",
    "PlanDrafterTool",
    "RuleValidatorTool",
    "ScheduleGeneratorTool",
    "TaskDecomposerTool",
    "TaskDurationPredictorTool",
    "ToolRegistry",
    "ToolResult",
    "UserStatisticsTool",
    "WorkloadEstimatorTool",
    "default_registry",
]
