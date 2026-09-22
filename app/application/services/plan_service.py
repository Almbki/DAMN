"""Plan service: orchestrates plan generation, retrieval and task updates.

Responsibilities (per the architecture rules): permission checks, transaction
boundaries, repository calls, and coordinating the Agent graph, Scheduler,
Rule Engine and ML predictors. The graph itself never touches the database.
"""

from __future__ import annotations

from statistics import mean

from sqlalchemy.orm import Session

from app.agent.graph import GenerationEvent, PlannerGraph
from app.agent.schemas import GeneratedTaskDraft
from app.agent.state import GenerationRequest, PlannerState
from app.application.dto.plan import PlanDetail, TaskWithStandards
from app.application.exceptions import NotFoundError, PermissionDeniedError
from app.application.services.profile_service import ProfileService
from app.domain.models import Goal, Plan, Task, TaskExecution, TaskStandard
from app.domain.models.enums import PlanStatus, TaskStatus
from app.domain.rules.base import RuleEngine
from app.domain.scheduling.scheduler import Scheduler
from app.infrastructure.database.repositories import (
    GoalRepository,
    PlanRepository,
    TaskExecutionRepository,
    TaskRepository,
    TaskStandardRepository,
    UserRepository,
)
from app.ml.predictors import PredictorSet


