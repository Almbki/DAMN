"""Agent tools.

``llm_exposed=True`` tools may be bound to a model's tool-calling interface.
Deterministic capabilities (scheduling, rule validation, workload estimation,
memory lookup) are deliberately ``False`` - the LLM must never decide hard
constraints or read the database.
"""

from __future__ import annotations

from app.agent.llm import StructuredLLM
from app.agent.tools.base import BaseTool, ToolRegistry, ToolResult
from app.agent.tools.memory_retriever import MemoryRetrieverTool
from app.agent.tools.plan_drafter import PlanDrafterMode, PlanDrafterTool
from app.agent.tools.rule_validator import RuleValidatorTool
from app.agent.tools.schedule_generator import ScheduleGeneratorTool
from app.agent.tools.task_decomposer import TaskDecomposerTool
from app.agent.tools.task_estimator import TaskEstimatorTool
from app.agent.tools.workload_estimator import WorkloadEstimatorTool
from app.domain.rules.base import RuleEngine
from app.domain.scheduling.scheduler import Scheduler


def default_registry(
    *,
    llm: StructuredLLM | None = None,
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
        MemoryRetrieverTool(),
        TaskEstimatorTool(),
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
    "TaskEstimatorTool",
    "ToolRegistry",
    "ToolResult",
    "WorkloadEstimatorTool",
    "default_registry",
]
