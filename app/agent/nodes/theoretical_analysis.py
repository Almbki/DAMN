"""``theoretical_analysis`` node: theory-derived workload estimates (MOCK).

One :class:`~app.agent.schemas.TheoreticalItem` is produced per goal. When the
goal carries an explicit time estimate the workload is split 30% video / 30%
reading / 40% practice; otherwise a subject/task_type default table applies.
"""

from __future__ import annotations

from app.agent.schemas import (
    GoalAnalysisResult,
    TheoreticalAnalysisResult,
    TheoreticalItem,
)
from app.agent.state import GoalInput, PlannerState
from app.domain.models.enums import CognitiveLoad

#: cognitive_load keyword map (case-insensitive substring match on subject/task_type).
_COGNITIVE_KEYWORDS: dict[CognitiveLoad, tuple[str, ...]] = {
    CognitiveLoad.HIGH: ("math", "algorithm", "数学", "算法", "408", "物理"),
    CognitiveLoad.MEDIUM: ("英语", "线代", "编程", "programming"),
    CognitiveLoad.RESTORATIVE: ("锻炼", "练琴", "休息", "rest", "music", "exercise"),
}

#: MOCK difficulty per load bucket (4.0 HIGH / 3.0 MEDIUM / 2.0 LOW; RESTORATIVE is light).
_DIFFICULTY_BY_LOAD: dict[CognitiveLoad, float] = {
    CognitiveLoad.HIGH: 4.0,
    CognitiveLoad.MEDIUM: 3.0,
    CognitiveLoad.LOW: 2.0,
    CognitiveLoad.RESTORATIVE: 2.0,
}

#: Default workload when ``estimated_minutes`` is absent:
#: (keywords, total_minutes, (video, reading, practice))
_TIME_DEFAULTS: tuple[tuple[tuple[str, ...], int, tuple[int, int, int]], ...] = (
    (("math", "algorithm", "数学", "算法", "408"), 120, (30, 30, 60)),  # practice-heavy
    (("english", "language", "英语", "语言"), 60, (20, 30, 10)),
    (("reading", "writing", "阅读", "写作"), 90, (10, 50, 30)),
)

#: Fallback used when no subject/task_type hints are present.
_FALLBACK_TOTAL = 90
_FALLBACK_SPLIT: tuple[int, int, int] = (30, 30, 30)

#: Severity order used to aggregate the workload-level load.
_LOAD_RANK = {
    CognitiveLoad.RESTORATIVE: 0,
    CognitiveLoad.LOW: 1,
    CognitiveLoad.MEDIUM: 2,
    CognitiveLoad.HIGH: 3,
}


class TheoreticalAnalysisAgent:
    """MOCK workload estimator - one :class:`TheoreticalItem` per goal."""

    name = "theoretical-analysis-mock-v0"

    def run(
        self,
        goals: list[GoalInput],
        analysis: GoalAnalysisResult | None = None,
    ) -> TheoreticalAnalysisResult:
        """Estimate the theoretical workload for every goal.

        MOCK heuristic: explicit estimates are split 30/30/40; otherwise the
        subject/task_type default table applies. ``analysis`` (optional) is
        used only to reuse the decomposed subtasks.
        """
        items: list[TheoreticalItem] = []
        for idx, goal in enumerate(goals):
            total, (video, reading, practice) = self._workload(goal)
            load = self._cognitive_load(goal)
            items.append(
                TheoreticalItem(
                    title=goal.title,
                    learning_content=goal.description or goal.title,
                    subtasks=self._subtasks(idx, goal, analysis),
                    video_minutes=video,
                    reading_minutes=reading,
                    practice_minutes=practice,
                    total_minutes=total,
                    difficulty=_DIFFICULTY_BY_LOAD[load],
                    cognitive_load=load,
                )
            )

        total_minutes = sum(item.total_minutes for item in items)
        overall_difficulty = (
            round(sum(item.difficulty for item in items) / len(items), 4) if items else 3.0
        )
        return TheoreticalAnalysisResult(
            items=items,
            total_theoretical_minutes=total_minutes,
            overall_difficulty=overall_difficulty,
            cognitive_load=self._aggregate_load(items),
            confidence=0.5,  # MOCK: fixed heuristic confidence
        )

    @staticmethod
    def _workload(goal: GoalInput) -> tuple[int, tuple[int, int, int]]:
        """Return ``(total_minutes, (video, reading, practice))``."""
        if goal.estimated_minutes is not None:
            total = goal.estimated_minutes
            video = round(total * 0.3)
            reading = round(total * 0.3)
            practice = total - video - reading  # 30/30/40 split, exact sum
            return total, (video, reading, practice)

        hint = " ".join(filter(None, (goal.subject or "", goal.task_type or ""))).lower()
        for keywords, total, split in _TIME_DEFAULTS:
            if any(kw in hint for kw in keywords):
                return total, split
        return _FALLBACK_TOTAL, _FALLBACK_SPLIT

    @staticmethod
    def _cognitive_load(goal: GoalInput) -> CognitiveLoad:
        """Keyword map lookup; no match => LOW (MOCK)."""
        hint = " ".join(filter(None, (goal.subject or "", goal.task_type or ""))).lower()
        for load, keywords in _COGNITIVE_KEYWORDS.items():
            if any(kw in hint for kw in keywords):
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
        """Most demanding load present, else MEDIUM (schema default)."""
        if not items:
            return CognitiveLoad.MEDIUM
        return max((item.cognitive_load for item in items), key=lambda load: _LOAD_RANK[load])


def theoretical_analysis_node(state: PlannerState) -> dict:
    """Node function: estimate the theoretical workload for the goals."""
    agent = state.get("theoretical_agent") or TheoreticalAnalysisAgent()
    result = agent.run(list(state.get("goals") or []), state.get("goal_analysis"))
    return {
        "theoretical_workload": result,
        "notes": [
            f"theoretical_analysis: {len(result.items)} item(s), "
            f"{result.total_theoretical_minutes} min total, confidence={result.confidence:.2f}."
        ],
    }
