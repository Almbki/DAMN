"""Backlog / MOVE / LOCAL_RESCHEDULE deterministic command tests."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pytest

from app.application.exceptions import (
    ConflictError,
    DomainValidationError,
    NotFoundError,
    PermissionDeniedError,
)
from app.application.services.task_scheduling_service import TaskSchedulingService
from app.core.clock import local_today
from app.domain.models.enums import (
    CognitiveLoad,
    GoalStatus,
    PlanStatus,
    TaskKind,
    TaskStatus,
)
from app.infrastructure.database import SessionLocal
from app.infrastructure.database.models import (
    Goal as GoalORM,
)
from app.infrastructure.database.models import (
    Plan as PlanORM,
)
from app.infrastructure.database.models import (
    ScheduleEvent as ScheduleEventORM,
)
from app.infrastructure.database.models import (
    Task as TaskORM,
)

TODAY = local_today()
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
DAY_AFTER = TODAY + timedelta(days=2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _seed_plan(
    user_id: int,
    *,
    version: int = 1,
    status: PlanStatus = PlanStatus.ACTIVE,
) -> int:
    with SessionLocal() as db:
        plan = PlanORM(
            user_id=user_id,
            version=version,
            status=status,
            title="Scheduling plan",
            start_date=TODAY - timedelta(days=30),
            end_date=TODAY + timedelta(days=60),
            confidence=0.5,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan.id


def _seed_goal(
    user_id: int,
    *,
    title: str = "Math",
    start_date: date | None = None,
    deadline: date | None = None,
) -> int:
    with SessionLocal() as db:
        goal = GoalORM(
            user_id=user_id,
            title=title,
            goal_type="project",
            status=GoalStatus.ACTIVE,
            start_date=start_date,
            deadline=(
                datetime.combine(deadline, time(23, 59)) if deadline is not None else None
            ),
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        return goal.id


def _seed_task(
    plan_id: int,
    *,
    title: str = "Task",
    goal_id: int | None = None,
    status: TaskStatus = TaskStatus.SCHEDULED,
    scheduled_date: date | None = None,
    start: time | None = time(9, 0),
    end: time | None = time(10, 0),
    duration: int = 60,
    series_id: str | None = None,
    order_index: int = 0,
    occurrence_date: date | None = None,
    work_unit_key: str | None = None,
    chunk_index: int | None = None,
    cognitive_load: CognitiveLoad = CognitiveLoad.MEDIUM,
    task_kind: TaskKind = TaskKind.ONE_OFF,
    deleted_at: datetime | None = None,
) -> int:
    if scheduled_date is None:
        start = None
        end = None
    with SessionLocal() as db:
        task = TaskORM(
            plan_id=plan_id,
            goal_id=goal_id,
            title=title,
            estimated_duration=duration,
            scheduled_date=scheduled_date,
            start_time=start,
            end_time=end,
            status=status,
            cognitive_load=cognitive_load,
            task_kind=task_kind,
            series_id=series_id,
            order_index=order_index,
            occurrence_date=occurrence_date,
            work_unit_key=work_unit_key,
            chunk_index=chunk_index,
            deleted_at=deleted_at,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task.id


def _seed_event(user_id: int, day: date, start: time, end: time, title: str = "Course") -> None:
    with SessionLocal() as db:
        db.add(
            ScheduleEventORM(
                user_id=user_id,
                title=title,
                start_date=day,
                end_date=day,
                start_time=start,
                end_time=end,
            )
        )
        db.commit()


def _task(task_id: int) -> TaskORM:
    with SessionLocal() as db:
        return db.get(TaskORM, task_id)


def _backlog(task_id: int, user_id: int, plan_id: int) -> TaskORM:
    with SessionLocal() as db:
        return TaskSchedulingService(db).move_task_to_backlog(user_id, plan_id, task_id)


def _move(task_id: int, user_id: int, plan_id: int, day: date, start: time) -> TaskORM:
    with SessionLocal() as db:
        return TaskSchedulingService(db).move_task(
            user_id,
            plan_id,
            task_id,
            target_date=day,
            target_start=start,
        )


def _reschedule(task_id: int, user_id: int, plan_id: int):
    with SessionLocal() as db:
        return TaskSchedulingService(db).local_reschedule(user_id, plan_id, task_id)


# ---------------------------------------------------------------------------
# Backlog
# ---------------------------------------------------------------------------
def test_overdue_task_enters_backlog_and_keeps_identity(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    goal_id = _seed_goal(user_id)
    task_id = _seed_task(
        plan_id,
        goal_id=goal_id,
        status=TaskStatus.OVERDUE,
        scheduled_date=YESTERDAY,
        series_id="math-project",
        order_index=3,
        work_unit_key="wg-1-project-3",
        chunk_index=1,
        duration=90,
    )

    result = _backlog(task_id, user_id, plan_id)

    assert result.status == TaskStatus.BACKLOG
    assert result.scheduled_date is None
    assert result.start_time is None
    assert result.end_time is None
    assert result.goal_id == goal_id
    assert result.work_unit_key == "wg-1-project-3"
    assert result.chunk_index == 1
    assert result.estimated_duration == 90
    assert result.series_id == "math-project"


def test_backlog_is_idempotent(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=TODAY, status=TaskStatus.SCHEDULED)

    first = _backlog(task_id, user_id, plan_id)
    second = _backlog(task_id, user_id, plan_id)

    assert first.status == second.status == TaskStatus.BACKLOG
    assert second.scheduled_date is None


def test_completed_task_cannot_enter_backlog(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=TODAY, status=TaskStatus.COMPLETED)

    with pytest.raises(ConflictError):
        _backlog(task_id, user_id, plan_id)
    assert _task(task_id).status == TaskStatus.COMPLETED


def test_missed_recurring_cannot_enter_backlog(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(
        plan_id,
        scheduled_date=YESTERDAY,
        status=TaskStatus.MISSED,
        occurrence_date=YESTERDAY,
        series_id="vocab",
        task_kind=TaskKind.ROUTINE,
    )

    with pytest.raises((ConflictError, DomainValidationError)):
        _backlog(task_id, user_id, plan_id)
    assert _task(task_id).status == TaskStatus.MISSED


def test_future_recurring_occurrence_cannot_enter_backlog(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(
        plan_id,
        scheduled_date=TOMORROW,
        status=TaskStatus.SCHEDULED,
        occurrence_date=TOMORROW,
        series_id="vocab",
        task_kind=TaskKind.ROUTINE,
    )

    with pytest.raises(DomainValidationError):
        _backlog(task_id, user_id, plan_id)
    assert _task(task_id).status == TaskStatus.SCHEDULED


def test_superseded_plan_and_deleted_task_are_not_backloggable(registered_user):
    user_id = registered_user["user"]["id"]
    old_plan = _seed_plan(user_id, version=1, status=PlanStatus.SUPERSEDED)
    old_task = _seed_task(old_plan, scheduled_date=YESTERDAY, status=TaskStatus.OVERDUE)
    with pytest.raises(ConflictError):
        _backlog(old_task, user_id, old_plan)

    plan_id = _seed_plan(user_id, version=2)
    deleted = _seed_task(
        plan_id,
        scheduled_date=YESTERDAY,
        status=TaskStatus.OVERDUE,
        deleted_at=datetime.now(),
    )
    with pytest.raises(NotFoundError):
        _backlog(deleted, user_id, plan_id)


def test_backlog_is_user_scoped(registered_user, client):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=TODAY, status=TaskStatus.SCHEDULED)

    other = client.post(
        "/api/v1/auth/register",
        json={
            "email": "scheduling-other@example.com",
            "password": "password123",
            "display_name": "Other",
        },
    )
    assert other.status_code == 201, other.text
    other_id = other.json()["id"]

    with pytest.raises(PermissionDeniedError):
        _backlog(task_id, other_id, plan_id)
    assert _task(task_id).status == TaskStatus.SCHEDULED


# ---------------------------------------------------------------------------
# MOVE
# ---------------------------------------------------------------------------
def test_move_scheduled_task_to_legal_slot(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    goal_id = _seed_goal(user_id)
    task_id = _seed_task(
        plan_id,
        goal_id=goal_id,
        scheduled_date=TODAY,
        series_id="math-project",
        order_index=1,
        work_unit_key="wg-1-project-1",
        chunk_index=0,
    )

    result = _move(task_id, user_id, plan_id, TOMORROW, time(14, 0))

    assert result.status == TaskStatus.SCHEDULED
    assert result.scheduled_date == TOMORROW
    assert result.start_time == time(14, 0)
    assert result.end_time == time(15, 0)
    assert result.work_unit_key == "wg-1-project-1"
    assert result.chunk_index == 0


def test_move_snaps_to_thirty_minute_grid(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=TODAY, duration=60)

    result = _move(task_id, user_id, plan_id, TOMORROW, time(14, 17))

    assert result.start_time == time(14, 30)
    assert result.end_time == time(15, 30)


def test_overdue_and_backlog_tasks_return_to_active_on_move(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    overdue = _seed_task(plan_id, scheduled_date=YESTERDAY, status=TaskStatus.OVERDUE)
    backlog = _seed_task(plan_id, scheduled_date=None, status=TaskStatus.BACKLOG)

    moved_overdue = _move(overdue, user_id, plan_id, TOMORROW, time(9, 0))
    moved_backlog = _move(backlog, user_id, plan_id, TOMORROW, time(11, 0))

    assert moved_overdue.status == TaskStatus.SCHEDULED
    assert moved_backlog.status == TaskStatus.SCHEDULED
    assert moved_backlog.scheduled_date == TOMORROW


def test_move_rejects_fixed_event_collision(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=TODAY)
    _seed_event(user_id, TOMORROW, time(9, 0), time(10, 0), "Calculus lecture")

    with pytest.raises(DomainValidationError) as caught:
        _move(task_id, user_id, plan_id, TOMORROW, time(9, 0))

    assert caught.value.detail["reason_code"] == "fixed_event_overlap"
    assert _task(task_id).scheduled_date == TODAY


def test_move_rejects_before_earliest_start(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    goal_id = _seed_goal(user_id, start_date=DAY_AFTER)
    task_id = _seed_task(plan_id, goal_id=goal_id, scheduled_date=TOMORROW)

    with pytest.raises(DomainValidationError) as caught:
        _move(task_id, user_id, plan_id, TOMORROW, time(9, 0))

    assert caught.value.detail["reason_code"] in {"earliest_start", "PAST_DATE"}


def test_move_rejects_after_deadline(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    goal_id = _seed_goal(user_id, deadline=TODAY)
    task_id = _seed_task(plan_id, goal_id=goal_id, scheduled_date=TODAY)

    with pytest.raises(DomainValidationError) as caught:
        _move(task_id, user_id, plan_id, TOMORROW, time(9, 0))

    assert caught.value.detail["reason_code"] == "deadline_exceeded"


def test_move_rejects_daily_capacity(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=TODAY)
    _seed_task(plan_id, scheduled_date=TOMORROW, duration=300, start=time(8, 0), end=time(13, 0))

    with pytest.raises(DomainValidationError) as caught:
        _move(task_id, user_id, plan_id, TOMORROW, time(14, 0))

    assert caught.value.detail["reason_code"] == "daily_limit"


def test_move_rejects_per_goal_daily_cap(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    goal_id = _seed_goal(user_id)
    _seed_task(
        plan_id,
        goal_id=goal_id,
        scheduled_date=TOMORROW,
        start=time(8, 0),
        end=time(9, 0),
    )
    _seed_task(
        plan_id,
        goal_id=goal_id,
        scheduled_date=TOMORROW,
        start=time(9, 15),
        end=time(10, 15),
    )
    task_id = _seed_task(plan_id, goal_id=goal_id, scheduled_date=TODAY)

    with pytest.raises(DomainValidationError) as caught:
        _move(task_id, user_id, plan_id, TOMORROW, time(11, 0))

    assert caught.value.detail["reason_code"] == "GOAL_DAILY_CAPACITY_EXCEEDED"


def test_move_rejects_high_cognitive_daily_limit(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    goal_a = _seed_goal(user_id, title="A")
    goal_b = _seed_goal(user_id, title="B")
    goal_c = _seed_goal(user_id, title="C")
    _seed_task(
        plan_id,
        goal_id=goal_a,
        scheduled_date=TOMORROW,
        start=time(8, 0),
        end=time(9, 0),
        cognitive_load=CognitiveLoad.HIGH,
    )
    _seed_task(
        plan_id,
        goal_id=goal_b,
        scheduled_date=TOMORROW,
        start=time(9, 15),
        end=time(10, 15),
        cognitive_load=CognitiveLoad.HIGH,
    )
    task_id = _seed_task(
        plan_id,
        goal_id=goal_c,
        scheduled_date=TODAY,
        cognitive_load=CognitiveLoad.HIGH,
    )

    with pytest.raises(DomainValidationError) as caught:
        _move(task_id, user_id, plan_id, TOMORROW, time(11, 0))

    assert caught.value.detail["reason_code"] == "high_cognitive_daily_max"


def test_completed_and_missed_tasks_cannot_move(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    completed = _seed_task(plan_id, scheduled_date=TODAY, status=TaskStatus.COMPLETED)
    missed = _seed_task(
        plan_id,
        scheduled_date=YESTERDAY,
        status=TaskStatus.MISSED,
        occurrence_date=YESTERDAY,
        series_id="vocab",
    )

    with pytest.raises(ConflictError):
        _move(completed, user_id, plan_id, TOMORROW, time(9, 0))
    with pytest.raises(ConflictError):
        _move(missed, user_id, plan_id, TOMORROW, time(9, 0))


def test_api_completing_backlog_task_removes_it_from_the_pool(
    client, registered_user, auth_headers
):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(
        plan_id,
        scheduled_date=None,
        status=TaskStatus.BACKLOG,
    )

    response = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}",
        headers=auth_headers,
        json={"completed": True},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"

    backlog = client.get(f"/api/v1/plans/{plan_id}/backlog", headers=auth_headers)
    assert backlog.status_code == 200, backlog.text
    assert backlog.json() == []


def test_api_completing_overdue_task_clears_overdue_lifecycle(
    client, registered_user, auth_headers
):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(
        plan_id,
        scheduled_date=YESTERDAY,
        status=TaskStatus.OVERDUE,
    )

    response = client.patch(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}",
        headers=auth_headers,
        json={"completed": True, "finished_at": datetime.now().isoformat()},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"

    detail = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers)
    assert detail.status_code == 200, detail.text
    task = next(item for item in detail.json()["tasks"] if item["id"] == task_id)
    assert task["status"] == "completed"


def test_move_does_not_create_a_replan(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=TODAY)

    with SessionLocal() as db:
        plans_before = db.query(PlanORM).filter(PlanORM.user_id == user_id).count()
    _move(task_id, user_id, plan_id, TOMORROW, time(9, 0))
    with SessionLocal() as db:
        plans_after = db.query(PlanORM).filter(PlanORM.user_id == user_id).count()
    assert plans_after == plans_before


def test_api_move_backlog_and_read_backlog(client, registered_user, auth_headers):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=TODAY)

    moved = client.post(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}/move",
        headers=auth_headers,
        json={"target_date": TOMORROW.isoformat(), "target_start": "14:17"},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["status"] == "scheduled"
    assert moved.json()["start_time"].startswith("14:30")

    back = client.post(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}/backlog",
        headers=auth_headers,
    )
    assert back.status_code == 200, back.text
    assert back.json()["status"] == "backlog"
    assert back.json()["scheduled_date"] is None

    listed = client.get(
        f"/api/v1/plans/{plan_id}/backlog", headers=auth_headers
    )
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()] == [task_id]


def test_api_move_rejection_exposes_reason_code(client, registered_user, auth_headers):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=TODAY)
    _seed_event(user_id, TOMORROW, time(9, 0), time(10, 0), "Lecture")

    response = client.post(
        f"/api/v1/plans/{plan_id}/tasks/{task_id}/move",
        headers=auth_headers,
        json={"target_date": TOMORROW.isoformat(), "target_start": "09:00"},
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"]["reason_code"] == "fixed_event_overlap"


def test_api_local_reschedule_returns_the_moved_sequence(
    client, registered_user, auth_headers
):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    goal_id = _seed_goal(user_id)
    a, b, c = _seed_sequence(plan_id, goal_id, start_status=TaskStatus.OVERDUE)

    response = client.post(
        f"/api/v1/plans/{plan_id}/tasks/{a}/local-reschedule",
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert {item["id"] for item in payload} == {a, b, c}
    assert all(item["status"] == "scheduled" for item in payload)


# ---------------------------------------------------------------------------
# LOCAL_RESCHEDULE
# ---------------------------------------------------------------------------
def _seed_sequence(
    plan_id: int,
    goal_id: int,
    *,
    start_status: TaskStatus,
    series_id: str = "math-project",
    count: int = 3,
    duration: int = 60,
    start_order: int = 0,
) -> list[int]:
    statuses = [start_status] + [TaskStatus.SCHEDULED] * (count - 1)
    dates = [TODAY - timedelta(days=count - 1 - index) for index in range(count)]
    end_minutes = 9 * 60 + duration
    end = time(end_minutes // 60, end_minutes % 60)
    return [
        _seed_task(
            plan_id,
            goal_id=goal_id,
            title=f"Unit {start_order + index}",
            status=statuses[index],
            scheduled_date=dates[index],
            start=time(9, 0),
            end=end,
            duration=duration,
            series_id=series_id,
            order_index=start_order + index,
            work_unit_key=f"wg-1-project-{start_order + index}",
            chunk_index=0,
        )
        for index in range(count)
    ]


def test_local_reschedule_preserves_sequence_order_and_identity(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    goal_id = _seed_goal(user_id)
    a, b, c = _seed_sequence(plan_id, goal_id, start_status=TaskStatus.OVERDUE)

    updated = _reschedule(a, user_id, plan_id)

    assert {item.id for item in updated} == {a, b, c}
    tasks = [_task(item) for item in (a, b, c)]
    assert all(item.status == TaskStatus.SCHEDULED for item in tasks)
    assert all(item.scheduled_date is not None and item.scheduled_date >= TODAY for item in tasks)
    assert tasks[0].scheduled_date <= tasks[1].scheduled_date <= tasks[2].scheduled_date
    assert [item.estimated_duration for item in tasks] == [60, 60, 60]
    assert [item.work_unit_key for item in tasks] == [
        "wg-1-project-0",
        "wg-1-project-1",
        "wg-1-project-2",
    ]
    assert [item.chunk_index for item in tasks] == [0, 0, 0]


def test_local_reschedule_freezes_completed_predecessor(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    goal_id = _seed_goal(user_id)
    x = _seed_task(
        plan_id,
        goal_id=goal_id,
        title="Unit X",
        status=TaskStatus.COMPLETED,
        scheduled_date=TODAY - timedelta(days=5),
        start=time(8, 0),
        end=time(9, 0),
        series_id="math-project",
        order_index=0,
        work_unit_key="wg-1-project-0",
    )
    a, b = _seed_sequence(
        plan_id, goal_id, start_status=TaskStatus.OVERDUE, count=2, start_order=1
    )
    before = _task(x)

    _reschedule(a, user_id, plan_id)

    after = _task(x)
    assert after.status == TaskStatus.COMPLETED
    assert after.scheduled_date == before.scheduled_date
    assert after.start_time == before.start_time
    assert after.end_time == before.end_time
    assert _task(b).scheduled_date >= TODAY


def test_local_reschedule_does_not_touch_another_goal(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    math_goal = _seed_goal(user_id, title="Math")
    english_goal = _seed_goal(user_id, title="English")
    a, b, c = _seed_sequence(plan_id, math_goal, start_status=TaskStatus.OVERDUE)
    unrelated = _seed_task(
        plan_id,
        goal_id=english_goal,
        title="English essay",
        scheduled_date=TOMORROW,
        start=time(9, 0),
        end=time(10, 0),
        series_id="english-project",
        order_index=10,
    )
    before = _task(unrelated)

    _reschedule(a, user_id, plan_id)

    after = _task(unrelated)
    assert after.scheduled_date == before.scheduled_date
    assert after.start_time == before.start_time
    assert after.end_time == before.end_time
    for item in (a, b, c):
        assert _task(item).scheduled_date >= TODAY


def test_local_reschedule_skips_fixed_event_days(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    goal_id = _seed_goal(user_id)
    _seed_event(user_id, TOMORROW, time(8, 0), time(22, 0), "All-day course")
    a, b, c = _seed_sequence(plan_id, goal_id, start_status=TaskStatus.OVERDUE)

    _reschedule(a, user_id, plan_id)

    for item in (a, b, c):
        task = _task(item)
        assert task.scheduled_date != TOMORROW


def test_local_reschedule_rolls_back_when_deadline_infeasible(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    goal_id = _seed_goal(user_id, deadline=TODAY)
    a, b, c = _seed_sequence(plan_id, goal_id, start_status=TaskStatus.OVERDUE)
    before = {item: _task(item) for item in (a, b, c)}

    with pytest.raises(DomainValidationError) as caught:
        _reschedule(a, user_id, plan_id)

    assert caught.value.detail["reason_code"] == "LOCAL_RESCHEDULE_INFEASIBLE"
    for item in (a, b, c):
        after = _task(item)
        assert after.status == before[item].status
        assert after.scheduled_date == before[item].scheduled_date
        assert after.start_time == before[item].start_time
        assert after.end_time == before[item].end_time


def test_local_reschedule_rejects_recurring_occurrence(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(
        plan_id,
        scheduled_date=YESTERDAY,
        status=TaskStatus.MISSED,
        occurrence_date=YESTERDAY,
        series_id="vocab",
        task_kind=TaskKind.ROUTINE,
    )

    with pytest.raises(DomainValidationError) as caught:
        _reschedule(task_id, user_id, plan_id)

    assert caught.value.detail["reason_code"] == "RECURRING_NOT_RESCHEDULABLE"


def test_local_reschedule_only_moves_unfinished_chunks(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    goal_id = _seed_goal(user_id)
    done_chunk = _seed_task(
        plan_id,
        goal_id=goal_id,
        title="Chapter A chunk 0",
        status=TaskStatus.COMPLETED,
        scheduled_date=TODAY - timedelta(days=3),
        series_id="book-project",
        order_index=0,
        work_unit_key="wg-1-project-0",
        chunk_index=0,
    )
    a = _seed_task(
        plan_id,
        goal_id=goal_id,
        title="Chapter A chunk 1",
        status=TaskStatus.OVERDUE,
        scheduled_date=TODAY - timedelta(days=2),
        series_id="book-project",
        order_index=1,
        work_unit_key="wg-1-project-0",
        chunk_index=1,
    )
    b = _seed_task(
        plan_id,
        goal_id=goal_id,
        title="Chapter A chunk 2",
        status=TaskStatus.SCHEDULED,
        scheduled_date=YESTERDAY,
        series_id="book-project",
        order_index=2,
        work_unit_key="wg-1-project-0",
        chunk_index=2,
    )
    before_done = _task(done_chunk)

    _reschedule(a, user_id, plan_id)

    after_done = _task(done_chunk)
    assert after_done.status == TaskStatus.COMPLETED
    assert after_done.scheduled_date == before_done.scheduled_date
    assert _task(a).status == TaskStatus.SCHEDULED
    assert _task(b).status == TaskStatus.SCHEDULED
    assert _task(a).chunk_index == 1
    assert _task(b).chunk_index == 2
    assert _task(a).work_unit_key == "wg-1-project-0"


def test_local_reschedule_can_start_from_backlog(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    goal_id = _seed_goal(user_id)
    a = _seed_task(
        plan_id,
        goal_id=goal_id,
        title="Unit 0",
        status=TaskStatus.BACKLOG,
        scheduled_date=None,
        series_id="math-project",
        order_index=0,
        work_unit_key="wg-1-project-0",
    )
    b = _seed_task(
        plan_id,
        goal_id=goal_id,
        title="Unit 1",
        status=TaskStatus.SCHEDULED,
        scheduled_date=TOMORROW,
        series_id="math-project",
        order_index=1,
        work_unit_key="wg-1-project-1",
    )
    c = _seed_task(
        plan_id,
        goal_id=goal_id,
        title="Unit 2",
        status=TaskStatus.SCHEDULED,
        scheduled_date=DAY_AFTER,
        series_id="math-project",
        order_index=2,
        work_unit_key="wg-1-project-2",
    )

    updated = _reschedule(a, user_id, plan_id)

    assert {item.id for item in updated} == {a, b, c}
    assert all(_task(item).status == TaskStatus.SCHEDULED for item in (a, b, c))
    assert _task(a).scheduled_date is not None


def test_local_reschedule_does_not_create_plan_or_agent_run(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    goal_id = _seed_goal(user_id)
    a, b, c = _seed_sequence(plan_id, goal_id, start_status=TaskStatus.OVERDUE)

    with SessionLocal() as db:
        plans_before = db.query(PlanORM).filter(PlanORM.user_id == user_id).count()
    _reschedule(a, user_id, plan_id)
    with SessionLocal() as db:
        plans_after = db.query(PlanORM).filter(PlanORM.user_id == user_id).count()
    assert plans_after == plans_before
