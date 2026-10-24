"""Unit tests for the real three-layer user model runtime and Level 3 shadow."""

from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path

import pytest

from app.user_models.contracts import HistoryBundle, Level3Mode, TaskPredictionContext
from app.user_models.errors import ModelInputError, ModelUnavailableError
from app.user_models.level1.runtime import Level1Runtime
from app.user_models.level2.ddsr.schemas import (
    DayInput,
    ReflectionInput,
    TaskExecution,
    TaskPlan,
)
from app.user_models.runtime import UserModelRuntime
from app.user_models.shadow import Level3ShadowRunner


def _trait_profile(theta: float = 0.2) -> dict:
    return {
        "schema_version": "1.0",
        "model": "trait_v1",
        "instrument": "IPIP-NEO-120",
        "method": "bayesian_cat",
        "calibration": {"model": "samejima_grm", "version": "grm_v1"},
        "domains": {
            domain: {
                "theta": theta,
                "se": 0.3,
                "ci95": [theta - 0.5, theta + 0.5],
                "items_answered": 8,
            }
            for domain in ("N", "E", "O", "A", "C")
        },
        "assessment": {"total_items_answered": 40, "completed": True},
    }


def _day(day: date, completed: bool = True, actual: int = 70) -> DayInput:
    return DayInput(
        date=day,
        task_plans=[
            TaskPlan(
                task_id="1",
                title="task",
                planned_start=datetime.combine(day, time(8, 0)),
                estimated_duration_minutes=60,
            )
        ],
        task_executions=[
            TaskExecution(
                task_id="1",
                completed=completed,
                actual_duration_minutes=actual,
                completion_ratio=1.0 if completed else 0.0,
            )
        ],
        reflection=ReflectionInput(day_review="今天很累，压力有点大"),
    )


def test_level1_loads_artifacts_and_exposes_versioned_metadata() -> None:
    runtime = Level1Runtime()
    assert runtime.available is True
    meta = runtime.metadata
    assert meta.model_version == "trait_v1"
    assert meta.artifact_version == "grm_v1"
    assert len(meta.artifact_hash) == 64

    snapshot = runtime.snapshot(_trait_profile(0.4))
    assert set(snapshot.domains) == {"N", "E", "O", "A", "C"}
    assert snapshot.domains["C"].theta == pytest.approx(0.4)
    assert snapshot.metadata.artifact_hash == meta.artifact_hash


def test_level1_rejects_malformed_profile() -> None:
    runtime = Level1Runtime()
    broken = _trait_profile()
    del broken["domains"]["C"]
    with pytest.raises(ModelInputError):
        runtime.snapshot(broken)


def test_missing_artifacts_degrade_to_unavailable(tmp_path: Path) -> None:
    runtime = Level1Runtime(root=tmp_path)
    assert runtime.available is False
    assert runtime.metadata.status.value == "unavailable"
    with pytest.raises(ModelUnavailableError):
        runtime.snapshot(_trait_profile())


def test_level2_replays_real_history_and_returns_a_typed_snapshot() -> None:
    runtime = UserModelRuntime(requested_mode="shadow")
    profile = runtime.level2.replay(
        [_day(date(2026, 9, 20)), _day(date(2026, 9, 21), actual=120)],
        _trait_profile(),
    )
    snapshot = runtime.level2.snapshot(profile)
    assert snapshot.model_version == "ddsr_v1"
    assert 0.0 <= snapshot.fatigue.value <= 1.0
    assert snapshot.fatigue.uncertainty > 0
    assert snapshot.date == date(2026, 9, 21)
    assert snapshot.metadata.artifact_hash


def test_level2_rejects_an_invalid_trait_context() -> None:
    runtime = UserModelRuntime(requested_mode="shadow")
    with pytest.raises(ModelInputError):
        runtime.level2.replay([_day(date(2026, 9, 20))], {"domains": {"N": {}}})


def _level3_inputs(runtime: UserModelRuntime):
    trait = runtime.level1.snapshot(_trait_profile())
    state = runtime.level2.snapshot(
        runtime.level2.replay([_day(date(2026, 9, 20))], _trait_profile())
    )
    task = TaskPredictionContext(
        task_id="1",
        title="task",
        estimated_duration_minutes=60,
        time_of_day=10,
    )
    return trait, state, task


def test_level3_cold_start_does_not_fabricate_completion_probability() -> None:
    runtime = UserModelRuntime(requested_mode="shadow")
    trait, state, task = _level3_inputs(runtime)
    history = HistoryBundle()
    prediction = runtime.predict_level3(
        runtime.build_level3_input(trait=trait, state=state, task=task, history=history)
    )
    assert prediction.prediction_mode == "cold_start"
    assert prediction.completion_probability is None
    assert prediction.predicted_duration_minutes == pytest.approx(60)
    assert prediction.degraded is True


def test_level3_history_baseline_uses_real_duration_ratios() -> None:
    runtime = UserModelRuntime(requested_mode="shadow")
    trait, state, task = _level3_inputs(runtime)
    history = HistoryBundle(
        completion_history=[True, True, False, True],
        duration_ratio_history=[1.5, 1.5, 1.4, 1.6],
        total_historical_tasks=4,
        completed_task_count=3,
        failed_task_count=1,
        usable_duration_samples=4,
    )
    prediction = runtime.predict_level3(
        runtime.build_level3_input(trait=trait, state=state, task=task, history=history)
    )
    assert prediction.prediction_mode == "history_baseline"
    assert prediction.completion_probability is not None
    assert prediction.predicted_duration_minutes > 60


def test_level3_mode_off_never_runs_and_active_is_downgraded(monkeypatch) -> None:
    off = UserModelRuntime(requested_mode="off")
    assert off.mode is Level3Mode.OFF
    assert off.describe()["effective_mode"] == "off"

    active = UserModelRuntime(requested_mode="active")
    assert active.requested_mode is Level3Mode.ACTIVE
    assert active.mode is Level3Mode.SHADOW
    assert active.mode_reason == "active_not_open"


def test_shadow_runner_contains_model_failures(monkeypatch) -> None:
    runtime = UserModelRuntime(requested_mode="shadow")
    trait, state, task = _level3_inputs(runtime)

    def boom(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("model exploded")

    monkeypatch.setattr(runtime, "predict_level3", boom)
    record = Level3ShadowRunner(runtime).run(
        user_id=1,
        plan_id=2,
        task_id=3,
        trait=trait,
        state=state,
        history=HistoryBundle(),
        task=task,
        production_decision={"predicted_duration": 60, "completion_probability": None},
    )
    assert record is not None
    assert record.success is False
    assert "model exploded" in (record.failure_reason or "")
    assert record.mode == "shadow"


def test_shadow_runner_never_mutates_production_inputs() -> None:
    runtime = UserModelRuntime(requested_mode="shadow")
    trait, state, task = _level3_inputs(runtime)
    production = {
        "predicted_duration": 60,
        "completion_probability": None,
        "scheduled_date": "2026-09-20",
    }
    snapshot_before = dict(production)
    record = Level3ShadowRunner(runtime).run(
        user_id=1,
        plan_id=2,
        task_id=3,
        trait=trait,
        state=state,
        history=HistoryBundle(),
        task=task,
        production_decision=production,
    )
    assert record is not None
    assert production == snapshot_before
    assert record.production_decision == snapshot_before


def test_artifact_integrity_check_is_clean() -> None:
    runtime = UserModelRuntime(requested_mode="shadow")
    assert runtime.ensure_artifact_integrity() == []