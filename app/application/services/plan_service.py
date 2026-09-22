"""Plan service - orchestrates the agent graphs and persistence.

Boundary: the Service owns transactions, permissions and persistence; the agent
owns planning. The Service never touches LangGraph internals, and the agent never
touches a session.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.agent.context import ContextBuilderProtocol
from app.agent.graph import PlannerGraph, RunEvents
from app.agent.state import (
    AgentConfig,
    PlannerContext,
    PlannerRequest,
    PlannerState,
)
from app.application.context import RepoContextBuilder
from app.application.dto.agent import (
    AdjustPreviewResult,
    ConfirmResult,
    FeedbackCycleOutcome,
    PreviewResult,
    _warnings_from_state,
)
from app.application.dto.plan import PlanDetail, TaskWithStandards
from app.application.exceptions import NotFoundError, PermissionDeniedError
from app.core.config import get_settings
from app.domain.models import (
    AgentRun,
    Goal,
    Plan,
    PredictionLog,
    ReplanEvent,
    Task,
    TaskExecution,
    TaskStandard,
)
from app.domain.models.enums import (
    PlanStatus,
    ReplanTriggerType,
    TaskStatus,
)
from app.domain.rules.base import RuleEngine
from app.domain.scheduling.scheduler import Scheduler
from app.infrastructure.database.repositories import (
    AgentRunRepository,
    GoalRepository,
    PlanRepository,
    PredictionLogRepository,
    ReplanEventRepository,
    TaskExecutionRepository,
    TaskRepository,
    TaskStandardRepository,
    UserRepository,
)
from app.ml.predictors import PredictorSet

DEFAULT_HORIZON_DAYS = 13


class PlanService:
    def __init__(
        self,
        session: Session,
        *,
        predictors: PredictorSet | None = None,
        scheduler: Scheduler | None = None,
        rule_engine: RuleEngine | None = None,
        llm: Any | None = None,
        context_builder: ContextBuilderProtocol | None = None,
        checkpointer: Any | None = None,
        config: AgentConfig | None = None,
    ) -> None:
        self._session = session
        self._plans = PlanRepository(session)
        self._tasks = TaskRepository(session)
        self._standards = TaskStandardRepository(session)
        self._goals = GoalRepository(session)
        self._executions = TaskExecutionRepository(session)
        self._users = UserRepository(session)
        self._replan_events = ReplanEventRepository(session)
        self._agent_runs = AgentRunRepository(session)
        self._predictions = PredictionLogRepository(session)

        self.predictors = predictors or PredictorSet.default()
        self.scheduler = scheduler or Scheduler()
        self.rule_engine = rule_engine or RuleEngine()
        self.llm = llm
        self.config = config or _agent_config_from_settings()

        settings = get_settings()
        self._context_builder: ContextBuilderProtocol = (
            context_builder or RepoContextBuilder(session)
        )
        self.checkpointer = checkpointer
        self._settings = settings

    # -- graph wiring ------------------------------------------------------
    def _planner_context(self, emit=None) -> PlannerContext:
        return PlannerContext(
            scheduler=self.scheduler,
            rule_engine=self.rule_engine,
            predictors=self.predictors,
            config=self.config,
            llm=self.llm,
            context_builder=self._context_builder,
            emit=emit,
        )

    def _graph(self, emit=None) -> PlannerGraph:
        return PlannerGraph(self._planner_context(emit), checkpointer=self.checkpointer)

    # ------------------------------------------------------------------
    # Run wrapper: event sink + agent_runs trace
    # ------------------------------------------------------------------
    def _start_run(self, user_id: int, trigger_type: str) -> str:
        """Open an ``agent_runs`` row before the graph starts."""
        run_id = uuid4().hex
        self._agent_runs.create(
            AgentRun(
                run_id=run_id,
                user_id=user_id,
                trigger_type=trigger_type,
                graph_version=self.config.graph_version,
                prompt_version=self.config.prompt_version,
                status="running",
            )
        )
        self._session.commit()
        return run_id

    def _finish_run(
        self,
        run_id: str,
        events: RunEvents,
        *,
        llm_before: int,
        plan_id: int | None = None,
        status: str = "completed",
        error: str | None = None,
        summary: dict | None = None,
    ) -> None:
        """Close the ``agent_runs`` row with counts and a small summary.

        Only counts/summaries are stored - no prompt bodies, no free text.
        """
        # Derive from both node.started and node.completed: every node emits
        # `started`, but only some emit `completed` (preview pauses mid-node).
        nodes: list[str] = []
        for event in events:
            if event.get("event") not in {"node.started", "node.completed"}:
                continue
            node = event.get("node")
            if node and node not in nodes:
                nodes.append(str(node))
        tool_calls = [
            {
                "tool": event.get("tool"),
                "ok": event.get("ok"),
                "duration_ms": event.get("duration_ms"),
                "summary": event.get("summary"),
            }
            for event in events
            if event.get("event") == "tool.completed"
        ]
        self._agent_runs.update_fields(
            run_id,
            status=status,
            finished_at=datetime.now(UTC),
            nodes_executed=nodes,
            tool_calls=tool_calls,
            llm_calls=max(0, getattr(self.llm, "calls", 0) - llm_before),
            plan_id=plan_id,
            error=error,
            result_summary=dict(summary or {}),
        )
        if self._traces_enabled:
            self._session.commit()

    def _run(
        self,
        *,
        user_id: int,
        trigger_type: str,
        emit,
        call,
        summary: dict | None = None,
    ):
        """Execute a graph call, mirroring events to ``emit`` and recording a trace."""
        events = RunEvents()

        def sink(name: str, payload: dict) -> None:
            events.sink(name, payload)
            if emit is not None:
                emit(name, payload)

        llm_before = getattr(self.llm, "calls", 0)
        run_id = self._start_run(user_id, trigger_type)
        try:
            result = call(sink)
        except Exception as exc:  # noqa: BLE001 - record then re-raise
            self._finish_run(
                run_id,
                events,
                llm_before=llm_before,
                status="failed",
                error=f"{type(exc).__name__}: {exc}"[:2000],
                summary=summary,
            )
            self._session.commit()
            raise
        self._finish_run(run_id, events, llm_before=llm_before, summary=summary)
        return result, events, run_id

    def _link_run(self, run_id: str, *, plan_id: int | None, summary: dict | None = None) -> None:
        """Attach the produced plan to the run (the plan only exists after persistence)."""
        fields: dict[str, object] = {}
        if plan_id is not None:
            fields["plan_id"] = plan_id
        if summary:
            fields["result_summary"] = summary
        if not fields:
            return
        self._agent_runs.update_fields(run_id, **fields)
        if self._traces_enabled:
            self._session.commit()

    @property
    def _traces_enabled(self) -> bool:
        return bool(getattr(self.config, "trace_enabled", True))

    # ------------------------------------------------------------------
    # Preview / confirm / adjust
    # ------------------------------------------------------------------
    def generate_preview(
        self, user_id: int, request: PlannerRequest, *, emit=None
    ) -> PreviewResult:
        """Persist goals, run graph A and return the paused preview."""
        self._require_user(user_id)
        goal_id_map = self._persist_goals(user_id, request)
        # Commit the goals before the graph runs: preview and confirm are separate
        # requests with separate sessions, so an uncommitted goal id would dangle
        # (the returned goal_id_map must point at real rows).
        self._session.commit()
        graph = self._graph()
        # `_run` returns (graph_result, events, run_id); graph A's result is
        # (state, preview).
        (state, preview), _events, _run_id = self._run(
            user_id=user_id,
            trigger_type="initial_plan",
            emit=emit,
            call=lambda sink: graph.generate_preview(
                request, goal_id_map=goal_id_map, emit=sink
            ),
            summary={"stage": "preview"},
        )

        if preview is None:  # pragma: no cover - graph A always pauses
            raise RuntimeError("plan generation finished without a preview")
        warnings = _warnings_from_state(state)
        return PreviewResult(
            thread_id=preview.thread_id,
            preview=preview,
            goals_persisted=len(goal_id_map),
            degraded=bool(warnings),
            warnings=warnings,
        )

    def confirm_plan(self, user_id: int, thread_id: str, *, emit=None) -> ConfirmResult:
        """Confirm the preview and persist v1."""
        self._authorise_thread(user_id, thread_id)
        graph = self._graph()
        (state, preview), _events, run_id = self._run(
            user_id=user_id,
            trigger_type="confirm_preview",
            emit=emit,
            call=lambda sink: graph.resume_preview(
                thread_id=thread_id, action="confirm", emit=sink
            ),
            summary={"stage": "confirm", "thread_id": thread_id},
        )
        warnings = _warnings_from_state(state)
        if preview is not None:  # pragma: no cover - confirm always finalises
            return ConfirmResult(
                detail=self.get_plan(user_id, 0),
                pending_preview=preview,
                degraded=bool(warnings),
                warnings=warnings,
            )
        detail = self._persist_final_plan(user_id, state)
        self._link_run(
            run_id,
            plan_id=detail.plan.id,
            summary={
                "stage": "confirm",
                "plan_id": detail.plan.id,
                "version": detail.plan.version,
                "tasks": len(detail.tasks),
                "confidence": detail.plan.confidence,
                "degraded": bool(warnings),
            },
        )
        return ConfirmResult(
            detail=detail,
            degraded=bool(warnings),
            warnings=warnings,
        )

    def adjust_preview(
        self, user_id: int, thread_id: str, feedback: str, *, emit=None
    ) -> AdjustPreviewResult:
        """Apply a bounded user adjustment.

        Returns another preview when the budget allows it, or the finalised plan
        when the budget is exhausted (the user is pushed into execution).
        """
        self._authorise_thread(user_id, thread_id)
        graph = self._graph()
        (state, preview), _events, run_id = self._run(
            user_id=user_id,
            trigger_type="preview_adjusted",
            emit=emit,
            call=lambda sink: graph.resume_preview(
                thread_id=thread_id, action="adjust", feedback=feedback, emit=sink
            ),
            summary={"stage": "adjust", "thread_id": thread_id},
        )
        warnings = _warnings_from_state(state)
        if preview is not None:
            self._link_run(
                run_id,
                plan_id=None,
                summary={
                    "stage": "adjust",
                    "thread_id": thread_id,
                    "adjustment_count": preview.adjustment_count,
                    "tasks": len(preview.tasks),
                },
            )
            return AdjustPreviewResult(
                thread_id=thread_id,
                preview=preview,
                budget_exhausted=not preview.can_adjust,
                degraded=bool(warnings),
                warnings=warnings,
            )

        detail = self._persist_final_plan(user_id, state)
        self._link_run(
            run_id,
            plan_id=detail.plan.id,
            summary={
                "stage": "adjust_finalized",
                "plan_id": detail.plan.id,
                "version": detail.plan.version,
                "tasks": len(detail.tasks),
                "degraded": bool(warnings),
            },
        )
        return AdjustPreviewResult(
            thread_id=thread_id,
            preview=None,
            budget_exhausted=True,
            plan_id=detail.plan.id,
            degraded=bool(warnings),
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Backwards-compatible convenience: preview + auto-confirm
    # ------------------------------------------------------------------
    def generate_plan(
        self, user_id: int, request: PlannerRequest, user_features: Any = None
    ) -> PlanDetail:
        detail, _preview = self.generate_plan_with_events(user_id, request)
        return detail

    def generate_plan_with_events(
        self, user_id: int, request: PlannerRequest, user_features: Any = None
    ) -> tuple[PlanDetail, RunEvents]:
        """Generate and immediately confirm (used by the SSE endpoint)."""
        events = RunEvents()
        result = self.generate_preview(user_id, request, emit=events.sink)
        confirmed = self.confirm_plan(user_id, result.thread_id, emit=events.sink)
        if confirmed.pending_preview is not None:  # pragma: no cover - auto-confirm
            raise RuntimeError("auto-confirm left the graph paused")
        return confirmed.detail, events

    # ------------------------------------------------------------------
    # Feedback cycle
    # ------------------------------------------------------------------
    def process_feedback_cycle(
        self, user_id: int, plan_id: int, *, note: str | None = None, emit=None
    ) -> FeedbackCycleOutcome:
        """Run graph B and persist a new version when the route requires it."""
        self.get_plan(user_id, plan_id)  # permission check
        request = self._planner_request_for_plan(user_id, plan_id, note=note)
        graph = self._graph()
        state, _events, run_id = self._run(
            user_id=user_id,
            trigger_type="feedback_cycle",
            emit=emit,
            call=lambda sink: graph.process_feedback(request, emit=sink),
            summary={"stage": "feedback", "plan_id": plan_id},
        )

        prediction = state.get("ml_prediction")
        warnings = _warnings_from_state(state)
        outcome = FeedbackCycleOutcome(
            route=state.get("route") or _no_change(),
            severity=prediction.severity if prediction else _no_severity(),
            reasons=list(prediction.reasons) if prediction else [],
            source=prediction.source if prediction else "fallback",
            plan_id=plan_id,
            degraded=bool(warnings),
            warnings=warnings,
        )
        if state.get("final_plan") is None:
            self._link_run(
                run_id,
                plan_id=plan_id,
                summary={
                    "stage": "feedback",
                    "plan_id": plan_id,
                    "route": outcome.route.value,
                    "changed": False,
                },
            )
            return outcome

        detail = self._persist_final_plan(
            user_id,
            state,
            parent_plan_id=plan_id,
            replan_reason=f"feedback cycle: {outcome.route.value}",
        )
        outcome.new_plan_id = detail.plan.id
        self._link_run(
            run_id,
            plan_id=detail.plan.id,
            summary={
                "stage": "feedback",
                "from_plan_id": plan_id,
                "plan_id": detail.plan.id,
                "version": detail.plan.version,
                "route": outcome.route.value,
                "source": outcome.source,
                "tasks": len(detail.tasks),
                "degraded": outcome.degraded,
            },
        )
        return outcome

    # ------------------------------------------------------------------
    # Agent replan
    # ------------------------------------------------------------------
    def replan_with_agent(
        self, user_id: int, plan_id: int, *, reason: str | None = None, emit=None
    ) -> PlanDetail:
        """Explicit replan through graph B (cooldown is checked by the caller)."""
        self.get_plan(user_id, plan_id)  # permission check
        request = self._planner_request_for_plan(user_id, plan_id, note=reason)
        graph = self._graph()
        state, _events, run_id = self._run(
            user_id=user_id,
            trigger_type="replan",
            emit=emit,
            call=lambda sink: graph.replan(request, reason=reason, emit=sink),
            summary={"stage": "replan", "plan_id": plan_id},
        )
        final = state.get("final_plan")
        if final is None:
            raise NotFoundError("replan produced no plan")
        detail = self._persist_final_plan(
            user_id,
            state,
            parent_plan_id=plan_id,
            replan_reason=reason or "user requested replan",
        )
        self._link_run(
            run_id,
            plan_id=detail.plan.id,
            summary={
                "stage": "replan",
                "plan_id": detail.plan.id,
                "version": detail.plan.version,
                "trigger_source": final.trigger_source,
                "tasks": len(detail.tasks),
            },
        )
        return detail

    # ------------------------------------------------------------------
    # Reads / task updates (unchanged public API)
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _require_user(self, user_id: int) -> None:
        if self._users.get_by_id(user_id) is None:
            raise NotFoundError("user not found")

    def _authorise_thread(self, user_id: int, thread_id: str) -> None:
        graph = self._graph()
        state = graph.pending_state(thread_id)
        if state is None:
            raise NotFoundError("no pending preview for this thread")
        if state.get("user_id") != user_id:
            raise PermissionDeniedError("preview belongs to another user")

    def _persist_goals(self, user_id: int, request: PlannerRequest) -> dict[int, int]:
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

    def _planner_request_for_plan(
        self, user_id: int, plan_id: int, *, note: str | None
    ) -> PlannerRequest:
        detail = self.get_plan(user_id, plan_id)
        goals = _goal_inputs(detail)
        plan = detail.plan
        return PlannerRequest(
            user_id=user_id,
            plan_id=plan_id,
            user_note=note,
            plan_title=plan.title,
            start_date=plan.start_date,
            end_date=plan.end_date,
            goals=goals,
        )

    def _persist_final_plan(
        self,
        user_id: int,
        state: PlannerState,
        *,
        parent_plan_id: int | None = None,
        replan_reason: str | None = None,
    ) -> PlanDetail:
        final = state.get("final_plan")
        if final is None:
            raise NotFoundError("no final plan on the agent state")
        request = state.get("request")
        goal_id_map = dict(state.get("goal_id_map") or {})
        schedule = state.get("candidate_plan")
        placed = {item.task_id: item for item in (schedule.tasks if schedule else [])}

        previous = self._plans.get_latest_by_user(user_id)
        if previous is not None and previous.id is not None:
            self._plans.update_status(previous.id, PlanStatus.SUPERSEDED)

        plan = Plan(
            user_id=user_id,
            version=self._plans.next_version(user_id),
            status=PlanStatus.ACTIVE,
            title=final.title or (request.plan_title if request else None),
            start_date=final.start_date or (request.start_date if request else date.today()),
            end_date=final.end_date
            or (
                request.end_date
                if request
                else date.today() + timedelta(days=DEFAULT_HORIZON_DAYS)
            ),
            parent_plan_id=parent_plan_id or (previous.id if previous else None),
            confidence=final.confidence,
        )
        plan = self._plans.create(plan)

        tasks: list[Task] = []
        standards: list[TaskStandard] = []
        for order, draft in enumerate(final.tasks):
            slot = placed.get(order + 1)  # PROVISIONAL TASK ID CONTRACT
            tasks.append(
                Task(
                    plan_id=plan.id,
                    goal_id=goal_id_map.get(draft.goal_id or 0, draft.goal_id),
                    title=draft.title,
                    description=draft.description,
                    estimated_duration=max(draft.estimated_duration, 1),
                    predicted_duration=draft.predicted_duration,
                    cognitive_load=draft.cognitive_load,
                    priority=draft.priority,
                    scheduled_date=slot.scheduled_date if slot else None,
                    start_time=slot.start_time if slot else None,
                    end_time=slot.end_time if slot else None,
                    status=TaskStatus.SCHEDULED,
                    completion_probability=draft.completion_probability,
                    order_index=order,
                )
            )
        created_tasks = self._tasks.create_many(tasks)
        self._log_predictions(
            user_id, plan.id or 0, list(zip(created_tasks, final.tasks, strict=False))
        )

        for task, draft in zip(created_tasks, final.tasks, strict=False):
            per_standard = max(len(draft.standards), 1)
            for std_order, description in enumerate(draft.standards):
                standards.append(
                    TaskStandard(
                        task_id=task.id,
                        description=description,
                        estimated_duration=max(task.estimated_duration // per_standard, 5),
                        order_index=std_order,
                    )
                )
        if standards:
            self._standards.create_many(standards)

        if final.trigger_source in {"replan", "micro_adjust"}:
            self._replan_events.create(
                ReplanEvent(
                    plan_id=plan.id or 0,
                    trigger_type=ReplanTriggerType.FEEDBACK_TRIGGERED
                    if final.trigger_source == "micro_adjust"
                    else ReplanTriggerType.MANUAL,
                    reason=replan_reason or final.trigger_source,
                    old_version=plan.version - 1,
                    new_version=plan.version,
                    changed_tasks=[task.id or 0 for task in created_tasks],
                )
            )

        self._session.commit()
        return self.get_plan(user_id, plan.id or 0)

    @staticmethod
    def _feature_hash(user_id: int, draft, prediction_type: str) -> str:
        """Stable fingerprint of the feature vector a prediction was made from.

        Lets us detect drift ("the same user/task shape now predicts very
        differently") without storing the whole vector.
        """
        load = getattr(draft.cognitive_load, "value", draft.cognitive_load)
        raw = "|".join(
            [
                str(user_id),
                prediction_type,
                draft.title or "",
                str(draft.estimated_duration),
                str(load),
                str(int(draft.priority)),
                draft.subject or "",
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _log_predictions(self, user_id: int, plan_id: int, pairs: list[tuple[Task, Any]]) -> int:
        """Record every per-task prediction so it can be scored later.

        This is the missing half of the ML feedback loop: without the predicted
        value next to the later actual (``task_executions``) there is no way to
        compute MAE / Brier or to tell whether a new model is better.
        """
        entries: list[PredictionLog] = []
        for task, draft in pairs:
            if task.id is None:  # pragma: no cover - create_many assigns ids
                continue
            source = draft.prediction_source or "unknown"
            common = {
                "user_id": user_id,
                "plan_id": plan_id,
                "task_id": task.id,
                "model_name": source,
                "model_version": "",
                "source": source,
            }
            if draft.predicted_duration is not None:
                entries.append(
                    PredictionLog(
                        prediction_type="duration",
                        predicted={
                            "predicted_minutes": draft.predicted_duration,
                            "theoretical_minutes": draft.estimated_duration,
                        },
                        feature_hash=self._feature_hash(user_id, draft, "duration"),
                        **common,
                    )
                )
            if draft.completion_probability is not None:
                entries.append(
                    PredictionLog(
                        prediction_type="completion",
                        predicted={"probability": draft.completion_probability},
                        feature_hash=self._feature_hash(user_id, draft, "completion"),
                        **common,
                    )
                )
            if draft.predicted_stress is not None:
                entries.append(
                    PredictionLog(
                        prediction_type="stress",
                        predicted={"predicted_stress": draft.predicted_stress},
                        feature_hash=self._feature_hash(user_id, draft, "stress"),
                        **common,
                    )
                )
            if draft.recommended_time_slot is not None:
                slot = getattr(draft.recommended_time_slot, "value", draft.recommended_time_slot)
                entries.append(
                    PredictionLog(
                        prediction_type="time_slot",
                        predicted={"slot": str(slot)},
                        feature_hash=self._feature_hash(user_id, draft, "time_slot"),
                        **common,
                    )
                )
        if entries:
            self._predictions.create_many(entries)
        return len(entries)

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


def _agent_config_from_settings() -> AgentConfig:
    settings = get_settings()
    return AgentConfig(
        max_preview_adjustments=settings.agent_max_preview_adjustments,
        max_repair_attempts=settings.agent_max_repair_attempts,
        llm_max_retries=settings.agent_llm_max_retries,
        llm_timeout_seconds=settings.agent_llm_timeout_seconds,
        graph_version=settings.agent_graph_version,
        prompt_version=settings.agent_prompt_version,
        trace_enabled=settings.agent_trace_enabled,
    )


def _no_change():
    from app.ml.base import AdjustmentRoute

    return AdjustmentRoute.NO_CHANGE


def _no_severity():
    from app.ml.base import AdjustmentSeverity

    return AdjustmentSeverity.NONE


def _goal_inputs(detail: PlanDetail) -> list:
    """Rebuild graph goal inputs from the persisted goals (subject from options)."""
    from app.agent.state import GoalInput

    inputs = []
    for goal in detail.goals:
        options = goal.options or {}
        inputs.append(
            GoalInput(
                title=goal.title,
                description=goal.description,
                goal_type=goal.goal_type,
                deadline=goal.deadline,
                priority=goal.priority,
                estimated_minutes=goal.estimated_minutes,
                subject=options.get("subject"),
                task_type=options.get("task_type"),
            )
        )
    return inputs


__all__ = ["DEFAULT_HORIZON_DAYS", "PlanService"]
