"""Statistical user-model builder (mock, no trained ML models).

Simple statistics, NOT a trained ML model. The builder aggregates historical
``TaskExecution`` and ``Feedback`` records into per-cognitive-load buckets:

* ``duration_factors``        = mean(actual / planned) of completed executions,
  blended toward ``1.0`` by ``execution_weight`` (fallback ``1.0``);
* ``completion_probability``  = mean of ``completion_rate`` per bucket;
* ``stress_response``         = mean(stress_after - stress_before);
* ``preferred_time_slots``    = modal ``time_of_day`` per bucket (fallback:
  modal ``Feedback.dominant_time_of_day``).

The :class:`~app.ml.base.UserFeatureSet` conversion mirrors these stats so the
Service layer can consume either shape. Everything is replaceable: the
interface is stable and a real trained model can populate the same fields
without touching the Service / API layers.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from app.domain.models import Feedback, TaskExecution, UserModel
from app.domain.models.enums import CognitiveLoad, TimeOfDay
from app.ml.base import UserFeatureSet


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class StatisticalUserModelBuilder:
    """Derives a ``UserModel`` from historical data.

    .. note::
        This is a plain aggregator of simple statistics and **not** a trained
        ML model. It is deterministic, synchronous and fully replaceable (the
        ``build`` / ``to_features`` interface is the stable contract).
    """

    def build(
        self,
        executions: list[TaskExecution],
        feedback: list[Feedback],
        *,
        user_id: int,
        execution_weight: float = 0.5,
        model_version: str = "statistical-v0",
        task_loads: dict[int, CognitiveLoad] | None = None,
    ) -> UserModel:
        """Aggregate executions + feedback into a ``UserModel``.

        ``task_loads`` maps task id -> cognitive load; executions whose task is
        unknown default to ``CognitiveLoad.MEDIUM``.
        """
        task_loads = task_loads or {}
        bucket_of = lambda ex: task_loads.get(ex.task_id, CognitiveLoad.MEDIUM)  # noqa: E731

        ratio_by_load: dict[str, list[float]] = defaultdict(list)
        completion_by_load: dict[str, list[float]] = defaultdict(list)
        stress_by_load: dict[str, list[float]] = defaultdict(list)
        slot_by_load: dict[str, list[TimeOfDay]] = defaultdict(list)

        for ex in executions:
            bucket = bucket_of(ex).value
            completion_by_load[bucket].append(ex.completion_rate)
            if ex.completed and ex.planned_duration > 0 and ex.actual_duration is not None:
                ratio_by_load[bucket].append(ex.actual_duration / ex.planned_duration)
            if ex.stress_before is not None and ex.stress_after is not None:
                stress_by_load[bucket].append(
                    float(ex.stress_after - ex.stress_before)
                )
            if ex.time_of_day is not None:
                slot_by_load[bucket].append(ex.time_of_day)

        buckets = sorted(completion_by_load.keys())

        # Fallback modal dominant slot across feedback.
        dominant_counter = Counter(
            f.dominant_time_of_day for f in feedback if f.dominant_time_of_day is not None
        )
        dominant_slot = (
            dominant_counter.most_common(1)[0][0] if dominant_counter else None
        )

        duration_factors: dict[str, float] = {}
        completion_probability: dict[str, float] = {}
        stress_response: dict[str, float] = {}
        preferred_time_slots: dict[str, str] = {}

        for bucket in buckets:
            ratios = ratio_by_load.get(bucket, [])
            if ratios:
                # Blend toward 1.0 by execution_weight (mock smoothing).
                raw = sum(ratios) / len(ratios)
                duration_factors[bucket] = round(
                    execution_weight * raw + (1.0 - execution_weight) * 1.0, 4
                )
            else:
                duration_factors[bucket] = 1.0

            rates = completion_by_load.get(bucket, [])
            if rates:
                completion_probability[bucket] = round(sum(rates) / len(rates), 4)

            deltas = stress_by_load.get(bucket, [])
            if deltas:
                stress_response[bucket] = round(sum(deltas) / len(deltas), 4)

            slot_counts = Counter(slot_by_load.get(bucket, []))
            if slot_counts:
                preferred_time_slots[bucket] = slot_counts.most_common(1)[0][0].value
            elif dominant_slot is not None:
                preferred_time_slots[bucket] = dominant_slot.value

        return UserModel(
            user_id=user_id,
            model_version=model_version,
            duration_factors=duration_factors,
            completion_probability=completion_probability,
            stress_response=stress_response,
            preferred_time_slots=preferred_time_slots,
            sample_size=len(executions),
            updated_at=datetime.now(UTC),
        )

    def to_features(
        self,
        model: UserModel | None,
        executions: list[TaskExecution],
        feedback: list[Feedback],
        *,
        user_id: int,
        execution_weight: float = 0.5,
    ) -> UserFeatureSet:
        """Derive a :class:`~app.ml.base.UserFeatureSet` from raw records.

        .. note::
            Simple statistics (means over windows), not a trained model. Falls
            back to ``model`` values when fresh data is missing.
        """
        # duration_factor: mean actual/planned; fallback model dict mean; else 1.0.
        ratios = [
            ex.actual_duration / ex.planned_duration
            for ex in executions
            if ex.completed
            and ex.planned_duration > 0
            and ex.actual_duration is not None
        ]
        duration_factor = 1.0
        if ratios:
            duration_factor = sum(ratios) / len(ratios)
        elif model is not None and model.duration_factors:
            duration_factor = sum(model.duration_factors.values()) / len(
                model.duration_factors
            )

        # completion rates over trailing 7d / 30d windows.
        now = datetime.now(UTC)

        def _within(value: datetime | None, days: int) -> bool:
            utc_value = _as_utc(value)
            return utc_value is not None and now - utc_value <= timedelta(days=days)

        rates_7d = [e.completion_rate for e in executions if _within(e.created_at, 7)]
        rates_30d = [e.completion_rate for e in executions if _within(e.created_at, 30)]
        completion_rate_7d = _mean(rates_7d) or 0.7
        completion_rate_30d = _mean(rates_30d) or 0.7

        stresses = [f.stress_level for f in feedback if f.stress_level is not None]
        energies = [f.energy_level for f in feedback if f.energy_level is not None]
        sleeps = [f.sleep_hours for f in feedback if f.sleep_hours is not None]
        avg_stress = _mean([float(s) for s in stresses]) or 5.0
        avg_energy = _mean([float(e) for e in energies]) or 5.0
        sleep_hours = _mean([float(s) for s in sleeps])
        preferred_time_slots = model.preferred_time_slots if model is not None else {}

        return UserFeatureSet(
            user_id=user_id,
            duration_factor=round(duration_factor, 4),
            completion_rate_7d=round(completion_rate_7d, 4),
            completion_rate_30d=round(completion_rate_30d, 4),
            avg_stress=round(avg_stress, 4),
            avg_energy=round(avg_energy, 4),
            sleep_hours=sleep_hours,
            preferred_time_slots=dict(preferred_time_slots),
            sample_size=len(executions),
            execution_weight=execution_weight,
        )