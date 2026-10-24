"""``task_estimator`` tool - deterministic production estimates.

This tool does **not** predict user behaviour. It passes through the
theory-derived workload estimate and observed Level 2 state so the production
plan remains honest when Level 3 is shadow-only:

* ``duration`` = the task's own estimated duration (no fabricated factor);
* ``completion`` = empty (the system does not invent a probability);
* ``stress`` = Level 2 stress projection when available;
* ``time_slot`` = the user's configured preference, never a model guess.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent.features import TaskFeatureSet, UserFeatureSet
from app.agent.tools.base import BaseTool
from app.domain.models.enums import TimeOfDay

SOURCE = "deterministic:workload_estimate"


class TaskEstimatorInput(BaseModel):
    task_features: list[TaskFeatureSet] = Field(default_factory=list)
    user: UserFeatureSet
    available_minutes: int | None = None


class TaskEstimates(BaseModel):
    duration: dict[int, int] = Field(default_factory=dict)
    #: Deliberately empty: no production model emits completion probability.
    completion: dict[int, float] = Field(default_factory=dict)
    stress: dict[int, float] = Field(default_factory=dict)
    time_slot: dict[int, TimeOfDay] = Field(default_factory=dict)
    overall_stress: float | None = None
    should_reduce_load: bool = False
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = SOURCE


class TaskEstimatorTool(BaseTool[TaskEstimatorInput, TaskEstimates]):
    name = "task_estimator"
    description = (
        "Deterministic workload estimates: pass through the theory-derived "
        "duration and observed Level 2 stress. Never fabricates a completion "
        "probability; Level 3 runs in shadow mode only."
    )
    llm_exposed = False

    def run(self, payload: TaskEstimatorInput) -> TaskEstimates:
        result = TaskEstimates()
        slot = _preferred_slot(payload.user.preferred_time_slots)
        for features in payload.task_features:
            result.duration[features.task_id] = max(
                1, int(round(features.estimated_duration_minutes))
            )
            if payload.user.avg_stress is not None:
                result.stress[features.task_id] = float(payload.user.avg_stress)
            if slot is not None:
                result.time_slot[features.task_id] = slot

        result.overall_stress = payload.user.avg_stress
        result.should_reduce_load = bool(
            (payload.user.avg_stress is not None and payload.user.avg_stress >= 8.0)
            or (payload.user.avg_energy is not None and payload.user.avg_energy <= 2.0)
        )
        result.confidence = 0.5
        result.source = SOURCE
        return result

    def summarize(self, value: TaskEstimates) -> str:
        return f"{len(value.duration)} task(s), source={value.source}"


def _preferred_slot(slots: dict[str, str]) -> TimeOfDay | None:
    for key in slots:
        try:
            return TimeOfDay(str(key).strip().lower())
        except ValueError:
            continue
    return None


__all__ = ["SOURCE", "TaskEstimates", "TaskEstimatorInput", "TaskEstimatorTool"]