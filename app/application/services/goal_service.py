"""Goal service - CRUD for the frontend's goal / "待拆解清单" surface.

Goals created here are independent of plan generation: a `draft` goal is simply
a not-yet-decomposed item that the frontend can persist across devices. The
existing planner keeps creating its own goals during preview; this service only
owns the explicit `/goals` CRUD surface.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.domain.models import Goal
from app.infrastructure.database.repositories import GoalRepository, TaskRepository
from app.schemas.goal import GoalCreate, GoalUpdate


class GoalService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._goals = GoalRepository(session)
        self._tasks = TaskRepository(session)

    def list_goals(self, user_id: int, *, status: str | None = None) -> list[Goal]:
        goals = self._goals.list_by_user(user_id)
        if status:
            goals = [
                goal
                for goal in goals
                if getattr(goal.status, "value", goal.status) == status
            ]
        return goals

    def get_goal(self, user_id: int, goal_id: int) -> Goal:
        goal = self._goals.get_by_id(goal_id)
        if goal is None:
            raise NotFoundError("goal not found")
        if goal.user_id != user_id:
            raise PermissionDeniedError("goal belongs to another user")
        return goal

    def create(self, user_id: int, payload: GoalCreate) -> Goal:
        goal = Goal(
            user_id=user_id,
            title=payload.title,
            description=payload.description,
            goal_type=payload.goal_type,
            deadline=payload.deadline,
            priority=payload.priority,
            status=payload.status,
            estimated_minutes=payload.estimated_minutes,
            options={"subject": payload.subject, "task_type": payload.task_type},
        )
        created = self._goals.create(goal)
        self._session.commit()
        return created

    def update(self, user_id: int, goal_id: int, payload: GoalUpdate) -> Goal:
        self.get_goal(user_id, goal_id)  # ownership
        updates: dict[str, object] = {}
        provided = payload.model_dump(exclude_unset=True)

        for field in ("title", "description", "deadline", "estimated_minutes"):
            if field in provided:
                updates[field] = provided[field]
        if "priority" in provided and provided["priority"] is not None:
            updates["priority"] = provided["priority"]
        if "status" in provided and provided["status"] is not None:
            updates["status"] = provided["status"]

        # subject / task_type live inside the free-form `options` JSON blob.
        if "subject" in provided or "task_type" in provided:
            current = self.get_goal(user_id, goal_id)
            options = dict(current.options or {})
            if "subject" in provided:
                options["subject"] = provided["subject"]
            if "task_type" in provided:
                options["task_type"] = provided["task_type"]
            updates["options"] = options

        if updates:
            updated = self._goals.update_fields(goal_id, **updates)
            self._session.commit()
            if updated is not None:
                return updated
        return self.get_goal(user_id, goal_id)

    def delete(self, user_id: int, goal_id: int) -> None:
        self.get_goal(user_id, goal_id)  # ownership
        if self._tasks.list_by_goal(goal_id):
            raise ConflictError(
                "goal is referenced by a plan task; remove or replan that task first"
            )
        self._goals.delete(goal_id)
        self._session.commit()


__all__ = ["GoalService"]
