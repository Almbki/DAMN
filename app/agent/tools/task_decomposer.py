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

#: Generic stage templates used when a goal has no description to split.
_GENERIC_STAGES: tuple[tuple[tuple[str, ...], list[str]], ...] = (
    (
        ("math", "数学", "算法", "algorithm", "408"),
        ["概念理解", "例题精做", "专项训练", "总结复盘"],
    ),
    (("english", "language", "英语", "语言"), ["词汇积累", "练习巩固", "总结复盘"]),
    (("reading", "writing", "阅读", "写作"), ["资料研读", "动笔输出", "修改复盘"]),
    (("exercise", "music", "锻炼", "练琴", "运动"), ["热身准备", "主体练习", "放松整理"]),
)

_DEFAULT_STAGES: list[str] = ["理解内容", "练习巩固", "总结复盘"]

PROMPT_NAME = "goal_analysis"


class TaskDecomposerInput(BaseModel):
    goals: list[GoalInput] = Field(default_factory=list)
    user_profile: dict = Field(default_factory=dict)
    mbti: str | None = None
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
                "mbti": payload.mbti or "",
                "execution_weight": payload.execution_weight,
            },
            fallback=fallback,
        )
        return result.value

    @staticmethod
    def _heuristic(payload: TaskDecomposerInput) -> GoalAnalysisResult:
        """Deterministic fallback: split descriptions, else generic stages."""
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
        if goal.description:
            raw = goal.description.replace("；", ";")
            parts = [p.strip() for line in raw.split("\n") for p in line.split(";")]
            cleaned = [p for p in parts if p]
            if cleaned:
                return cleaned

        hint = " ".join(filter(None, (goal.subject or "", goal.task_type or ""))).lower()
        for keywords, stages in _GENERIC_STAGES:
            if any(keyword in hint for keyword in keywords):
                return list(stages)
        return list(_DEFAULT_STAGES)

    def summarize(self, value: GoalAnalysisResult) -> str:
        return f"{len(value.goals)} goal(s) decomposed"


__all__ = ["PROMPT_NAME", "TaskDecomposerInput", "TaskDecomposerTool"]
