"""Deterministic daily execution reconciliation.

This service is the single owner of the *execution lifecycle* status written by
time passing:

* a past, unfinished, non-recurring task      -> ``OVERDUE``
* a past, unfinished recurring occurrence     -> ``MISSED``
* a past day with observed execution but no
  check-in                                    -> ``PENDING_FEEDBACK``

It is deterministic and idempotent: repeated calls with the same ``as_of_date``
produce no new rows and no further status changes. It never reschedules, never
moves a task to today, never touches the backlog and never calls an LLM.

Terminal states are preserved: ``COMPLETED`` / ``SKIPPED`` / ``FAILED`` tasks,
soft-deleted rows, and tasks of superseded plan versions are never reactivated.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.application.dto.reconciliation import (
    FeedbackObligation,
    ReconciliationResult,
)
from app.application.preferences import effective_scheduling_preferences
from app.core.clock import local_date_at, local_today
from app.domain.execution import is_observed_execution
from app.domain.models import Plan, Task
from app.domain.models.enums import (
    FeedbackObligationStatus,
    PlanStatus,
    TaskStatus,
)
from app.infrastructure.database.repositories import (
    FeedbackRepository,
    PlanRepository,
    TaskExecutionRepository,
    TaskRepository,
    UserRepository,
)

#: Only unfinished, non-terminal states may roll into OVERDUE / MISSED.
_RECONCILABLE_STATUSES = frozenset(
    {TaskStatus.PENDING, TaskStatus.SCHEDULED, TaskStatus.IN_PROGRESS}
)
_TERMINAL_STATUSES = frozenset({TaskStatus.COMPLETED, TaskStatus.SKIPPED})


def _is_recurring_occurrence(task: Task) -> bool:
    """Only recurrence-materialized day cells carry ``occurrence_date``.

    ``task_kind`` is a legacy label (project rows can be ``long_term``) and
    ``series_id`` is also set on plain project units, so neither is evidence of
    a recurring occurrence. ``occurrence_date`` is the only reliable marker.
    """
    return task.occurrence_date is not None


class ExecutionReconciliationService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._tasks = TaskRepository(session)
        self._plans = PlanRepository(session)
        self._executions = TaskExecutionRepository(session)
        self._feedbacks = FeedbackRepository(session)
        self._users = UserRepository(session)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def reconcile_user_execution_state(
        self, user_id: int, *, as_of_date: date | None = None
    ) -> ReconciliationResult:
        """Settle past task/occurrence states and report unresolved feedback."""
        as_of = as_of_date or local_today()
        tasks = self._tasks.list_by_user(user_id)
        plans = self._plan_map(user_id)
        auto_backlog = self._auto_backlog_enabled(user_id)

        overdue: list[int] = []
        backlogged: list[int] = []
        missed: list[int] = []
        for task in tasks:
            if task.id is None:
                continue
            # Already-OVERDUE rows are only revisited when the user has opted
            # into automatic backlog. Recurring rows are never converted.
            revisiting_overdue = (
                auto_backlog and task.status == TaskStatus.OVERDUE
            )
            if task.status not in _RECONCILABLE_STATUSES and not revisiting_overdue:
                continue
            plan = plans.get(task.plan_id)
            # A superseded/archived plan version is already a terminal outcome
            # for its unfinished rows; the carried work lives in the new version.
            if plan is None or plan.status != PlanStatus.ACTIVE:
                continue

            if _is_recurring_occurrence(task):
                if task.status not in _RECONCILABLE_STATUSES:
                    continue
                day = task.occurrence_date or task.scheduled_date
                if day is None or day >= as_of:
                    continue
                self._tasks.update_fields(task.id, status=TaskStatus.MISSED)
                missed.append(task.id)
            else:
                day = task.scheduled_date
                if day is None or day >= as_of:
                    continue
                if auto_backlog:
                    # BACKLOG means "still to do, no placement". Clearing the
                    # date is the existing backlog mutation semantics.
                    self._tasks.update_fields(
                        task.id,
                        status=TaskStatus.BACKLOG,
                        scheduled_date=None,
                        start_time=None,
                        end_time=None,
                        scheduling_reason=None,
                        scheduling_detail=None,
                    )
                    backlogged.append(task.id)
                else:
                    # OVERDUE is a lifecycle fact only: the date is left untouched.
                    self._tasks.update_fields(task.id, status=TaskStatus.OVERDUE)
                    overdue.append(task.id)

        if overdue or backlogged or missed:
            self._session.commit()

        pending_dates = tuple(
            obligation.execution_date
            for obligation in self.list_feedback_obligations(
                user_id, as_of_date=as_of
            )
        )
        return ReconciliationResult(
            as_of_date=as_of,
            overdue_task_ids=tuple(overdue),
            backlogged_task_ids=tuple(backlogged),
            missed_task_ids=tuple(missed),
            pending_feedback_dates=pending_dates,
        )

    def list_feedback_obligations(
        self, user_id: int, *, as_of_date: date | None = None
    ) -> list[FeedbackObligation]:
        """Unresolved ``user + execution_date`` feedback debts, oldest first.

        Eligibility is derived from persisted behaviour, never from the mere
        existence of a calendar date:

        * at least one *observed* execution on the day, or
        * at least one task on the day whose status is COMPLETED / SKIPPED.

        A day already covered by a ``feedbacks`` row (any plan version) is
        resolved. No obligation row is created, so repeated reconciliation cannot
        duplicate debt; the persisted source of truth stays ``tasks`` +
        ``task_executions`` + ``feedbacks``.
        """
        as_of = as_of_date or local_today()
        tasks = self._tasks.list_by_user(user_id)
        plans = self._plan_map(user_id)
        task_by_id = {task.id: task for task in tasks if task.id is not None}
        submitted_days = {
            feedback.date
            for feedback in self._feedbacks.list_by_user(user_id, limit=5000)
            if feedback.user_id == user_id
        }

        #: day -> candidate plan ids (deterministic plan choice at the end).
        eligible: dict[date, set[int]] = {}

        def mark(day: date, plan_id: int) -> None:
            if day <= as_of:
                eligible.setdefault(day, set()).add(plan_id)

        # Task-level behaviour without an execution row (e.g. PATCH status).
        for task in tasks:
            if task.status not in _TERMINAL_STATUSES:
                continue
            day = task.scheduled_date or task.occurrence_date
            if day is not None:
                mark(day, task.plan_id)

        # Observed execution behaviour (completion / partial / actual duration).
        for execution in self._executions.list_by_user(user_id, limit=5000):
            if execution.user_id != user_id or not is_observed_execution(execution):
                continue
            task = task_by_id.get(execution.task_id)
            # A soft-deleted task no longer represents user-visible behaviour.
            if task is None:
                continue
            day = task.scheduled_date or task.occurrence_date
            if day is None and execution.created_at is not None:
                day = local_date_at(execution.created_at)
            if day is not None:
                mark(day, task.plan_id)

        return [
            FeedbackObligation(
                execution_date=day,
                status=FeedbackObligationStatus.PENDING,
                is_retrospective=day < as_of,
                plan_id=self._choose_plan(eligible[day], plans),
            )
            for day in sorted(eligible)
            if day not in submitted_days
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _plan_map(self, user_id: int) -> dict[int, Plan]:
        return {
            plan.id: plan
            for plan in self._plans.list_by_user(user_id)
            if plan.id is not None
        }

    def _auto_backlog_enabled(self, user_id: int) -> bool:
        user = self._users.get_by_id(user_id)
        preferences = effective_scheduling_preferences(
            user.profile if user is not None else None,
            user.scheduling_preferences if user is not None else None,
        )
        return bool(preferences.get("auto_backlog_overdue"))

    @staticmethod
    def _choose_plan(candidates: set[int], plans: dict[int, Plan]) -> int | None:
        """Prefer the active version; otherwise the newest known version."""
        known = [plan_id for plan_id in candidates if plan_id in plans]
        if not known:
            return max(candidates) if candidates else None
        active = [
            plan_id for plan_id in known if plans[plan_id].status == PlanStatus.ACTIVE
        ]
        pool = active or known
        return max(pool, key=lambda plan_id: (plans[plan_id].version, plan_id))


__all__ = ["ExecutionReconciliationService"]
