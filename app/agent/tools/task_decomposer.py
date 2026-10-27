"""``task_decomposer`` tool - goals -> objective + subtasks.

LLM-backed (``llm_exposed=True``) with a deterministic heuristic fallback that
keeps the pipeline running when no model is configured.
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, Field

from app.agent.goal_identity import goal_index_for_ref
from app.agent.llm import StructuredLLM
from app.agent.schemas import (
    AnalyzedGoal,
    DecompositionStatus,
    GoalAnalysisResult,
    GoalKind,
    MissingInformation,
    RecurrenceSpec,
    WorkUnit,
)
from app.agent.state import GoalInput
from app.agent.tools.base import BaseTool
from app.domain.date_constraints import resolve_earliest_start
from app.domain.models.enums import PlanningMode
from app.domain.planning import (
    derive_planning_mode,
    derive_recurrence_interval,
)
from app.domain.recurrence import RecurrenceFrequency

PROMPT_NAME = "goal_analysis"


def _recurrence_for(goal: GoalInput) -> RecurrenceSpec:
    """Build the recurrence spec from explicit client metadata only (no regex)."""
    weekdays = sorted({int(day) for day in (goal.recurrence_weekdays or [])})
    interval = derive_recurrence_interval(goal.recurrence_interval)
    frequency = goal.recurrence_frequency
    if frequency is None:
        frequency = (
            RecurrenceFrequency.WEEKLY
            if 0 < len(weekdays) < 7
            else RecurrenceFrequency.DAILY
        )
    if frequency is RecurrenceFrequency.DAILY:
        return RecurrenceSpec(
            frequency=RecurrenceFrequency.DAILY,
            interval=interval,
            weekdays=[],
        )
    return RecurrenceSpec(
        frequency=RecurrenceFrequency.WEEKLY,
        interval=interval,
        weekdays=weekdays or None,
    )


def _classify(goal: GoalInput) -> tuple[GoalKind, RecurrenceSpec | None]:
    """Deterministic fallback classification from explicit goal metadata.

    ``planning_mode`` is the product-level 4-way value; the LLM schema keeps
    three semantic kinds, so ``project_recurring`` becomes ``project`` plus a
    recurrence. This never parses free text.
    """
    mode = derive_planning_mode(
        goal.planning_mode,
        goal_type=goal.goal_type,
        task_kind=goal.task_kind,
        recurrence_frequency=goal.recurrence_frequency,
        recurrence_weekdays=goal.recurrence_weekdays,
    )
    if mode is PlanningMode.ONE_OFF:
        return GoalKind.ONE_OFF, None
    if mode is PlanningMode.RECURRING:
        return GoalKind.RECURRING, _recurrence_for(goal)
    if mode is PlanningMode.PROJECT:
        return GoalKind.PROJECT, None
    return GoalKind.PROJECT, _recurrence_for(goal)


def _normalise(item: AnalyzedGoal, goal: GoalInput | None) -> AnalyzedGoal:
    """Make the analysis consistent with explicit planning_mode authority.

    Explicit user planning_mode wins over the LLM classification. One-off
    keeps its checklist as internal ``subtasks``; recurring is opaque; project
    keeps finite work units; project_recurring is project + recurrence.
    """
    updates: dict = {}
    explicit = goal.planning_mode if goal is not None else None

    if explicit is PlanningMode.ONE_OFF:
        updates.update(
            goal_kind=GoalKind.ONE_OFF,
            recurrence=None,
            work_units=[],
            decomposition_status=DecompositionStatus.READY,
            missing_information=[],
        )
    elif explicit is PlanningMode.RECURRING:
        updates.update(
            goal_kind=GoalKind.RECURRING,
            recurrence=item.recurrence or (_recurrence_for(goal) if goal else None),
            work_units=[],
            subtasks=[],
            decomposition_status=DecompositionStatus.READY,
            missing_information=[],
        )
    elif explicit is PlanningMode.PROJECT:
        updates.update(goal_kind=GoalKind.PROJECT, recurrence=None)
    elif explicit is PlanningMode.PROJECT_RECURRING:
        updates.update(
            goal_kind=GoalKind.PROJECT,
            recurrence=item.recurrence or (_recurrence_for(goal) if goal else None),
        )
    else:
        # Legacy / missing planning_mode: semantic normalization as before.
        if item.goal_kind is GoalKind.RECURRING:
            updates["work_units"] = []
            updates["subtasks"] = []
            if item.recurrence is None:
                updates["recurrence"] = _recurrence_for(goal) if goal else None
        elif item.goal_kind is GoalKind.PROJECT:
            if item.recurrence is None and goal is not None and (
                goal.recurrence_frequency is not None
                or bool(goal.recurrence_weekdays)
            ):
                updates["recurrence"] = _recurrence_for(goal)
        else:
            updates["recurrence"] = None
            updates["work_units"] = []

    draft = item.model_copy(update=updates) if updates else item

    # A project with no meaningful work units must ask the user; never fake a
    # unit from the goal title.
    if draft.goal_kind is GoalKind.PROJECT and not draft.work_units:
        if draft.decomposition_status is not DecompositionStatus.NEEDS_CLARIFICATION:
            draft = draft.model_copy(
                update={
                    "decomposition_status": DecompositionStatus.NEEDS_CLARIFICATION,
                    "missing_information": draft.missing_information
                    or [
                        MissingInformation(
                            field="curriculum",
                            question="这个项目/课程包含哪些阶段或主题？",
                        )
                    ],
                }
            )
    return draft


def _goal_text(goal: GoalInput) -> str:
    """Evidence text used by the deterministic date parser (never rewritten)."""
    parts = [goal.title, goal.description or ""]
    parts.extend(str(value) for value in (goal.clarifications or {}).values())
    return "\n".join(part for part in parts if part)


def _with_deterministic_earliest(item: AnalyzedGoal, goal: GoalInput) -> AnalyzedGoal:
    """Make an explicit textual date fact authoritative over the LLM.

    The LLM value (if any) is a candidate; the deterministic parser adds every
    supported explicit expression and the later day wins. Ambiguous or
    contradictory text raises instead of being ignored.
    """
    deadline = goal.deadline.date() if goal.deadline is not None else None
    earliest = resolve_earliest_start(
        item.earliest_start_date,
        text=_goal_text(goal),
        deadline=deadline,
        reference=goal.start_date or date.today(),
        source=(
            f"goal id={goal.existing_goal_id!r} title={goal.title!r}"
        ),
    )
    if earliest != item.earliest_start_date:
        return item.model_copy(update={"earliest_start_date": earliest})
    return item


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
            return self._finalise(fallback, payload)

        result = self._llm.complete_model(
            prompt_name=PROMPT_NAME,
            schema=GoalAnalysisResult,
            # Goal analysis must not see the user model / execution weight:
            # those may not change goal_kind, recurrence, curriculum or deadline.
            # Persisted ids are internal: the model must use request positions.
            variables={
                "goals": [
                    {
                        "goal_index": index,
                        **goal.model_dump(
                            mode="json", exclude={"existing_goal_id"}
                        ),
                    }
                    for index, goal in enumerate(payload.goals, start=1)
                ],
            },
            fallback=fallback,
        )
        value = result.value
        goals_by_key = {idx: goal for idx, goal in enumerate(payload.goals, start=1)}
        analyzed: list[AnalyzedGoal] = []
        for item in value.goals:
            index = goal_index_for_ref(item.goal_id, payload.goals)
            if index is None:
                # A single-goal request can safely attribute an echoed id.
                if len(payload.goals) == 1:
                    index = 1
                else:
                    continue
            goal = goals_by_key.get(index)
            item = item.model_copy(update={"goal_id": index})
            if goal is None or not goal.description:
                item = item.model_copy(update={"subtasks": []})
            analyzed.append(_normalise(item, goal))
        return self._finalise(
            value.model_copy(update={"goals": analyzed}), payload
        )

    @classmethod
    def _finalise(
        cls, result: GoalAnalysisResult, payload: TaskDecomposerInput
    ) -> GoalAnalysisResult:
        """Normalise local goal refs and apply deterministic date facts."""
        goals_by_key = {idx: goal for idx, goal in enumerate(payload.goals, start=1)}
        items: list[AnalyzedGoal] = []
        for item in result.goals:
            index = goal_index_for_ref(item.goal_id, payload.goals)
            if index is None:
                if len(payload.goals) == 1:
                    index = 1
                else:
                    continue
            goal = goals_by_key[index]
            item = item.model_copy(update={"goal_id": index})
            items.append(_with_deterministic_earliest(item, goal))
        return result.model_copy(update={"goals": items})

    @staticmethod
    def _heuristic(payload: TaskDecomposerInput) -> GoalAnalysisResult:
        """Deterministic fallback: split only user-provided supplement text."""
        analyzed: list[AnalyzedGoal] = []
        confidences: list[float] = []
        for idx, goal in enumerate(payload.goals, start=1):
            kind, recurrence = _classify(goal)
            subtasks = TaskDecomposerTool._subtasks(goal)
            work_units = (
                [
                    WorkUnit(
                        title=part,
                        estimated_minutes=goal.estimated_minutes or 60,
                    )
                    for part in subtasks
                ]
                if kind is GoalKind.PROJECT
                else []
            )
            # Clarifications are separate provenance; a curriculum answer can
            # unlock a project without concatenating it into the description.
            if kind is GoalKind.PROJECT and not work_units:
                curriculum = (goal.clarifications or {}).get("curriculum", "")
                parts = [
                    part.strip()
                    for part in re.split(r"[\n,，、;；]", curriculum)
                    if part.strip()
                ]
                if parts:
                    work_units = [
                        WorkUnit(
                            title=part,
                            estimated_minutes=goal.estimated_minutes or 60,
                        )
                        for part in parts
                    ]
            status = DecompositionStatus.READY
            missing: list[MissingInformation] = []
            if kind is GoalKind.PROJECT and not work_units:
                # Never fake a project unit from the goal title. Ask the user
                # for the curriculum/progress instead.
                status = DecompositionStatus.NEEDS_CLARIFICATION
                missing = [
                    MissingInformation(
                        field="curriculum",
                        question="这个项目/课程包含哪些阶段或主题？",
                    )
                ]
            item = AnalyzedGoal(
                # 1-based goal key; matches the provisional task id contract.
                goal_id=idx,
                title=goal.title,
                objective=goal.description or goal.title,
                subtasks=subtasks,
                constraints=[],
                goal_kind=kind,
                recurrence=recurrence,
                work_units=work_units,
                decomposition_status=status,
                missing_information=missing,
            )
            analyzed.append(_normalise(item, goal))
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
