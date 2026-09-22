"""Offline evaluation of the registered predictions.

Joins ``prediction_logs`` (what a predictor said) with ``task_executions`` (what
actually happened) and reports honest, sample-size-aware metrics. This is the
tool that answers "is the model any good?" *before* switching a user from the
statistical fallbacks to a trained model.

Usage::

    uv run python scripts/evaluate_predictors.py
    uv run python scripts/evaluate_predictors.py --user-id 3
    uv run python scripts/evaluate_predictors.py --min-samples 5

Scoring rules
-------------
* duration  -> MAE of ``predicted_minutes`` vs ``TaskExecution.actual_duration``
  (rows with a NULL actual are counted in ``missing``).
* completion -> MAE and Brier of ``probability`` vs the observed
  ``TaskExecution.completion_rate`` (the closest outcome record the app keeps).
* stress    -> MAE of ``predicted_stress`` vs ``TaskExecution.stress_after``.
* time_slot -> error rate (0 = the recommended slot always matched the recorded
  ``time_of_day``).

Lower is better for every metric.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from statistics import mean

from app.core.config import get_settings
from app.domain.models import PredictionLog, TaskExecution
from app.infrastructure.database import SessionLocal
from app.infrastructure.database.repositories import (
    PredictionLogRepository,
    TaskExecutionRepository,
)


@dataclass
class Metric:
    name: str
    values: list[float] = field(default_factory=list)
    missing: int = 0

    @property
    def n(self) -> int:
        return len(self.values)

    @property
    def value(self) -> float | None:
        return round(mean(self.values), 4) if self.values else None

    def render(self) -> str:
        if self.n == 0:
            return f"{self.name:<24} n=0     no scored predictions"
        return f"{self.name:<24} n={self.n:<5} {self.value:.4f}  missing={self.missing}"


def _duration(metric: Metric, prediction: PredictionLog, execution: TaskExecution) -> None:
    predicted = prediction.predicted.get("predicted_minutes")
    actual = execution.actual_duration
    if predicted is None or actual is None:
        metric.missing += 1
        return
    metric.values.append(abs(float(predicted) - float(actual)))


def _completion(
    mae: Metric, brier: Metric, prediction: PredictionLog, execution: TaskExecution
) -> None:
    predicted = prediction.predicted.get("probability")
    observed = execution.completion_rate
    if predicted is None or observed is None:
        mae.missing += 1
        brier.missing += 1
        return
    predicted_f, observed_f = float(predicted), float(observed)
    mae.values.append(abs(predicted_f - observed_f))
    brier.values.append((predicted_f - observed_f) ** 2)


def _stress(metric: Metric, prediction: PredictionLog, execution: TaskExecution) -> None:
    predicted = prediction.predicted.get("predicted_stress")
    actual = execution.stress_after
    if predicted is None or actual is None:
        metric.missing += 1
        return
    metric.values.append(abs(float(predicted) - float(actual)))


def _time_slot(metric: Metric, prediction: PredictionLog, execution: TaskExecution) -> None:
    predicted = prediction.predicted.get("slot")
    observed = getattr(execution.time_of_day, "value", execution.time_of_day)
    if not predicted or not observed:
        metric.missing += 1
        return
    metric.values.append(0.0 if str(predicted).lower() == str(observed).lower() else 1.0)


def evaluate(user_id: int | None = None, *, limit: int = 10000) -> list[Metric]:
    """Score every registered prediction that can be joined to an execution."""
    session = SessionLocal()
    try:
        prediction_repo = PredictionLogRepository(session)
        execution_repo = TaskExecutionRepository(session)

        predictions = (
            prediction_repo.list_by_user(user_id, limit=limit)
            if user_id is not None
            else prediction_repo.list_all(limit=limit)
        )

        executions_by_user: dict[int, dict[int, TaskExecution]] = defaultdict(dict)
        metrics: dict[str, Metric] = {
            "duration_mae_minutes": Metric("duration_mae_minutes"),
            "completion_mae": Metric("completion_mae"),
            "completion_brier": Metric("completion_brier"),
            "stress_mae": Metric("stress_mae"),
            "time_slot_error_rate": Metric("time_slot_error_rate"),
        }

        for prediction in predictions:
            if prediction.task_id is None:
                continue
            if prediction.user_id not in executions_by_user:
                executions_by_user[prediction.user_id] = {
                    execution.task_id: execution
                    for execution in execution_repo.list_by_user(prediction.user_id)
                }
            execution = executions_by_user[prediction.user_id].get(prediction.task_id)
            if execution is None:
                continue

            if prediction.prediction_type == "duration":
                _duration(metrics["duration_mae_minutes"], prediction, execution)
            elif prediction.prediction_type == "completion":
                _completion(
                    metrics["completion_mae"],
                    metrics["completion_brier"],
                    prediction,
                    execution,
                )
            elif prediction.prediction_type == "stress":
                _stress(metrics["stress_mae"], prediction, execution)
            elif prediction.prediction_type == "time_slot":
                _time_slot(metrics["time_slot_error_rate"], prediction, execution)

        return list(metrics.values())
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate registered predictions.")
    parser.add_argument("--user-id", type=int, default=None)
    parser.add_argument(
        "--min-samples",
        type=int,
        default=1,
        help="flag metrics whose sample count is below this as provisional",
    )
    args = parser.parse_args()

    settings = get_settings()
    print(f"database: {settings.database_url.split('@')[-1]}")
    print(f"scope   : {'user ' + str(args.user_id) if args.user_id else 'all users'}\n")

    metrics = evaluate(args.user_id)
    for metric in metrics:
        line = metric.render()
        if metric.n and metric.n < args.min_samples:
            line += "   [provisional: small sample]"
        print(line)

    print(
        "\nLower is better (time_slot_error_rate 0 = perfect).\n"
        "Only swap in a trained model once it beats the current `source` on the\n"
        "same rows; the row's model_name/source tells you what produced each value."
    )


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
