"""Level 3 shadow invariant: production output is identical with shadow on/off.

The shadow runner runs *after* the plan is committed and can only append audit
rows. This test persists the same deterministic plan twice - once with Level 3
off, once in shadow mode - and compares every production-visible task field.
"""

from __future__ import annotations

from datetime import date, time

from fastapi.testclient import TestClient

from app.agent.schemas import FinalPlanPayload, GeneratedTaskDraft
from app.agent.state import PlannerRequest
from app.application.services.plan_service import PlanService
from app.application.services.user_model_service import UserModelService
from app.domain.scheduling.schedule_result import CandidateSchedule, ScheduledTask
from app.infrastructure.database import SessionLocal
from app.infrastructure.database.repositories import ShadowPredictionRepository
from app.user_models.runtime import UserModelRuntime


def _state(user_id: int):
    today = date.today()
    draft = GeneratedTaskDraft(
        title="Shadow invariant task",
        estimated_duration=60,
        predicted_duration=60,
        prediction_source="deterministic:workload_estimate",
        order_index=0,
    )
    final = FinalPlanPayload(
        title="Shadow invariant plan",
        start_date=today,
        end_date=today,
        tasks=[draft],
        confidence=0.5,
    )
    schedule = CandidateSchedule(
        start_date=today,
        end_date=today,
        tasks=[
            ScheduledTask(
                task_id=1,
                title=draft.title,
                scheduled_date=today,
                start_time=time(9, 0),
                end_time=time(10, 0),
                duration_minutes=60,
            )
        ],
    )
    request = PlannerRequest(user_id=user_id, start_date=today, end_date=today)
    return {
        "request": request,
        "final_plan": final,
        "candidate_plan": schedule,
        "goal_id_map": {},
        "user_context": None,
    }


def _signature(detail) -> list[tuple]:
    return [
        (
            item.task.title,
            item.task.estimated_duration,
            item.task.predicted_duration,
            item.task.scheduled_date,
            item.task.start_time,
            item.task.end_time,
            item.task.completion_probability,
            item.task.prediction_source,
            item.task.prediction_mode,
            item.task.status,
        )
        for item in detail.tasks
    ]


def test_production_is_identical_with_and_without_shadow(
    client: TestClient, auth_headers: dict
) -> None:
    user_id = client.get("/api/v1/users/me", headers=auth_headers).json()["id"]

    session_off = SessionLocal()
    try:
        service_off = PlanService(
            session_off,
            user_model_service=UserModelService(
                session_off, runtime=UserModelRuntime(requested_mode="off")
            ),
        )
        detail_off = service_off._persist_final_plan(user_id, _state(user_id))
        shadow_off = ShadowPredictionRepository(session_off).list_by_plan(
            detail_off.plan.id or 0
        )
    finally:
        session_off.close()

    session_shadow = SessionLocal()
    try:
        service_shadow = PlanService(
            session_shadow,
            user_model_service=UserModelService(
                session_shadow, runtime=UserModelRuntime(requested_mode="shadow")
            ),
        )
        detail_shadow = service_shadow._persist_final_plan(user_id, _state(user_id))
        shadow_on = ShadowPredictionRepository(session_shadow).list_by_plan(
            detail_shadow.plan.id or 0
        )
    finally:
        session_shadow.close()

    assert _signature(detail_off) == _signature(detail_shadow)
    assert shadow_off == []
    # Shadow ran and recorded an auditable attempt, but the task is untouched.
    assert len(shadow_on) == 1
    assert shadow_on[0].production_decision["predicted_duration"] == 60
    assert shadow_on[0].mode == "shadow"