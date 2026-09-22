"""``plan_drafter`` tool - produce task drafts for the three planning modes.

* ``INITIAL``    - first plan from the theoretical workload + user situation
* ``ADJUSTMENT`` - apply one bounded user change to an existing preview
* ``REPLAN``     - rebuild from the full context after a FULL_REPLAN decision

LLM-backed (``llm_exposed=True``) with a deterministic fallback per mode. The
tool never emits scheduled dates or times: the scheduler owns placement.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, Field

from app.agent.llm import StructuredLLM
from app.agent.schemas import (
    GeneratedTaskDraft,
    PlanGenerationResult,
    PreviewPayload,
    UserSituationResult,
)
from app.agent.state import GoalInput, PreferenceInput
from app.agent.tools.base import BaseTool
from app.domain.models.enums import Priority, TimeOfDay
from app.ml.base import AdjustmentPrediction, PlanProgress

#: Deterministic adjustment keywords -> duration scale.
_SCALE_DOWN_RE = re.compile(r"太多|减少|少一点|少排|轻松|too much|less|reduce|overload", re.I)
_MORNING_RE = re.compile(r"上午|早上|morning", re.I)
_EVENING_RE = re.compile(r"晚上|evening|night", re.I)


class PlanDrafterMode(StrEnum):
    INITIAL = "INITIAL"
    ADJUSTMENT = "ADJUSTMENT"
    REPLAN = "REPLAN"


_PROMPT_BY_MODE: dict[PlanDrafterMode, str] = {
    PlanDrafterMode.INITIAL: "initial_plan",
    PlanDrafterMode.ADJUSTMENT: "adjustment",
    PlanDrafterMode.REPLAN: "replanning",
}


class PlanDrafterInput(BaseModel):
    mode: PlanDrafterMode = PlanDrafterMode.INITIAL
    title: str = "Adaptive Plan"
    goals: list[GoalInput] = Field(default_factory=list)
    user_situation: UserSituationResult | None = None
    theoretical: dict = Field(default_factory=dict)
    preferences: PreferenceInput | None = None

    # adjustment mode
    preview: PreviewPayload | None = None
    user_adjustment: str | None = None
    adjustment_count: int = 0

    # replan mode
    planning_context: str = ""
    ml_prediction: AdjustmentPrediction | None = None
    progress: PlanProgress | None = None
    replan_reason: str | None = None
    completed_task_titles: list[str] = Field(default_factory=list)
    #: Truthful origin of the per-task predictions (carried onto every draft).
    prediction_source: str | None = None


class PlanDrafterTool(BaseTool[PlanDrafterInput, PlanGenerationResult]):
    name = "plan_drafter"
    description = (
        "Produce structured task drafts for an initial plan, a bounded preview "
        "adjustment, or a full replan. Never returns dates or times."
    )
    llm_exposed = True

    def __init__(self, llm: StructuredLLM | None = None) -> None:
        self._llm = llm

    def prompt_name(self, mode: PlanDrafterMode) -> str:
        return _PROMPT_BY_MODE[mode]

    def run(self, payload: PlanDrafterInput) -> PlanGenerationResult:
        fallback = self._fallback(payload)
        if self._llm is None or not self._llm.enabled:
            return fallback

        result = self._llm.complete_model(
            prompt_name=self.prompt_name(payload.mode),
            schema=PlanGenerationResult,
            variables=self._prompt_variables(payload),
            fallback=fallback,
        )
        return result.value

    # -- prompt variables --------------------------------------------------
    @staticmethod
    def _prompt_variables(payload: PlanDrafterInput) -> dict[str, object]:
        return {
            "theoretical_analysis": payload.theoretical,
            "user_situation": (
                payload.user_situation.model_dump(mode="json")
                if payload.user_situation
                else {}
            ),
            "goals": [goal.model_dump(mode="json") for goal in payload.goals],
            "preferences": (
                payload.preferences.model_dump(mode="json") if payload.preferences else {}
            ),
            "preview": payload.preview.model_dump(mode="json") if payload.preview else {},
            "user_adjustment": payload.user_adjustment or "",
            "adjustment_count": payload.adjustment_count,
            "planning_context": payload.planning_context,
            "ml_prediction": (
                payload.ml_prediction.model_dump(mode="json") if payload.ml_prediction else {}
            ),
            "current_plan": (
                payload.preview.model_dump(mode="json") if payload.preview else {}
            ),
            "progress": payload.progress.model_dump(mode="json") if payload.progress else {},
            "replan_reason": payload.replan_reason or "",
        }

    # -- deterministic fallback -------------------------------------------
    @classmethod
    def _fallback(cls, payload: PlanDrafterInput) -> PlanGenerationResult:
        if payload.mode is PlanDrafterMode.ADJUSTMENT and payload.preview is not None:
            drafts = cls._adjust(
                cls._preview_to_drafts(payload.preview, payload.prediction_source),
                payload.user_adjustment,
            )
        else:
            drafts = cls._from_theoretical(payload)

        return PlanGenerationResult(
            title=payload.title,
            tasks=drafts,
            confidence=0.5,
        )

    @staticmethod
    def _from_theoretical(payload: PlanDrafterInput) -> list[GeneratedTaskDraft]:
        items = list(payload.theoretical.get("items") or [])
        situation = payload.user_situation
        completed = {title.strip().lower() for title in payload.completed_task_titles}
        drafts: list[GeneratedTaskDraft] = []

        for idx, item in enumerate(items):
            goal = payload.goals[idx] if idx < len(payload.goals) else None
            title = str(item.get("title", f"Task {idx + 1}"))
            if payload.mode is PlanDrafterMode.REPLAN and title.strip().lower() in completed:
                continue
            provisional_id = idx + 1
            total = int(item.get("total_minutes") or 60)
            predicted = None
            completion = None
            slot = None
            stress = None
            if situation is not None:
                predicted = situation.predicted_duration.get(provisional_id)
                completion = situation.predicted_completion_probability.get(provisional_id)
                stress = situation.stress_state
                slot = situation.recommended_time_slot
            if predicted is None:
                factor = situation.duration_factor if situation else 1.0
                predicted = max(1, round(total * factor))
            drafts.append(
                GeneratedTaskDraft(
                    title=title,
                    description=str(item.get("learning_content") or "") or None,
                    goal_id=idx + 1,
                    estimated_duration=total,
                    predicted_duration=predicted,
                    completion_probability=completion,
                    recommended_time_slot=slot,
                    predicted_stress=stress,
                    cognitive_load=item.get("cognitive_load") or "medium",
                    priority=goal.priority if goal else Priority.MEDIUM,
                    subject=goal.subject if goal else None,
                    standards=list(item.get("subtasks") or []),
                    deadline=goal.deadline if goal else None,
                    prediction_source=payload.prediction_source,
                    order_index=len(drafts),
                )
            )
        return drafts

    @staticmethod
    def _preview_to_drafts(
        preview: PreviewPayload, prediction_source: str | None = None
    ) -> list[GeneratedTaskDraft]:
        return [
            GeneratedTaskDraft(
                title=task.title,
                description=task.description,
                goal_id=task.goal_id,
                estimated_duration=task.estimated_duration,
                predicted_duration=task.predicted_duration,
                completion_probability=task.completion_probability,
                recommended_time_slot=task.recommended_time_slot,
                cognitive_load=task.cognitive_load,
                priority=task.priority,
                subject=task.subject,
                standards=list(task.standards),
                prediction_source=prediction_source,
                order_index=index,
            )
            for index, task in enumerate(preview.tasks)
        ]

    @staticmethod
    def _adjust(
        drafts: list[GeneratedTaskDraft], note: str | None
    ) -> list[GeneratedTaskDraft]:
        """Minimal deterministic adjustment: scale load and/or bias the slot."""
        if not note:
            return drafts

        scale = 0.8 if _SCALE_DOWN_RE.search(note) else 1.0
        prefer: TimeOfDay | None = None
        if _MORNING_RE.search(note):
            prefer = TimeOfDay.MORNING
        elif _EVENING_RE.search(note):
            prefer = TimeOfDay.EVENING

        adjusted: list[GeneratedTaskDraft] = []
        for index, draft in enumerate(drafts):
            estimated = max(5, round(draft.estimated_duration * scale))
            predicted = (
                max(5, round(draft.predicted_duration * scale))
                if draft.predicted_duration is not None
                else None
            )
            adjusted.append(
                draft.model_copy(
                    update={
                        "estimated_duration": estimated,
                        "predicted_duration": predicted,
                        "recommended_time_slot": prefer or draft.recommended_time_slot,
                        "order_index": index,
                    }
                )
            )
        return adjusted

    def summarize(self, value: PlanGenerationResult) -> str:
        return f"{len(value.tasks)} draft(s) [{self.name}]"


__all__ = ["PlanDrafterInput", "PlanDrafterMode", "PlanDrafterTool"]
