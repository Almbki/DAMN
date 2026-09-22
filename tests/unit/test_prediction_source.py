"""Regression guards for prediction provenance.

``GeneratedTaskDraft.prediction_source`` is part of the LLM output schema, so a
successful model call used to let the LLM invent the provenance of the numbers
(observed: ``"user_situation (duration_factor=1.5528, completion_ability=0.65,
stress=7.0)"``). That value overflowed ``prediction_logs.source`` (VARCHAR(64))
and raised ``StringDataRightTruncation``, aborting the whole confirm request.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.agent.schemas import GeneratedTaskDraft, PlanGenerationResult
from app.agent.tools.plan_drafter import (
    PlanDrafterInput,
    PlanDrafterMode,
    PlanDrafterTool,
)
from app.application.services.plan_service import PlanService

#: The exact free-text source the LLM produced in production (73 chars).
LLM_INVENTED_SOURCE = (
    "user_situation (duration_factor=1.5528, completion_ability=0.65, stress=7.0)"
)


class _StubLLM:
    enabled = True

    def __init__(self, value: PlanGenerationResult) -> None:
        self._value = value

    def complete_model(self, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(value=self._value, used_llm=True)


def test_llm_path_stamps_the_truthful_prediction_source() -> None:
    generated = PlanGenerationResult(
        title="T",
        tasks=[
            GeneratedTaskDraft(
                title="复习高数极限",
                prediction_source=LLM_INVENTED_SOURCE,
                predicted_duration=90,
                order_index=0,
            )
        ],
    )
    tool = PlanDrafterTool(llm=_StubLLM(generated))  # type: ignore[arg-type]
    payload = PlanDrafterInput(
        mode=PlanDrafterMode.INITIAL,
        prediction_source="mock:statistical",
    )

    result = tool.run(payload)

    # The LLM does not get to author provenance; the ML predictor's source wins.
    assert result.tasks[0].prediction_source == "mock:statistical"


def test_truthful_source_override_handles_no_tasks() -> None:
    tool = PlanDrafterTool(llm=_StubLLM(PlanGenerationResult(title="T")))  # type: ignore[arg-type]
    result = tool.run(PlanDrafterInput(prediction_source="mock:statistical"))
    assert result.tasks == []


def test_prediction_source_is_capped_to_the_column_width() -> None:
    capped = PlanService._short_source(LLM_INVENTED_SOURCE)
    assert len(capped) == 64
    assert capped == LLM_INVENTED_SOURCE[:64]
    assert len(LLM_INVENTED_SOURCE) > 64  # the bug this guards against


def test_short_source_falls_back_to_unknown() -> None:
    assert PlanService._short_source(None) == "unknown"
    assert PlanService._short_source("   ") == "unknown"
    assert PlanService._short_source("  mock:statistical  ") == "mock:statistical"
