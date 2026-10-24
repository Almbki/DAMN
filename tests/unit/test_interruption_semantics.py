"""Level 2 adapter semantics: missing interruption is not zero."""

from __future__ import annotations

from datetime import date, datetime, time

from app.application.services.user_model_service import UserModelService
from app.domain.models import TaskExecution as DomainExecution
from app.user_models.level2.ddsr.config import DDSRConfig
from app.user_models.level2.ddsr.schemas import (
    DayInput,
    TaskPlan,
)
from app.user_models.level2.ddsr.schemas import (
    TaskExecution as Level2Execution,
)
from app.user_models.level2.ddsr.task_metrics import derive_task_metrics


def _domain(value: int | None) -> DomainExecution:
    return DomainExecution(
        task_id=1,
        user_id=1,
        planned_duration=60,
        actual_duration=30,
        completion_rate=0.5,
        completed=False,
        interruption_count=value,
    )


def test_application_adapter_preserves_null() -> None:
    assert UserModelService._level2_execution(_domain(None)).interruption_count is None
    assert UserModelService._level2_execution(_domain(0)).interruption_count == 0
    assert UserModelService._level2_execution(_domain(3)).interruption_count == 3


def test_ddsr_metrics_preserve_null_vs_zero() -> None:
    plan = TaskPlan(
        task_id="1",
        title="task",
        planned_start=datetime.combine(date(2026, 9, 1), time(9, 0)),
        estimated_duration_minutes=60,
    )
    base = {
        "task_id": "1",
        "actual_start": datetime.combine(date(2026, 9, 1), time(9, 0)),
        "actual_duration_minutes": 30,
        "completion_ratio": 0.5,
        "completed": False,
    }

    def metric(value: int | None):
        day = DayInput(
            date=date(2026, 9, 1),
            task_plans=[plan],
            task_executions=[Level2Execution(**base, interruption_count=value)],
        )
        return derive_task_metrics(day, DDSRConfig())[0]

    assert metric(None).interruption_count is None
    assert metric(0).interruption_count == 0
    assert metric(3).interruption_count == 3