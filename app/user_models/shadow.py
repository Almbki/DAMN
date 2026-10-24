"""Level 3 Shadow Mode.

``shadow`` means: run the real model on the same auditable input, validate the
output, persist it, and **never** feed it back into the production decision.

Invariant: production output with shadow enabled == production output with
shadow disabled, for the same inputs and deterministic dependencies. The runner
is called only after the production plan has been persisted; it cannot mutate
state, the scheduler, or the rule engine.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.user_models.artifacts import sha256_json
from app.user_models.contracts import (
    DynamicStateSnapshot,
    HistoryBundle,
    Level3Mode,
    ModelLevel,
    TaskPredictionContext,
    TraitSnapshot,
)
from app.user_models.runtime import UserModelRuntime

logger = logging.getLogger(__name__)


class ShadowPredictionRecord(BaseModel):
    """One auditable shadow inference (persisted to ``shadow_predictions``)."""

    model_config = ConfigDict(extra="forbid")

    user_id: int
    plan_id: int | None = None
    task_id: int | None = None
    inference_timestamp: datetime
    model_level: str = ModelLevel.LEVEL3.value
    model_version: str = ""
    artifact_hash: str = ""
    artifact_version: str = ""
    feature_version: str = ""
    input_hash: str = ""
    input_summary: dict[str, Any] = Field(default_factory=dict)
    production_decision: dict[str, Any] = Field(default_factory=dict)
    shadow_prediction: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None
    uncertainty: float | None = None
    disagreement: float | None = None
    latency_ms: int = 0
    success: bool = True
    failure_reason: str | None = None
    degraded: bool = False
    mode: str = Level3Mode.SHADOW.value
    #: real | synthetic - synthetic shadow rows must not enter real evaluation.
    data_origin: str = "real"


class Level3ShadowRunner:
    """Runs Level 3 for logging only. Every failure is contained."""

    def __init__(self, runtime: UserModelRuntime) -> None:
        self.runtime = runtime

    def run(
        self,
        *,
        user_id: int,
        plan_id: int | None,
        task_id: int | None,
        trait: TraitSnapshot,
        state: DynamicStateSnapshot,
        history: HistoryBundle,
        task: TaskPredictionContext,
        production_decision: dict[str, Any],
        timestamp: datetime | None = None,
        data_origin: str = "real",
    ) -> ShadowPredictionRecord | None:
        """Return a record to persist, or ``None`` when Level 3 is off."""
        if self.runtime.mode is Level3Mode.OFF:
            return None

        started = time.perf_counter()
        inferred_at = timestamp or datetime.now(UTC)
        record = ShadowPredictionRecord(
            user_id=user_id,
            plan_id=plan_id,
            task_id=task_id,
            inference_timestamp=inferred_at,
            production_decision=dict(production_decision),
            mode=self.runtime.mode.value,
            degraded=self.runtime.mode_reason is not None,
            data_origin=data_origin,
        )
        try:
            inp = self.runtime.build_level3_input(
                trait=trait,
                state=state,
                task=task,
                history=history,
                prediction_timestamp=inferred_at,
            )
            record.input_hash = sha256_json(inp)
            record.input_summary = {
                "task_id": task.task_id,
                "estimated_duration_minutes": task.estimated_duration_minutes,
                "history_total": history.total_historical_tasks,
                "history_usable_duration": history.usable_duration_samples,
                "state_date": state.date.isoformat(),
                "level1_version": trait.model_version,
                "level2_version": state.model_version,
            }
            prediction = self.runtime.predict_level3(inp)
            meta = self.runtime.level3.metadata
            record.model_version = prediction.model_version or meta.model_version
            record.artifact_hash = meta.artifact_hash
            record.artifact_version = meta.artifact_version
            record.feature_version = meta.feature_version
            record.shadow_prediction = prediction.model_dump(mode="json")
            record.uncertainty = prediction.completion_uncertainty
            record.confidence = None  # the model does not emit a calibrated confidence
            record.disagreement = _disagreement(
                prediction.completion_probability,
                prediction.predicted_duration_minutes,
                production_decision,
            )
            record.degraded = prediction.degraded or record.degraded
        except Exception as exc:  # noqa: BLE001 - shadow must never break production
            record.success = False
            record.failure_reason = f"{type(exc).__name__}: {exc}"[:500]
            record.degraded = True
            logger.warning(
                "level3 shadow inference failed for user=%s task=%s: %s",
                user_id,
                task_id,
                exc,
            )
        finally:
            record.latency_ms = max(0, int((time.perf_counter() - started) * 1000))
        return record


def _disagreement(
    shadow_completion: float | None,
    shadow_duration: float | None,
    production_decision: dict[str, Any],
) -> float | None:
    """Symmetric, bounded disagreement between production and shadow."""
    production_completion = production_decision.get("completion_probability")
    if shadow_completion is not None and production_completion is not None:
        return round(abs(float(shadow_completion) - float(production_completion)), 6)
    production_duration = production_decision.get("predicted_duration")
    if shadow_duration is not None and production_duration not in (None, 0):
        return round(
            abs(float(shadow_duration) - float(production_duration))
            / max(float(production_duration), 1.0),
            6,
        )
    return None


__all__ = ["Level3ShadowRunner", "ShadowPredictionRecord"]