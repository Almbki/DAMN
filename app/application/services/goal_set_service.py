"""Goal-set service - CRUD, archive/restore and goal attachment.

A goal set groups the goals created by one plan-generation batch. Archiving a
set archives its goals and soft-deletes their unfinished tasks; completed tasks,
executions and plan-version history are always preserved.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.dto.goal_set import (
    GoalAttachResult,
    GoalSetDetail,
    GoalSetImpact,
    GoalSetRestoreResult,
    GoalSetSummary,
)
from app.application.exceptions import (
    DomainValidationError,
    NotFoundError,
    PermissionDeniedError,
)
from app.application.services.goal_service import GoalService
from app.domain.models import GoalSet
from app.domain.models.base import utcnow
from app.domain.models.enums import GoalSetStatus, GoalStatus
from app.infrastructure.database.repositories import (
    GoalRepository,
    GoalSetRepository,
)


class GoalSetService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._goal_sets = GoalSetRepository(session)
        self._goals = GoalRepository(session)
        self._goal_service = GoalService(session)

    # -- reads ------------------------------------------------------------
    def list_goal_sets(
        self, user_id: int, *, include_archived: bool = True
    ) -> list[GoalSetSummary]:
        goals = self._goals.list_by_user(user_id)
        return [
            self._summary(goal_set, goals)
            for goal_set in self._goal_sets.list_by_user(
                user_id, include_archived=include_archived
            )
        ]

    def get_detail(self, user_id: int, goal_set_id: int) -> GoalSetDetail:
        goal_set = self._owned(user_id, goal_set_id)
        goals = self._goals.list_by_goal_set(goal_set_id)
        summary = self._summary(goal_set, goals)
        return GoalSetDetail(**summary.model_dump(), goals=goals)

    # -- writes -----------------------------------------------------------
    def create(
        self, user_id: int, name: str, description: str | None = None
    ) -> GoalSetSummary:
        created = self._goal_sets.create(
            GoalSet(user_id=user_id, name=name, description=description)
        )
        self._session.commit()
        return self._summary(created, [])

    def update(
        self,
        user_id: int,
        goal_set_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> GoalSetSummary:
        self._owned(user_id, goal_set_id)
        fields: dict[str, object] = {}
        if name is not None:
            fields["name"] = name
        if description is not None:
            fields["description"] = description
        if fields:
            self._goal_sets.update_fields(goal_set_id, **fields)
            self._session.commit()
        goal_set = self._owned(user_id, goal_set_id)
        return self._summary(goal_set, self._goals.list_by_goal_set(goal_set_id))

    def archive(self, user_id: int, goal_set_id: int) -> GoalSetImpact:
        goal_set = self._owned(user_id, goal_set_id)
        if goal_set.status == GoalSetStatus.ARCHIVED:
            return GoalSetImpact(goal_set_id=goal_set_id)

        archived_goals = 0
        removed_tasks = 0
        preserved_completed_tasks = 0
        for goal in self._goals.list_by_goal_set(goal_set_id):
            if goal.id is None or goal.status == GoalStatus.ARCHIVED:
                continue
            impact = self._goal_service._archive_locked(
                user_id, goal.id, marker_set_id=goal_set_id
            )
            archived_goals += 1
            removed_tasks += impact["removed_tasks"]
            preserved_completed_tasks += impact["preserved_completed_tasks"]

        self._goal_sets.update_fields(
            goal_set_id,
            status=GoalSetStatus.ARCHIVED,
            archived_at=utcnow(),
        )
        self._session.commit()
        return GoalSetImpact(
            goal_set_id=goal_set_id,
            archived_goals=archived_goals,
            removed_tasks=removed_tasks,
            preserved_completed_tasks=preserved_completed_tasks,
        )

    def restore(self, user_id: int, goal_set_id: int) -> GoalSetRestoreResult:
        goal_set = self._owned(user_id, goal_set_id)
        if goal_set.status != GoalSetStatus.ARCHIVED:
            return GoalSetRestoreResult()

        restored_goals = 0
        restored_tasks = 0
        for goal in self._goals.list_by_goal_set(goal_set_id):
            if goal.id is None:
                continue
            options = dict(goal.options or {})
            if options.get("_archived_by_goal_set_id") != goal_set_id:
                continue
            restored_tasks += self._goal_service._restore_locked(
                user_id, goal.id, clear_marker=True
            )
            restored_goals += 1

        self._goal_sets.update_fields(
            goal_set_id, status=GoalSetStatus.ACTIVE, archived_at=None
        )
        self._session.commit()
        return GoalSetRestoreResult(
            restored_goals=restored_goals, restored_tasks=restored_tasks
        )

    def attach_goals(
        self, user_id: int, goal_set_id: int, goal_ids: list[int]
    ) -> GoalAttachResult:
        goal_set = self._owned(user_id, goal_set_id)
        if goal_set.status == GoalSetStatus.ARCHIVED:
            raise DomainValidationError("cannot attach goals to an archived set")

        attached = 0
        for goal_id in goal_ids:
            goal = self._goals.get_by_id(goal_id)
            if goal is None:
                raise NotFoundError(f"goal {goal_id} not found")
            if goal.user_id != user_id:
                raise PermissionDeniedError(
                    f"goal {goal_id} belongs to another user"
                )
            if goal.goal_set_id == goal_set_id:
                continue  # idempotent: already attached
            self._goals.update_fields(goal_id, goal_set_id=goal_set_id)
            attached += 1
        self._session.commit()
        return GoalAttachResult(attached_goals=attached)

    # -- helpers ----------------------------------------------------------
    def _owned(self, user_id: int, goal_set_id: int) -> GoalSet:
        goal_set = self._goal_sets.get_by_id(goal_set_id)
        if goal_set is None:
            raise NotFoundError("goal set not found")
        if goal_set.user_id != user_id:
            raise PermissionDeniedError("goal set belongs to another user")
        return goal_set

    @staticmethod
    def _summary(goal_set: GoalSet, goals: list) -> GoalSetSummary:
        set_goals = [goal for goal in goals if goal.goal_set_id == goal_set.id]
        return GoalSetSummary(
            id=goal_set.id or 0,
            user_id=goal_set.user_id,
            name=goal_set.name,
            description=goal_set.description,
            status=goal_set.status,
            goal_count=len(set_goals),
            incomplete_goal_count=sum(
                1 for goal in set_goals if goal.status == GoalStatus.ACTIVE
            ),
            archived_at=goal_set.archived_at,
            created_at=goal_set.created_at,
        )


__all__ = ["GoalSetService"]
