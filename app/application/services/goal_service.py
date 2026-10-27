"""Goal service - CRUD for the frontend's goal / "待拆解清单" surface.

Goals created here are independent of plan generation: a `draft` goal is simply
a not-yet-decomposed item that the frontend can persist across devices. The
existing planner keeps creating its own goals during preview; this service only
owns the explicit `/goals` CRUD surface.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.application.dto.goal import GoalCreateData
from app.application.exceptions import (
    ConflictError,
    DomainValidationError,
    NotFoundError,
    PermissionDeniedError,
)
from app.domain.date_constraints import DateConstraintError, resolve_earliest_start
from app.domain.models import Goal
from app.domain.models.enums import GoalSetStatus, GoalStatus, PlanStatus, TaskStatus
from app.infrastructure.database.repositories import (
    GoalRepository,
    GoalSetRepository,
    PlanRepository,
    TaskRepository,
)


def _resolved_start_date(
    *,
    title: str | None,
    description: str | None,
    deadline,
    explicit: date | None,
    source: str | None = None,
) -> date | None:
    """Fold an explicit text date into the persisted inclusive lower bound."""
    try:
        return resolve_earliest_start(
            explicit,
            text="\n".join(part for part in (title, description) if part),
            deadline=deadline.date() if deadline is not None else None,
            reference=date.today(),
            source=source,
        )
    except DateConstraintError as exc:
        raise DomainValidationError(str(exc)) from exc


class GoalService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._goals = GoalRepository(session)
        self._goal_sets = GoalSetRepository(session)
        self._plans = PlanRepository(session)
        self._tasks = TaskRepository(session)

    def list_goals(
        self,
        user_id: int,
        *,
        status: str | None = None,
        include_archived: bool = True,
    ) -> list[Goal]:
        goals = self._goals.list_by_user(user_id)
        if status:
            goals = [
                goal
                for goal in goals
                if getattr(goal.status, "value", goal.status) == status
            ]
        elif not include_archived:
            goals = [
                goal
                for goal in goals
                if getattr(goal.status, "value", goal.status)
                != GoalStatus.ARCHIVED.value
            ]
        return goals

    def get_goal(self, user_id: int, goal_id: int) -> Goal:
        goal = self._goals.get_by_id(goal_id)
        if goal is None:
            raise NotFoundError("goal not found")
        if goal.user_id != user_id:
            raise PermissionDeniedError("goal belongs to another user")
        return goal

    def create(self, user_id: int, payload: GoalCreateData) -> Goal:
        if payload.goal_set_id is not None:
            goal_set = self._goal_sets.get_by_id(payload.goal_set_id)
            if goal_set is None:
                raise NotFoundError("goal set not found")
            if goal_set.user_id != user_id:
                raise PermissionDeniedError("goal set belongs to another user")
            if goal_set.status != GoalSetStatus.ACTIVE:
                raise DomainValidationError("goal set is archived")
        goal = Goal(
            user_id=user_id,
            goal_set_id=payload.goal_set_id,
            title=payload.title,
            description=payload.description,
            goal_type=payload.goal_type,
            deadline=payload.deadline,
            priority=payload.priority,
            status=payload.status,
            estimated_minutes=payload.estimated_minutes,
            start_date=_resolved_start_date(
                title=payload.title,
                description=payload.description,
                deadline=payload.deadline,
                explicit=payload.start_date,
                source=f"goal title={payload.title!r}",
            ),
            task_kind=payload.task_kind,
            planning_mode=payload.planning_mode,
            recurrence_frequency=payload.recurrence_frequency,
            recurrence_interval=payload.recurrence_interval,
            daily_target_minutes=payload.daily_target_minutes,
            recurrence_weekdays=payload.recurrence_weekdays,
            target_amount=payload.target_amount,
            target_unit=payload.target_unit,
            options={"subject": payload.subject, "task_type": payload.task_type},
        )
        created = self._goals.create(goal)
        self._session.commit()
        return created

    def update(self, user_id: int, goal_id: int, updates: dict[str, object]) -> Goal:
        current = self.get_goal(user_id, goal_id)  # ownership + current state
        provided = dict(updates)
        requested_status = provided.pop("status", None) if "status" in provided else None
        field_updates: dict[str, object] = {}

        for field in (
            "title",
            "description",
            "deadline",
            "estimated_minutes",
            "start_date",
            "task_kind",
            "planning_mode",
            "recurrence_frequency",
            "recurrence_interval",
            "daily_target_minutes",
            "recurrence_weekdays",
            "target_amount",
            "target_unit",
        ):
            if field in provided:
                field_updates[field] = provided[field]
        if "priority" in provided and provided["priority"] is not None:
            field_updates["priority"] = provided["priority"]

        # Moving a goal between sets is also exposed through PATCH; ``None``
        # detaches it. The explicit attachments endpoint remains the batch path.
        if "goal_set_id" in provided:
            new_set_id = provided["goal_set_id"]
            if new_set_id is not None:
                goal_set = self._goal_sets.get_by_id(new_set_id)
                if goal_set is None:
                    raise NotFoundError("goal set not found")
                if goal_set.user_id != user_id:
                    raise PermissionDeniedError("goal set belongs to another user")
                if goal_set.status != GoalSetStatus.ACTIVE:
                    raise DomainValidationError("goal set is archived")
            field_updates["goal_set_id"] = new_set_id

        # subject / task_type live inside the free-form `options` JSON blob.
        if "subject" in provided or "task_type" in provided:
            options = dict(current.options or {})
            if "subject" in provided:
                options["subject"] = provided["subject"]
            if "task_type" in provided:
                options["task_type"] = provided["task_type"]
            field_updates["options"] = options

        # Re-derive the structured lower bound when the user edits the start
        # date, or fill it from text when no lower bound exists yet. An
        # existing non-null start_date is never silently cleared.
        affects_dates = {"title", "description", "deadline"} & provided.keys()
        if "start_date" in provided or affects_dates:
            if "start_date" in provided or current.start_date is None:
                field_updates["start_date"] = _resolved_start_date(
                    title=field_updates.get("title", current.title),
                    description=field_updates.get("description", current.description),
                    deadline=field_updates.get("deadline", current.deadline),
                    explicit=(
                        field_updates["start_date"]
                        if "start_date" in field_updates
                        else current.start_date
                    ),
                    source=(
                        f"goal id={goal_id} "
                        f"title={field_updates.get('title', current.title)!r}"
                    ),
                )

        if field_updates:
            self._goals.update_fields(goal_id, **field_updates)

        # Status transitions share the archive/restore task semantics. Only one
        # commit happens, no matter which fields changed.
        if requested_status is not None:
            status = (
                GoalStatus(requested_status)
                if isinstance(requested_status, str)
                else requested_status
            )
            if status == GoalStatus.ARCHIVED and current.status != GoalStatus.ARCHIVED:
                self._archive_locked(user_id, goal_id)
            elif status == GoalStatus.ACTIVE and current.status == GoalStatus.ARCHIVED:
                self._restore_locked(user_id, goal_id)
            elif status != current.status:
                self._goals.update_fields(goal_id, status=status)

        self._session.commit()
        return self.get_goal(user_id, goal_id)

    def archive(self, user_id: int, goal_id: int) -> dict[str, int]:
        """Archive one goal and remove its unfinished tasks from the active plan."""
        self.get_goal(user_id, goal_id)  # ownership + 404
        impact = self._archive_locked(user_id, goal_id)
        self._session.commit()
        return impact

    def restore(self, user_id: int, goal_id: int) -> int:
        """Restore one goal and undelete the tasks archived with it."""
        self.get_goal(user_id, goal_id)  # ownership + 404
        restored = self._restore_locked(user_id, goal_id)
        self._session.commit()
        return restored

    def _latest_active_plan_id(self, user_id: int) -> int | None:
        plan = self._plans.get_latest_by_user(user_id)
        if plan is None or plan.id is None or plan.status != PlanStatus.ACTIVE:
            return None
        return plan.id

    def _archive_locked(
        self,
        user_id: int,
        goal_id: int,
        *,
        marker_set_id: int | None = None,
    ) -> dict[str, int]:
        """Archive a goal without committing (callers own the transaction).

        ``marker_set_id`` records that the goal was archived *via a set*, so a
        later set restore can restore exactly those goals and not goals the user
        archived individually.
        """
        goal = self.get_goal(user_id, goal_id)
        options = dict(goal.options or {})
        if marker_set_id is not None:
            options["_archived_by_goal_set_id"] = marker_set_id

        if goal.status != GoalStatus.ARCHIVED:
            fields: dict[str, object] = {"status": GoalStatus.ARCHIVED}
            if options != (goal.options or {}):
                fields["options"] = options
            self._goals.update_fields(goal_id, **fields)

        plan_id = self._latest_active_plan_id(user_id)
        preserved = 0
        removed = 0
        if plan_id is not None:
            preserved = sum(
                1
                for task in self._tasks.list_by_goal(goal_id)
                if task.plan_id == plan_id and task.status == TaskStatus.COMPLETED
            )
            removed = self._tasks.soft_delete_incomplete_for_goal(
                plan_id, goal_id, f"goal_archived:{goal_id}"
            )
        return {
            "goal_id": goal_id,
            "removed_tasks": removed,
            "preserved_completed_tasks": preserved,
        }

    def _restore_locked(
        self,
        user_id: int,
        goal_id: int,
        *,
        clear_marker: bool = False,
    ) -> int:
        """Restore a goal without committing (callers own the transaction)."""
        goal = self.get_goal(user_id, goal_id)
        fields: dict[str, object] = {}
        if goal.status != GoalStatus.ACTIVE:
            fields["status"] = GoalStatus.ACTIVE
        if clear_marker:
            options = dict(goal.options or {})
            if "_archived_by_goal_set_id" in options:
                options.pop("_archived_by_goal_set_id", None)
                fields["options"] = options
        if fields:
            self._goals.update_fields(goal_id, **fields)

        plan_id = self._latest_active_plan_id(user_id)
        if plan_id is None:
            return 0
        return self._tasks.restore_for_goal(
            plan_id, goal_id, f"goal_archived:{goal_id}"
        )

    def delete(self, user_id: int, goal_id: int) -> None:
        self.get_goal(user_id, goal_id)  # ownership
        if self._tasks.list_by_goal(goal_id):
            raise ConflictError(
                "goal is referenced by a plan task; remove or replan that task first"
            )
        # Soft-deleted tasks still reference the goal row; detach them (their
        # rows/executions stay intact) so the FK does not block the deletion.
        self._tasks.detach_deleted_from_goal(goal_id)
        self._goals.delete(goal_id)
        self._session.commit()


__all__ = ["GoalService"]