class PlanService:
    def __init__(
        self,
        session: Session,
        *,
        predictors: PredictorSet | None = None,
        scheduler: Scheduler | None = None,
        rule_engine: RuleEngine | None = None,
        llm: object | None = None,
    ) -> None:
        self._session = session
        self._plans = PlanRepository(session)
        self._tasks = TaskRepository(session)
        self._standards = TaskStandardRepository(session)
        self._goals = GoalRepository(session)
        self._executions = TaskExecutionRepository(session)
        self._users = UserRepository(session)
        self.predictors = predictors or PredictorSet.default()
        self.scheduler = scheduler or Scheduler()
        self.rule_engine = rule_engine or RuleEngine()
        self.llm = llm

    # -- generation --------------------------------------------------------
    def _build_graph(self) -> PlannerGraph:
        return PlannerGraph(
            llm=self.llm,
            predictors=self.predictors,
            scheduler=self.scheduler,
            rule_engine=self.rule_engine,
        )

    def generate_plan(
        self, user_id: int, request: GenerationRequest, user_features=None
    ) -> PlanDetail:
        plan, _events = self._generate(
            user_id, request, user_features=user_features, collect_events=False
        )
        return plan

    def generate_plan_with_events(
        self, user_id: int, request: GenerationRequest, user_features=None
    ) -> tuple[PlanDetail, list[GenerationEvent]]:
        plan, events = self._generate(
            user_id, request, user_features=user_features, collect_events=True
        )
        return plan, events

    def _generate(
        self,
        user_id: int,
        request: GenerationRequest,
        *,
        user_features,
        collect_events: bool,
    ) -> tuple[PlanDetail, list[GenerationEvent]]:
        if self._users.get_by_id(user_id) is None:
            raise NotFoundError("user not found")

        # 1. Persist the goals so drafts can reference real goal ids.
        goal_id_map = self._persist_goals(user_id, request)

        # 2. Build user features (history => ML predictors) and the 画像 prompt.
        profile_service = ProfileService(self._session)
        if user_features is None:
            user_features = profile_service.build_user_features(user_id)
        profile_prompt = profile_service.build_profile_prompt(user_id)

        # 3. Run the agent graph (no DB access inside).
        graph = self._build_graph()
        if collect_events:
            state, events = graph.run_with_events(
                request,
                user_features=user_features,
                goal_id_map=goal_id_map,
                profile_prompt=profile_prompt,
            )
        else:
            state = graph.invoke(
                request,
                user_features=user_features,
                goal_id_map=goal_id_map,
                profile_prompt=profile_prompt,
            )
            events = []

        # 4. Persist the plan version + tasks + standards.
        detail = self._persist_plan(user_id, request, state)
        return detail, events

    def _persist_goals(self, user_id: int, request: GenerationRequest) -> dict[int, int]:
        goals: list[Goal] = []
        for goal_input in request.goals:
            goals.append(
                Goal(
                    user_id=user_id,
                    title=goal_input.title,
                    description=goal_input.description,
                    goal_type=goal_input.goal_type,
                    deadline=goal_input.deadline,
                    priority=goal_input.priority,
                    estimated_minutes=goal_input.estimated_minutes,
                    options={"subject": goal_input.subject, "task_type": goal_input.task_type},
                )
            )
        created = self._goals.create_many(goals)
        return {index + 1: goal.id for index, goal in enumerate(created) if goal.id is not None}

    def _persist_plan(
        self, user_id: int, request: GenerationRequest, state: PlannerState
    ) -> PlanDetail:
        drafts = self._final_drafts(state)
        schedule = state.get("final_plan") or state.get("candidate_plan")
        schedule_map = {item.task_id: item for item in (schedule.tasks if schedule else [])}

        previous = self._plans.get_latest_by_user(user_id)
        if previous is not None and previous.id is not None:
            self._plans.update_status(previous.id, PlanStatus.SUPERSEDED)

        plan = Plan(
            user_id=user_id,
            version=self._plans.next_version(user_id),
            status=PlanStatus.ACTIVE,
            title=request.plan_title
            or (state.get("plan_draft").title if state.get("plan_draft") else None),
            start_date=request.start_date,
            end_date=request.end_date,
            parent_plan_id=previous.id if previous else None,
            confidence=self._confidence(state),
        )
        plan = self._plans.create(plan)

        tasks: list[Task] = []
        standards: list[TaskStandard] = []
        for order, draft in enumerate(drafts):
            placed = schedule_map.get(order + 1)
            tasks.append(
                Task(
                    plan_id=plan.id,
                    goal_id=draft.goal_id,
                    title=draft.title,
                    description=draft.description,
                    estimated_duration=max(draft.estimated_duration, 1),
                    predicted_duration=draft.predicted_duration,
                    cognitive_load=draft.cognitive_load,
                    priority=draft.priority,
                    scheduled_date=placed.scheduled_date if placed else None,
                    start_time=placed.start_time if placed else None,
                    end_time=placed.end_time if placed else None,
                    status=TaskStatus.SCHEDULED,
                    completion_probability=placed.completion_probability if placed else None,
                    order_index=order,
                )
            )
        created_tasks = self._tasks.create_many(tasks)

        for task, draft in zip(created_tasks, drafts, strict=False):
            for std_order, description in enumerate(draft.standards):
                standards.append(
                    TaskStandard(
                        task_id=task.id,
                        description=description,
                        estimated_duration=max(
                            task.estimated_duration // max(len(draft.standards), 1), 5
                        ),
                        order_index=std_order,
                    )
                )
        if standards:
            self._standards.create_many(standards)

        self._session.commit()
        return self.get_plan(user_id, plan.id)

    @staticmethod
    def _final_drafts(state: PlannerState) -> list[GeneratedTaskDraft]:
        drafts = state.get("final_tasks")
        if drafts:
            return list(drafts)
        plan_draft = state.get("plan_draft")
        return list(plan_draft.tasks) if plan_draft else []

    @staticmethod
    def _confidence(state: PlannerState) -> float:
        values: list[float] = []
        for key in ("goal_analysis", "theoretical_workload", "user_situation", "plan_draft"):
            value = state.get(key)
            confidence = getattr(value, "confidence", None)
            if confidence is not None:
                values.append(float(confidence))
        return round(mean(values), 3) if values else 0.5

    # -- reads -------------------------------------------------------------
    def list_plans(self, user_id: int) -> list[Plan]:
        return self._plans.list_by_user(user_id)

    def get_plan(self, user_id: int, plan_id: int) -> PlanDetail:
        plan = self._plans.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError("plan not found")
        if plan.user_id != user_id:
            raise PermissionDeniedError("plan belongs to another user")
        tasks = self._tasks.list_by_plan(plan_id)
        standards = self._standards.list_by_plan(plan_id)
        standards_by_task: dict[int, list[TaskStandard]] = {}
        for standard in standards:
            standards_by_task.setdefault(standard.task_id, []).append(standard)
        goal_ids = [t.goal_id for t in tasks if t.goal_id is not None]
        goals = self._goals.list_by_ids(list(set(goal_ids))) if goal_ids else []
        return PlanDetail(
            plan=plan,
            tasks=[
                TaskWithStandards(task=task, standards=standards_by_task.get(task.id, []))
                for task in tasks
            ],
            goals=goals,
        )

    def update_task(
        self,
        user_id: int,
        plan_id: int,
        task_id: int,
        *,
        changes: dict,
        standard_updates: list[dict] | None = None,
    ) -> Task:
        self.get_plan(user_id, plan_id)  # permission check
        task = self._tasks.get_by_id(task_id)
        if task is None or task.plan_id != plan_id:
            raise NotFoundError("task not found in plan")

        completed = changes.pop("completed", None)
        if completed is True:
            changes.setdefault("status", TaskStatus.COMPLETED)
        if "status" in changes and isinstance(changes["status"], str):
            changes["status"] = TaskStatus(changes["status"])
        if changes:
            updated = self._tasks.update_fields(task_id, **changes)
            task = updated or task

        for update in standard_updates or []:
            standard_id = update.get("id")
            if standard_id is None:
                continue
            self._standards.update_fields(standard_id, completed=bool(update.get("completed")))

        if completed is True:
            self._record_execution(user_id, task, changes)
        self._session.commit()
        refreshed = self._tasks.get_by_id(task_id)
        if refreshed is None:  # pragma: no cover - defensive
            raise NotFoundError("task not found in plan")
        return refreshed

    def _record_execution(self, user_id: int, task: Task, changes: dict) -> None:
        """Persist real execution data (ML data asset)."""
        execution = TaskExecution(
            task_id=task.id,
            user_id=user_id,
            planned_duration=task.predicted_duration or task.estimated_duration,
            actual_duration=changes.get("actual_duration"),
            completion_rate=1.0,
            started_at=changes.get("started_at"),
            finished_at=changes.get("finished_at"),
            difficulty_feedback=changes.get("difficulty_feedback"),
            stress_before=changes.get("stress_before"),
            stress_after=changes.get("stress_after"),
            failure_reason=changes.get("failure_reason"),
            completed=True,
        )
        self._executions.create(execution)
        # 环节 3 feedback reflow: an execution with real duration is an observation.
        if execution.actual_duration is not None:
            ProfileService(self._session).apply_feedback(
                user_id,
                actual_min=execution.actual_duration,
                theoretical_min=task.estimated_duration,
                completed=True,
            )
