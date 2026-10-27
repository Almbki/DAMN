"""Daily execution reconciliation: PENDING_FEEDBACK, OVERDUE and MISSED.

All scenarios use an explicit ``as_of_date`` so they never depend on the wall
clock. Dates are the product's local calendar dates (``APP_TIMEZONE``).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.application.services.execution_reconciliation_service import (
    ExecutionReconciliationService,
)
from app.core.clock import local_date_at, local_today
from app.domain.models.enums import (
    FeedbackObligationStatus,
    PlanStatus,
    TaskKind,
    TaskStatus,
)
from app.infrastructure.database import SessionLocal
from app.infrastructure.database.models import (
    Feedback as FeedbackORM,
)
from app.infrastructure.database.models import (
    Plan as PlanORM,
)
from app.infrastructure.database.models import (
    Task as TaskORM,
)
from app.infrastructure.database.models import (
    TaskExecution as TaskExecutionORM,
)

DAY_1 = date(2026, 10, 26)
DAY_2 = date(2026, 10, 27)
DAY_3 = date(2026, 10, 28)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _seed_plan(user_id: int, *, version: int = 1, status: PlanStatus = PlanStatus.ACTIVE) -> int:
    with SessionLocal() as db:
        plan = PlanORM(
            user_id=user_id,
            version=version,
            status=status,
            title="Reconciliation plan",
            start_date=DAY_1 - timedelta(days=30),
            end_date=DAY_3 + timedelta(days=30),
            confidence=0.5,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan.id


def _seed_task(
    plan_id: int,
    *,
    scheduled_date: date | None,
    status: TaskStatus,
    title: str = "Task",
    occurrence_date: date | None = None,
    series_id: str | None = None,
    task_kind: TaskKind = TaskKind.ONE_OFF,
    estimated_duration: int = 30,
    deleted_at: datetime | None = None,
) -> int:
    with SessionLocal() as db:
        task = TaskORM(
            plan_id=plan_id,
            title=title,
            estimated_duration=estimated_duration,
            scheduled_date=scheduled_date,
            status=status,
            occurrence_date=occurrence_date,
            series_id=series_id,
            task_kind=task_kind,
            order_index=0,
            deleted_at=deleted_at,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task.id


def _seed_execution(
    task_id: int,
    user_id: int,
    *,
    completed: bool = False,
    completion_rate: float = 0.5,
    finished_at: datetime | None = None,
    created_at: datetime | None = None,
) -> None:
    with SessionLocal() as db:
        db.add(
            TaskExecutionORM(
                task_id=task_id,
                user_id=user_id,
                planned_duration=30,
                completion_rate=completion_rate,
                completed=completed,
                finished_at=finished_at or datetime(2026, 10, 26, 10, 0, tzinfo=UTC),
                created_at=created_at or datetime(2026, 10, 26, 10, 0, tzinfo=UTC),
            )
        )
        db.commit()


def _seed_feedback(user_id: int, plan_id: int, day: date = DAY_1) -> None:
    with SessionLocal() as db:
        db.add(
            FeedbackORM(
                user_id=user_id,
                plan_id=plan_id,
                date=day,
                completion_rate=0.5,
                created_at=datetime(2026, 10, 26, 22, 0, tzinfo=UTC),
            )
        )
        db.commit()


def _status(task_id: int) -> TaskStatus:
    with SessionLocal() as db:
        return db.get(TaskORM, task_id).status


def _task(task_id: int) -> TaskORM:
    with SessionLocal() as db:
        return db.get(TaskORM, task_id)


def _reconcile(user_id: int, as_of: date):
    with SessionLocal() as db:
        return ExecutionReconciliationService(db).reconcile_user_execution_state(
            user_id, as_of_date=as_of
        )


def _obligations(user_id: int, as_of: date):
    with SessionLocal() as db:
        return ExecutionReconciliationService(db).list_feedback_obligations(
            user_id, as_of_date=as_of
        )


# ---------------------------------------------------------------------------
# Feedback obligations
# ---------------------------------------------------------------------------
def test_unsubmitted_historical_execution_stays_pending_next_day(registered_user, auth_headers):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=DAY_1, status=TaskStatus.SCHEDULED)
    _seed_execution(task_id, user_id)

    result = _reconcile(user_id, DAY_2)

    assert DAY_1 in result.pending_feedback_dates
    obligations = _obligations(user_id, DAY_2)
    assert [(item.execution_date, item.status, item.is_retrospective) for item in obligations] == [
        (DAY_1, FeedbackObligationStatus.PENDING, True)
    ]
    assert obligations[0].plan_id == plan_id


def test_submitted_feedback_is_not_pending_again(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=DAY_1, status=TaskStatus.SCHEDULED)
    _seed_execution(task_id, user_id)
    _seed_feedback(user_id, plan_id, DAY_1)

    assert _reconcile(user_id, DAY_2).pending_feedback_dates == ()
    assert _obligations(user_id, DAY_2) == []


def test_no_execution_or_task_behaviour_creates_no_feedback_debt(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    _seed_task(plan_id, scheduled_date=DAY_1, status=TaskStatus.SCHEDULED)

    # The task is overdue, but the user never produced any execution behaviour.
    result = _reconcile(user_id, DAY_2)

    assert result.pending_feedback_dates == ()
    assert _obligations(user_id, DAY_2) == []


def test_reconciliation_is_idempotent(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    normal_id = _seed_task(plan_id, scheduled_date=DAY_1, status=TaskStatus.SCHEDULED)
    recurring_id = _seed_task(
        plan_id,
        scheduled_date=DAY_1,
        status=TaskStatus.SCHEDULED,
        occurrence_date=DAY_1,
        series_id="series-a",
        task_kind=TaskKind.ROUTINE,
    )

    first = _reconcile(user_id, DAY_2)
    second = _reconcile(user_id, DAY_2)

    assert set(first.overdue_task_ids) == {normal_id}
    assert set(first.missed_task_ids) == {recurring_id}
    assert second.overdue_task_ids == ()
    assert second.missed_task_ids == ()
    assert _status(normal_id) == TaskStatus.OVERDUE
    assert _status(recurring_id) == TaskStatus.MISSED
    # No duplicate lifecycle rows are possible: status is the only write.
    with SessionLocal() as db:
        assert db.query(TaskORM).filter(TaskORM.plan_id == plan_id).count() == 2


def test_feedback_obligations_are_scoped_to_the_authenticated_user(
    client, registered_user, auth_headers
):
    owner_id = registered_user["user"]["id"]
    plan_id = _seed_plan(owner_id)
    task_id = _seed_task(plan_id, scheduled_date=DAY_1, status=TaskStatus.SCHEDULED)
    _seed_execution(task_id, owner_id)

    other = client.post(
        "/api/v1/auth/register",
        json={
            "email": "other-reconcile@example.com",
            "password": "password123",
            "display_name": "Other",
        },
    )
    assert other.status_code == 201, other.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "other-reconcile@example.com", "password": "password123"},
    )
    assert login.status_code == 200, login.text
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get("/api/v1/feedback/obligations", headers=other_headers)
    assert response.status_code == 200, response.text
    assert response.json() == []

    own = client.get("/api/v1/feedback/obligations", headers=auth_headers)
    assert own.status_code == 200, own.text
    assert [item["execution_date"] for item in own.json()] == [DAY_1.isoformat()]


# ---------------------------------------------------------------------------
# Normal tasks: OVERDUE
# ---------------------------------------------------------------------------
def test_past_unfinished_normal_task_becomes_overdue_without_moving(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=DAY_1, status=TaskStatus.SCHEDULED)

    result = _reconcile(user_id, DAY_2)

    assert result.overdue_task_ids == (task_id,)
    task = _task(task_id)
    assert task.status == TaskStatus.OVERDUE
    assert task.scheduled_date == DAY_1


def test_completed_task_stays_completed(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=DAY_1, status=TaskStatus.COMPLETED)

    result = _reconcile(user_id, DAY_2)

    assert result.overdue_task_ids == ()
    assert result.missed_task_ids == ()
    assert _status(task_id) == TaskStatus.COMPLETED


def test_skipped_task_is_a_terminal_state(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=DAY_1, status=TaskStatus.SKIPPED)

    _reconcile(user_id, DAY_2)

    assert _status(task_id) == TaskStatus.SKIPPED


def test_future_task_is_untouched(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=DAY_3, status=TaskStatus.SCHEDULED)

    result = _reconcile(user_id, DAY_2)

    assert result.overdue_task_ids == ()
    assert _status(task_id) == TaskStatus.SCHEDULED


def test_superseded_plan_and_deleted_task_are_not_reactivated(registered_user):
    user_id = registered_user["user"]["id"]
    old_plan_id = _seed_plan(user_id, version=1, status=PlanStatus.SUPERSEDED)
    superseded_task = _seed_task(old_plan_id, scheduled_date=DAY_1, status=TaskStatus.SCHEDULED)
    active_plan_id = _seed_plan(user_id, version=2, status=PlanStatus.ACTIVE)
    deleted_task = _seed_task(
        active_plan_id,
        scheduled_date=DAY_1,
        status=TaskStatus.SCHEDULED,
        deleted_at=datetime(2026, 10, 26, 9, 0, tzinfo=UTC),
    )

    result = _reconcile(user_id, DAY_2)

    assert result.overdue_task_ids == ()
    assert result.missed_task_ids == ()
    assert _status(superseded_task) == TaskStatus.SCHEDULED
    assert _status(deleted_task) == TaskStatus.SCHEDULED


# ---------------------------------------------------------------------------
# Recurring occurrences: MISSED
# ---------------------------------------------------------------------------
def test_long_term_kind_alone_is_not_recurring(registered_user):
    """A legacy/project row can be LONG_TERM without a recurrence occurrence."""
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(
        plan_id,
        scheduled_date=DAY_1,
        status=TaskStatus.SCHEDULED,
        title="Project unit",
        task_kind=TaskKind.LONG_TERM,
    )

    _reconcile(user_id, DAY_2)

    assert _status(task_id) == TaskStatus.OVERDUE


def test_project_series_id_alone_is_not_recurring(registered_user):
    """Plain project units carry series_id but must become OVERDUE, not MISSED."""
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(
        plan_id,
        scheduled_date=DAY_1,
        status=TaskStatus.SCHEDULED,
        title="Project unit",
        series_id="goal-1-project",
        task_kind=TaskKind.ONE_OFF,
    )

    _reconcile(user_id, DAY_2)

    assert _status(task_id) == TaskStatus.OVERDUE


def test_routine_kind_alone_is_not_recurring(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(
        plan_id,
        scheduled_date=DAY_1,
        status=TaskStatus.SCHEDULED,
        task_kind=TaskKind.ROUTINE,
    )

    _reconcile(user_id, DAY_2)

    assert _status(task_id) == TaskStatus.OVERDUE


def test_occurrence_date_alone_is_the_missed_marker(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(
        plan_id,
        scheduled_date=DAY_1,
        status=TaskStatus.SCHEDULED,
        occurrence_date=DAY_1,
        task_kind=TaskKind.ONE_OFF,
    )

    _reconcile(user_id, DAY_2)

    assert _status(task_id) == TaskStatus.MISSED


def test_past_recurring_occurrence_becomes_missed_without_merging_into_today(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    missed_id = _seed_task(
        plan_id,
        scheduled_date=DAY_1,
        status=TaskStatus.SCHEDULED,
        title="背单词",
        occurrence_date=DAY_1,
        series_id="vocab",
        task_kind=TaskKind.ROUTINE,
        estimated_duration=30,
    )
    today_id = _seed_task(
        plan_id,
        scheduled_date=DAY_2,
        status=TaskStatus.SCHEDULED,
        title="背单词",
        occurrence_date=DAY_2,
        series_id="vocab",
        task_kind=TaskKind.ROUTINE,
        estimated_duration=30,
    )

    result = _reconcile(user_id, DAY_2)

    assert result.missed_task_ids == (missed_id,)
    assert result.overdue_task_ids == ()
    assert _status(missed_id) == TaskStatus.MISSED
    assert _status(today_id) == TaskStatus.SCHEDULED
    # No duration inflation / no make-up occurrence.
    assert _task(missed_id).estimated_duration == 30
    assert _task(today_id).estimated_duration == 30
    assert _task(missed_id).scheduled_date == DAY_1
    assert _task(today_id).scheduled_date == DAY_2


def test_unplaced_past_recurring_occurrence_uses_its_occurrence_date(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(
        plan_id,
        scheduled_date=None,
        status=TaskStatus.PENDING,
        occurrence_date=DAY_1,
        series_id="unplaced",
        task_kind=TaskKind.LONG_TERM,
    )

    _reconcile(user_id, DAY_2)

    assert _status(task_id) == TaskStatus.MISSED


# ---------------------------------------------------------------------------
# Hooks and timezone
# ---------------------------------------------------------------------------
def test_login_reconciles_without_opening_a_screen(client, registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(
        plan_id,
        scheduled_date=local_today() - timedelta(days=2),
        status=TaskStatus.SCHEDULED,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert response.status_code == 200, response.text

    assert _status(task_id) == TaskStatus.OVERDUE


def test_retrospective_submission_resolves_debt_without_replanning(
    client, registered_user, auth_headers
):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    task_id = _seed_task(plan_id, scheduled_date=DAY_1, status=TaskStatus.COMPLETED)
    _seed_execution(task_id, user_id, completed=True, completion_rate=1.0)

    response = client.post(
        f"/api/v1/plans/{plan_id}/feedback",
        headers=auth_headers,
        json={"date": DAY_1.isoformat(), "completion_rate": 1.0},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["replan_decision"] == "none"
    assert body["replan_triggered"] is False

    obligations = client.get("/api/v1/feedback/obligations", headers=auth_headers)
    assert obligations.status_code == 200, obligations.text
    assert obligations.json() == []


def test_utc_instant_maps_to_product_local_date():
    # 16:30 UTC is already the next calendar day in Asia/Shanghai.
    instant = datetime(2026, 10, 26, 16, 30, tzinfo=UTC)
    assert local_date_at(instant, "UTC") == DAY_1
    assert local_date_at(instant, "Asia/Shanghai") == DAY_2


def test_execution_day_uses_local_date_not_utc_date(registered_user):
    user_id = registered_user["user"]["id"]
    plan_id = _seed_plan(user_id)
    # No scheduled/occurrence date: the execution timestamp is the only day.
    task_id = _seed_task(plan_id, scheduled_date=None, status=TaskStatus.SCHEDULED)
    _seed_execution(
        task_id,
        user_id,
        created_at=datetime(2026, 10, 26, 16, 30, tzinfo=UTC),
    )

    obligations = _obligations(user_id, DAY_2)

    assert [item.execution_date for item in obligations] == [DAY_2]
    assert obligations[0].is_retrospective is False
