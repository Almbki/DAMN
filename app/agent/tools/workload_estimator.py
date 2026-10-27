"""``workload_estimator`` tool - theoretical workload per goal.

LLM-backed (``llm_exposed=True``) with a deterministic subject/keyword fallback.
This is the *theory* side: it must not personalise to the individual user.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent.goal_identity import goal_index_for_ref
from app.agent.llm import StructuredLLM
from app.agent.schemas import (
    GoalAnalysisResult,
    GoalKind,
    TheoreticalAnalysisResult,
    TheoreticalItem,
)
from app.agent.state import GoalInput
from app.agent.tools.base import BaseTool
from app.domain.models.enums import CognitiveLoad, PlanningMode
from app.domain.planning import derive_planning_mode
from app.domain.workload import normalise_total_minutes, rescale_split

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
        fallback = self._normalise_result(self._heuristic(payload), payload)
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
                # No user_profile: theoretical workload must not be
                # personalised (Level 1/2 only affect later adaptation).
            },
            fallback=fallback,
        )
        return self._normalise_result(result.value, payload)

    @classmethod
    def _normalise_result(
        cls, result: TheoreticalAnalysisResult, payload: WorkloadEstimatorInput
    ) -> TheoreticalAnalysisResult:
        """Bound LLM totals before they become a single execution block."""
        items: list[TheoreticalItem] = []
        for index, item in enumerate(result.items, start=1):
            resolved = goal_index_for_ref(item.goal_id, payload.goals)
            if resolved is not None and resolved != item.goal_id:
                item = item.model_copy(update={"goal_id": resolved})
            goal = (
                payload.goals[item.goal_id - 1]
                if item.goal_id is not None and 0 < item.goal_id <= len(payload.goals)
                else (payload.goals[index - 1] if index <= len(payload.goals) else None)
            )
            mode = (
                derive_planning_mode(
                    goal.planning_mode,
                    goal_type=goal.goal_type,
                    task_kind=goal.task_kind,
                    recurrence_frequency=goal.recurrence_frequency,
                    recurrence_weekdays=goal.recurrence_weekdays,
                )
                if goal is not None
                else PlanningMode.ONE_OFF
            )
            explicit = (
                goal.estimated_minutes
                if goal is not None and mode is PlanningMode.ONE_OFF
                else None
            )
            total = normalise_total_minutes(
                mode=mode,
                total_minutes=item.total_minutes,
                explicit_minutes=explicit,
                cognitive_load=item.cognitive_load,
            )
            video, reading, practice = rescale_split(
                total,
                item.video_minutes,
                item.reading_minutes,
                item.practice_minutes,
            )
            items.append(
                item.model_copy(
                    update={
                        "video_minutes": video,
                        "reading_minutes": reading,
                        "practice_minutes": practice,
                        "total_minutes": total,
                        "subtasks": [] if mode is PlanningMode.RECURRING else item.subtasks,
                    }
                )
            )

        total_minutes = sum(item.total_minutes for item in items)
        overall = (
            round(sum(item.difficulty for item in items) / len(items), 4)
            if items
            else 3.0
        )
        return result.model_copy(
            update={
                "items": items,
                "total_theoretical_minutes": total_minutes,
                "overall_difficulty": overall,
                "cognitive_load": cls._aggregate_load(items),
            }
        )

    @classmethod
    def _heuristic(cls, payload: WorkloadEstimatorInput) -> TheoreticalAnalysisResult:
        items: list[TheoreticalItem] = []
        analysis_by_goal: dict[int, object] = {}
        for item in payload.goal_analysis.goals if payload.goal_analysis else []:
            resolved = goal_index_for_ref(item.goal_id, payload.goals)
            if resolved is not None:
                analysis_by_goal[resolved] = item
        for idx, goal in enumerate(payload.goals, start=1):
            analyzed = analysis_by_goal.get(idx)
            load = cls._cognitive_load(goal)

            if analyzed is not None and analyzed.goal_kind is GoalKind.PROJECT:
                # Project workload is per work unit, not one goal-level blob.
                units = list(analyzed.work_units)
                if not units:
                    # Clarification / fail-closed path: do not fabricate a unit.
                    continue
                for unit_idx, unit in enumerate(units):
                    total = max(1, int(unit.estimated_minutes))
                    video, reading, practice = cls._split(total)
                    items.append(
                        TheoreticalItem(
                            title=unit.title,
                            goal_id=idx,
                            work_unit_index=unit_idx,
                            learning_content=unit.description or unit.title,
                            subtasks=[],
                            video_minutes=video,
                            reading_minutes=reading,
                            practice_minutes=practice,
                            total_minutes=total,
                            difficulty=_DIFFICULTY_BY_LOAD[load],
                            cognitive_load=load,
                        )
                    )
                continue

            total, (video, reading, practice) = cls._workload(goal)
            if analyzed is not None and analyzed.goal_kind is GoalKind.RECURRING:
                # One reusable occurrence, never the whole 249-day lifecycle.
                total = int(goal.daily_target_minutes or total)
                video, reading, practice = cls._split(total)
                subtasks: list[str] = []
            else:
                subtasks = cls._subtasks(idx - 1, goal, payload.goal_analysis)
            items.append(
                TheoreticalItem(
                    title=goal.title,
                    goal_id=idx,
                    learning_content=goal.description or goal.title,
                    subtasks=subtasks,
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
    def _split(total: int) -> tuple[int, int, int]:
        video = round(total * 0.3)
        reading = round(total * 0.3)
        return video, reading, total - video - reading

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
        """Never invent steps when the user did not add supplement content."""
        if analysis is not None and idx < len(analysis.goals):
            return list(analysis.goals[idx].subtasks)
        return []

    @staticmethod
    def _aggregate_load(items: list[TheoreticalItem]) -> CognitiveLoad:
        if not items:
            return CognitiveLoad.MEDIUM
        return max((item.cognitive_load for item in items), key=lambda load: _LOAD_RANK[load])

    def summarize(self, value: TheoreticalAnalysisResult) -> str:
        return f"{len(value.items)} item(s), {value.total_theoretical_minutes} min total"


__all__ = ["PROMPT_NAME", "WorkloadEstimatorInput", "WorkloadEstimatorTool"]
