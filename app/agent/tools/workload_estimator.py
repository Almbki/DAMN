"""``workload_estimator`` tool - theoretical workload per goal.

LLM-backed (``llm_exposed=True``) with a deterministic subject/keyword fallback.
This is the *theory* side: it must not personalise to the individual user.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent.llm import StructuredLLM
from app.agent.schemas import (
    GoalAnalysisResult,
    TheoreticalAnalysisResult,
    TheoreticalItem,
)
from app.agent.state import GoalInput
from app.agent.tools.base import BaseTool
from app.domain.models.enums import CognitiveLoad

PROMPT_NAME = "theoretical_analysis"

_COGNITIVE_KEYWORDS: dict[CognitiveLoad, tuple[str, ...]] = {
    CognitiveLoad.HIGH: ("math", "algorithm", "数学", "算法", "408", "物理"),
    CognitiveLoad.MEDIUM: (
        "english",
        "language",
        "英语",
        "语言",
        "线代",
        "编程",
        "programming",
    ),
    CognitiveLoad.RESTORATIVE: ("锻炼", "练琴", "休息", "rest", "music", "exercise"),
}

_DIFFICULTY_BY_LOAD: dict[CognitiveLoad, float] = {
    CognitiveLoad.HIGH: 4.0,
    CognitiveLoad.MEDIUM: 3.0,
    CognitiveLoad.LOW: 2.0,
    CognitiveLoad.RESTORATIVE: 2.0,
}

_TIME_DEFAULTS: tuple[tuple[tuple[str, ...], int, tuple[int, int, int]], ...] = (
    (("math", "algorithm", "数学", "算法", "408"), 120, (30, 30, 60)),
    (("english", "language", "英语", "语言"), 60, (20, 30, 10)),
    (("reading", "writing", "阅读", "写作"), 90, (10, 50, 30)),
)

_FALLBACK_TOTAL = 90
_FALLBACK_SPLIT: tuple[int, int, int] = (30, 30, 30)

_LOAD_RANK = {
    CognitiveLoad.RESTORATIVE: 0,
    CognitiveLoad.LOW: 1,
    CognitiveLoad.MEDIUM: 2,
    CognitiveLoad.HIGH: 3,
}


class WorkloadEstimatorInput(BaseModel):
    goals: list[GoalInput] = Field(default_factory=list)
    goal_analysis: GoalAnalysisResult | None = None
    user_profile: dict = Field(default_factory=dict)


class WorkloadEstimatorTool(BaseTool[WorkloadEstimatorInput, TheoreticalAnalysisResult]):
    name = "workload_estimator"
    description = (
        "Estimate the theoretical workload (video / reading / practice minutes, "
        "difficulty, cognitive load) for each goal."
    )
    llm_exposed = True

    def __init__(self, llm: StructuredLLM | None = None) -> None:
        self._llm = llm

    def run(self, payload: WorkloadEstimatorInput) -> TheoreticalAnalysisResult:
        fallback = self._heuristic(payload)
        if self._llm is None or not self._llm.enabled:
            return fallback

        result = self._llm.complete_model(
            prompt_name=PROMPT_NAME,
            schema=TheoreticalAnalysisResult,
            variables={
                "goals": [goal.model_dump(mode="json") for goal in payload.goals],
                "goal_analysis": (
                    payload.goal_analysis.model_dump(mode="json")
                    if payload.goal_analysis
                    else {}
                ),
                "user_profile": payload.user_profile,
            },
            fallback=fallback,
        )
        return result.value

    @classmethod
    def _heuristic(cls, payload: WorkloadEstimatorInput) -> TheoreticalAnalysisResult:
        items: list[TheoreticalItem] = []
        for idx, goal in enumerate(payload.goals):
            total, (video, reading, practice) = cls._workload(goal)
            load = cls._cognitive_load(goal)
            items.append(
                TheoreticalItem(
                    title=goal.title,
                    learning_content=goal.description or goal.title,
                    subtasks=cls._subtasks(idx, goal, payload.goal_analysis),
                    video_minutes=video,
                    reading_minutes=reading,
                    practice_minutes=practice,
                    total_minutes=total,
                    difficulty=_DIFFICULTY_BY_LOAD[load],
                    cognitive_load=load,
                )
            )

        total_minutes = sum(item.total_minutes for item in items)
        overall = (
            round(sum(item.difficulty for item in items) / len(items), 4) if items else 3.0
        )
        return TheoreticalAnalysisResult(
            items=items,
            total_theoretical_minutes=total_minutes,
            overall_difficulty=overall,
            cognitive_load=cls._aggregate_load(items),
            confidence=0.5,
        )

    @staticmethod
    def _workload(goal: GoalInput) -> tuple[int, tuple[int, int, int]]:
        if goal.estimated_minutes is not None:
            total = goal.estimated_minutes
            video = round(total * 0.3)
            reading = round(total * 0.3)
            practice = total - video - reading
            return total, (video, reading, practice)

        hint = " ".join(filter(None, (goal.subject or "", goal.task_type or ""))).lower()
        for keywords, total, split in _TIME_DEFAULTS:
            if any(keyword in hint for keyword in keywords):
                return total, split
        return _FALLBACK_TOTAL, _FALLBACK_SPLIT

    @staticmethod
    def _cognitive_load(goal: GoalInput) -> CognitiveLoad:
        hint = " ".join(filter(None, (goal.subject or "", goal.task_type or ""))).lower()
        for load, keywords in _COGNITIVE_KEYWORDS.items():
            if any(keyword in hint for keyword in keywords):
                return load
        return CognitiveLoad.LOW

    @staticmethod
    def _subtasks(
        idx: int, goal: GoalInput, analysis: GoalAnalysisResult | None
    ) -> list[str]:
        if analysis is not None and idx < len(analysis.goals):
            subtasks = analysis.goals[idx].subtasks
            if subtasks:
                return list(subtasks)
        return ["理解内容", "练习巩固", "总结复盘"]

    @staticmethod
    def _aggregate_load(items: list[TheoreticalItem]) -> CognitiveLoad:
        if not items:
            return CognitiveLoad.MEDIUM
        return max((item.cognitive_load for item in items), key=lambda load: _LOAD_RANK[load])

    def summarize(self, value: TheoreticalAnalysisResult) -> str:
        return f"{len(value.items)} item(s), {value.total_theoretical_minutes} min total"


__all__ = ["PROMPT_NAME", "WorkloadEstimatorInput", "WorkloadEstimatorTool"]
