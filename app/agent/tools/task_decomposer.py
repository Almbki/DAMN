"""``task_decomposer`` tool - goals -> objective + subtasks.

LLM-backed (``llm_exposed=True``) with a deterministic heuristic fallback that
keeps the pipeline running when no model is configured.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent.llm import StructuredLLM
from app.agent.schemas import AnalyzedGoal, GoalAnalysisResult
from app.agent.state import GoalInput
from app.agent.tools.base import BaseTool

PROMPT_NAME = "goal_analysis"


class TaskDecomposerInput(BaseModel):
    goals: list[GoalInput] = Field(default_factory=list)
    user_profile: dict = Field(default_factory=dict)
    execution_weight: float = 0.5


class TaskDecomposerTool(BaseTool[TaskDecomposerInput, GoalAnalysisResult]):
    name = "task_decomposer"
    description = (
        "Decompose raw goals into an objective, ordered subtasks and inferred "
        "constraints. Returns a structured GoalAnalysisResult."
    )
    llm_exposed = True

    def __init__(self, llm: StructuredLLM | None = None) -> None:
        self._llm = llm

    def run(self, payload: TaskDecomposerInput) -> GoalAnalysisResult:
        fallback = self._heuristic(payload)
        if self._llm is None or not self._llm.enabled:
            return fallback

        result = self._llm.complete_model(
            prompt_name=PROMPT_NAME,
            schema=GoalAnalysisResult,
            variables={
                "goals": [goal.model_dump(mode="json") for goal in payload.goals],
                "user_profile": payload.user_profile,
                "execution_weight": payload.execution_weight,
            },
            fallback=fallback,
        )
        value = result.value
        goals_by_key = {idx: goal for idx, goal in enumerate(payload.goals, start=1)}
        analyzed = [
            item.model_copy(update={"subtasks": []})
            if not goals_by_key.get(item.goal_id) or not goals_by_key[item.goal_id].description
            else item
            for item in value.goals
        ]
        return value.model_copy(update={"goals": analyzed})

    @staticmethod
    def _heuristic(payload: TaskDecomposerInput) -> GoalAnalysisResult:
        """Deterministic fallback: split only user-provided supplement text."""
        analyzed: list[AnalyzedGoal] = []
        confidences: list[float] = []
        for idx, goal in enumerate(payload.goals, start=1):
            analyzed.append(
                AnalyzedGoal(
                    # 1-based goal key; matches the provisional task id contract.
                    goal_id=idx,
                    title=goal.title,
                    objective=goal.description or goal.title,
                    subtasks=TaskDecomposerTool._subtasks(goal),
                    constraints=[],
                )
            )
            confidences.append(0.6 if goal.estimated_minutes is not None else 0.45)

        confidence = sum(confidences) / len(confidences) if confidences else 0.5
        return GoalAnalysisResult(
            goals=analyzed,
            summary=f"Analyzed {len(analyzed)} goal(s).",
            confidence=round(confidence, 4),
        )

    @staticmethod
    def _subtasks(goal: GoalInput) -> list[str]:
        """Substeps exist only when the user supplied supplement content."""
        if not goal.description or not goal.description.strip():
            return []
        raw = goal.description.replace("；", ";")
        parts = [p.strip() for line in raw.split("\n") for p in line.split(";")]
        return [p for p in parts if p]

    def summarize(self, value: GoalAnalysisResult) -> str:
        return f"{len(value.goals)} goal(s) decomposed"


__all__ = ["PROMPT_NAME", "TaskDecomposerInput", "TaskDecomposerTool"]
