"""``goal_analysis`` node: decompose goals into objective + subtasks.

MOCK implementation - deterministic heuristics only, no LLM call is ever made
in the default path. The optional ``llm`` argument is accepted for interface
compatibility with future real-LM agents but is unused here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.agent.schemas import AnalyzedGoal, GoalAnalysisResult
from app.agent.state import GoalInput, PlannerState

if TYPE_CHECKING:  # pragma: no cover
    from app.infrastructure.llm.client import LLMClient

#: 2-4 generic stages used when a goal has no description to split.
_GENERIC_STAGES: tuple[tuple[tuple[str, ...], list[str]], ...] = (
    (
        ("math", "数学", "算法", "algorithm", "408"),
        ["概念理解", "例题精做", "专项训练", "总结复盘"],
    ),
    (("english", "language", "英语", "语言"), ["词汇积累", "练习巩固", "总结复盘"]),
    (("reading", "writing", "阅读", "写作"), ["资料研读", "动笔输出", "修改复盘"]),
    (("exercise", "music", "锻炼", "练琴", "运动"), ["热身准备", "主体练习", "放松整理"]),
)

#: Fallback study stages when neither description nor a known subject is given.
_DEFAULT_STAGES: list[str] = ["理解内容", "练习巩固", "总结复盘"]


class GoalAnalysisAgent:
    """MOCK heuristic goal analyser.

    * ``objective`` = ``goal.description`` (or the title).
    * ``subtasks`` = description split on newlines / ``;`` / ``；``; otherwise
      2-4 generic stages derived from ``subject``/``task_type``; otherwise the
      default Chinese study stages.
    """

    name = "goal-analysis-mock-v0"

    def __init__(self, llm: LLMClient | None = None) -> None:
        # MOCK: accepted for interface compatibility, never called.
        self.llm = llm

    def run(
        self, goals: list[GoalInput], user_profile: dict | None = None
    ) -> GoalAnalysisResult:
        """Analyse every goal into an :class:`AnalyzedGoal`.

        MOCK heuristic; ``user_profile`` is accepted for interface symmetry but
        not consumed in the mock path.
        """
        analyzed: list[AnalyzedGoal] = []
        confidences: list[float] = []
        for idx, goal in enumerate(goals, start=1):
            objective = goal.description or goal.title
            analyzed.append(
                AnalyzedGoal(
                    # 1-based; matches the provisional task id (order_index + 1).
                    goal_id=idx,
                    title=goal.title,
                    objective=objective,
                    subtasks=self._subtasks(goal),
                    constraints=[],
                )
            )
            # MOCK confidence: a concrete time estimate signals a better-known goal.
            confidences.append(0.6 if goal.estimated_minutes is not None else 0.45)

        summary = f"Analyzed {len(analyzed)} goal(s)."
        confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.5
        return GoalAnalysisResult(goals=analyzed, summary=summary, confidence=confidence)

    @staticmethod
    def _subtasks(goal: GoalInput) -> list[str]:
        """Derive subtasks: split the description, else generic stages."""
        if goal.description:
            raw = goal.description.replace("；", ";")
            parts = [p.strip() for line in raw.split("\n") for p in line.split(";")]
            cleaned = [p for p in parts if p]
            if cleaned:
                return cleaned

        hint = " ".join(filter(None, (goal.subject or "", goal.task_type or ""))).lower()
        for keywords, stages in _GENERIC_STAGES:
            if any(kw in hint for kw in keywords):
                return list(stages)
        return list(_DEFAULT_STAGES)


def goal_analysis_node(state: PlannerState) -> dict:
    """Node function: run the MOCK goal analysis and write the state keys."""
    result = GoalAnalysisAgent().run(
        list(state.get("goals") or []), state.get("user_profile")
    )
    return {
        "goal_analysis": result,
        "notes": [f"goal_analysis: MOCK heuristic, confidence={result.confidence:.2f}."],
        "events": [
            {
                "node": "goal_analysis",
                "stage": "complete",
                "status": "ok",
                "summary": f"Analyzed {len(result.goals)} goal(s).",
            }
        ],
    }
