"""``task_duration_predictor`` tool - ML predictions for a task set.

Thin adapter over the injected :class:`~app.ml.predictors.PredictorSet`. The
tool owns no model: it is the stable seam the ML team implements behind.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent.tools.base import BaseTool
from app.domain.models.enums import TimeOfDay
from app.ml.base import PredictionRequest, TaskFeatureSet, UserFeatureSet
from app.ml.predictors import PredictorSet


class TaskPredictions(BaseModel):
    """Per-task predictions plus the aggregates the pipeline needs."""

    duration: dict[int, int] = Field(default_factory=dict)
    completion: dict[int, float] = Field(default_factory=dict)
    stress: dict[int, float] = Field(default_factory=dict)
    time_slot: dict[int, TimeOfDay] = Field(default_factory=dict)
    overall_stress: float = 5.0
    should_reduce_load: bool = False
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    #: Truthful origin of the numbers (``mock:statistical`` / ``llm`` / ``xgb`` ...).
    source: str = "unknown"


class TaskDurationPredictorInput(BaseModel):
    task_features: list[TaskFeatureSet] = Field(default_factory=list)
    user: UserFeatureSet
    available_minutes: int | None = None


class TaskDurationPredictorTool(BaseTool[TaskDurationPredictorInput, TaskPredictions]):
    name = "task_duration_predictor"
    description = (
        "Predict per-task duration, completion probability, stress and the "
        "recommended time slot through the ML predictor interfaces."
    )
    llm_exposed = False

    def __init__(self, predictors: PredictorSet | None = None) -> None:
        self._predictors = predictors or PredictorSet.default()

    @property
    def predictors(self) -> PredictorSet:
        return self._predictors

    def run(self, payload: TaskDurationPredictorInput) -> TaskPredictions:
        result = TaskPredictions()
        confidences: list[float] = []
        stress_values: list[float] = []
        sources: set[str] = set()

        for features in payload.task_features:
            request = PredictionRequest(
                task=features,
                user=payload.user,
                available_minutes=payload.available_minutes,
            )
            duration = self._predictors.duration.predict(request)
            completion = self._predictors.completion.predict(request)
            stress = self._predictors.stress.predict(request)
            slot = self._predictors.time_slot.predict(request)

            result.duration[features.task_id] = duration.predicted_minutes
            result.completion[features.task_id] = completion.probability
            result.stress[features.task_id] = stress.predicted_stress
            result.time_slot[features.task_id] = slot.recommended_slot

            confidences.extend(
                [duration.confidence, completion.confidence, stress.confidence, slot.confidence]
            )
            stress_values.append(stress.predicted_stress)
            result.should_reduce_load = result.should_reduce_load or stress.should_reduce_load
            sources.update({duration.source, completion.source, stress.source, slot.source})

        if stress_values:
            result.overall_stress = round(sum(stress_values) / len(stress_values), 4)
        if confidences:
            result.confidence = round(sum(confidences) / len(confidences), 4)
        result.source = ",".join(sorted(sources)) if sources else "unknown"
        return result

    def summarize(self, value: TaskPredictions) -> str:
        return f"{len(value.duration)} task(s), source={value.source}"


__all__ = [
    "TaskDurationPredictorInput",
    "TaskDurationPredictorTool",
    "TaskPredictions",
]
