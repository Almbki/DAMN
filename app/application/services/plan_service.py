"""Plan service - orchestrates the agent graphs and persistence.

Boundary: the Service owns transactions, permissions and persistence; the agent
owns planning. The Service never touches LangGraph internals, and the agent never
touches a session.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, date, datetime, time, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.agent.context import ContextBuilderProtocol
from app.agent.graph import PlannerGraph, RunEvents
from app.agent.schemas import RequestIntent
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
from app.application.dto.plan import (
    PlanChange,
    PlanDetail,
    TaskWithStandards,
    diff_days,
)
from app.application.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.application.services.user_model_service import UserModelService
from app.core.config import get_settings
from app.domain.feedback.models import AdjustmentRoute, AdjustmentSeverity
from app.domain.models import (
    AgentRun,
    Goal,
    Plan,
    PredictionLog,
    ReplanEvent,
    Task,
    TaskEvent,
    TaskExecution,
    TaskStandard,
)
from app.domain.models.enums import (
    CognitiveLoad,
    PlanStatus,
    Priority,
    ReplanTriggerType,
    TaskStatus,
)
from app.domain.rules.base import RuleEngine
from app.domain.scheduling.constants import DEFAULT_HORIZON_DAYS
from app.domain.scheduling.scheduler import Scheduler
from app.infrastructure.database.repositories import (
    AgentRunRepository,
    GoalRepository,
    PlanRepository,
    PredictionLogRepository,
    ReplanEventRepository,
    TaskEventRepository,
    TaskExecutionRepository,
    TaskRepository,
    TaskStandardRepository,
    UserRepository,
)

logger = logging.getLogger(__name__)

#: ``prediction_logs.model_name`` / ``.source`` are VARCHAR(64). A wider value
#: used to raise StringDataRightTruncation and abort the confirm transaction.
_PREDICTION_SOURCE_MAX_LEN = 64

#: Bounded text columns written from LLM output. Over-long free text used to
#: raise StringDataRightTruncation and abort the confirm transaction.
_TITLE_MAX_LEN = 255
_DESCRIPTION_MAX_LEN = 1000
_STANDARD_MAX_LEN = 500
#: Task PATCH fields that belong to ``task_executions``, not ``tasks``.
_EXECUTION_FIELDS: tuple[str, ...] = (
    "actual_duration",
    "difficulty_feedback",
    "stress_before",
    "stress_after",
    "failure_reason",
    "interruption_count",
    "execution_status",
    "failure_category",
    "estimate_feedback",
    "started_at",
    "finished_at",
)

#: Task PATCH fields that only move a task in time (-> ``rescheduled`` events).
_RESCHEDULE_FIELDS: frozenset[str] = frozenset({"scheduled_date", "start_time", "end_time"})


class PlanService:
    def __init__(
        self,
        session: Session,
        *,
        scheduler: Scheduler | None = None,
        rule_engine: RuleEngine | None = None,
        llm: Any | None = None,
        context_builder: ContextBuilderProtocol | None = None,
        checkpointer: Any | None = None,
        config: AgentConfig | None = None,
        user_model_service: UserModelService | None = None,
    ) -> None:
        self._session = session
        self._plans = PlanRepository(session)
        self._tasks = TaskRepository(session)
        self._task_events = TaskEventRepository(session)
        self._standards = TaskStandardRepository(session)
        self._goals = GoalRepository(session)
        self._executions = TaskExecutionRepository(session)
        self._users = UserRepository(session)
        self._replan_events = ReplanEventRepository(session)
        self._agent_runs = AgentRunRepository(session)
        self._predictions = PredictionLogRepository(session)
        self._user_models = user_model_service or UserModelService(session)

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

    def close(self) -> None:
        """Close the session owned by this service.

        Used by detached workers (background generation jobs) that build their
        own ``PlanService`` and must release the session when the run is over.
        """
        self._session.close()

    # -- graph wiring ------------------------------------------------------
    def _planner_context(self, emit=None) -> PlannerContext:
        return PlannerContext(
            scheduler=self.scheduler,
            rule_engine=self.rule_engine,
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
    def _start_run(self, user_id: int, trigger_type: str, *, run_id: str | None = None) -> str:
        """Open an ``agent_runs`` row before the graph starts."""
        run_id = run_id or uuid4().hex
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
        run_id: str | None = None,
    ):
        """Execute a graph call, mirroring events to ``emit`` and recording a trace.

        ``run_id`` may be pre-generated by the caller so it can double as the
        LangGraph ``thread_id`` (see `generate_preview`).
        """
        events = RunEvents()

        def sink(name: str, payload: dict) -> None:
            events.sink(name, payload)
            if emit is not None:
                emit(name, payload)

        llm_before = getattr(self.llm, "calls", 0)
        run_id = self._start_run(user_id, trigger_type, run_id=run_id)
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
        # Pre-generate the run id so it can double as the LangGraph thread_id:
        # the frontend's `draft_id` is then the same handle the trace uses.
        draft_id = uuid4().hex
        (state, preview), _events, _run_id = self._run(
            user_id=user_id,
            trigger_type="initial_plan",
            emit=emit,
            run_id=draft_id,
            call=lambda sink: graph.generate_preview(
                request, run_id=draft_id, goal_id_map=goal_id_map, emit=sink
            ),
            summary={"stage": "preview", "draft_id": draft_id},
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
                detail=None,
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
                "thread_id": thread_id,
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
    def generate_plan_with_events(
        self, user_id: int, request: PlannerRequest, *, emit=None
    ) -> tuple[PlanDetail, RunEvents]:
        """Generate and immediately confirm (used by the SSE endpoint).

        Every event is recorded on the returned ``events`` and mirrored to
        ``emit`` (the async job's live sink) when one is supplied.
        """
        events = RunEvents()

        def sink(name: str, payload: dict) -> None:
            events.sink(name, payload)
            if emit is not None:
                emit(name, payload)

        result = self.generate_preview(user_id, request, emit=sink)
        confirmed = self.confirm_plan(user_id, result.thread_id, emit=sink)
        if confirmed.pending_preview is not None:  # pragma: no cover - auto-confirm
            raise RuntimeError("auto-confirm left the graph paused")
        return confirmed.detail, events

    # ------------------------------------------------------------------
    # Feedback cycle
    # ------------------------------------------------------------------
    def process_feedback_cycle(
        self,
        user_id: int,
        plan_id: int,
        *,
        note: str | None = None,
        route: str | None = None,
        emit=None,
    ) -> FeedbackCycleOutcome:
        """Run the replan workflow and persist a new version when required."""
        self.get_plan(user_id, plan_id)  # permission check
        request = self._planner_request_for_plan(
            user_id,
            plan_id,
            note=note,
            trigger_type=RequestIntent.FEEDBACK_DRIVEN,
            feedback_route=route,
        )
        graph = self._graph()
        state, _events, run_id = self._run(
            user_id=user_id,
            trigger_type="feedback_cycle",
            emit=emit,
            call=lambda sink: graph.process_feedback(request, emit=sink),
            summary={"stage": "feedback", "plan_id": plan_id},
        )

        prediction = state.get("adjustment")
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
        request = self._planner_request_for_plan(
            user_id,
            plan_id,
            note=reason,
            trigger_type=RequestIntent.REPLAN_REQUEST,
        )
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
        # Read-model only: expose the active execution start so a refresh can
        # still show "in progress" without leaking execution entities.
        active_starts: dict[int, datetime] = {}
        for execution in self._executions.list_by_user(user_id, limit=2000):
            if (
                execution.started_at is not None
                and not execution.completed
                and execution.finished_at is None
            ):
                active_starts.setdefault(execution.task_id, execution.started_at)
        for task in tasks:
            if task.status in {TaskStatus.COMPLETED, TaskStatus.SKIPPED}:
                continue
            task.started_at = active_starts.get(task.id or 0)
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
        # Snapshot before the in-place update: the event log is append-only.
        before_snapshot = task.model_dump(mode="json")

        completed = changes.pop("completed", None)
        # Execution-only fields are not Task columns. They used to be silently
        # dropped when `completed` was not True; now every provided execution
        # field produces a TaskExecution row (partial completion included).
        execution_payload = {
            field: changes.pop(field)
            for field in _EXECUTION_FIELDS
            if field in changes
        }
        completion_rate = changes.pop("completion_rate", None)
        if completed is True:
            changes.setdefault("status", TaskStatus.COMPLETED)
        if "status" in changes and isinstance(changes["status"], str):
            changes["status"] = TaskStatus(changes["status"])
        # Explicit user override: persist as-is, only normalise enum values.
        if "priority" in changes and not isinstance(changes["priority"], Priority):
            changes["priority"] = Priority(int(changes["priority"]))
        if "cognitive_load" in changes and not isinstance(
            changes["cognitive_load"], CognitiveLoad
        ):
            changes["cognitive_load"] = CognitiveLoad(changes["cognitive_load"])
        if changes:
            updated = self._tasks.update_fields(task_id, **changes)
            task = updated or task

        for update in standard_updates or []:
            standard_id = update.get("id")
            if standard_id is None:
                continue
            self._standards.update_fields(standard_id, completed=bool(update.get("completed")))

        recorded_execution = (
            completed is True or bool(execution_payload) or completion_rate is not None
        )
        if recorded_execution:
            rate = (
                1.0
                if completed is True
                else float(completion_rate if completion_rate is not None else 0.0)
            )
            self._record_execution(
                user_id,
                task,
                execution_payload,
                completed=bool(completed),
                completion_rate=rate,
            )
        if changes:
            # The task row is updated in place; history lives in task_events.
            self._task_events.create(
                TaskEvent(
                    user_id=user_id,
                    task_id=task_id,
                    event_type=_task_event_type(changes),
                    before={
                        key: before_snapshot[key]
                        for key in changes
                        if key in before_snapshot
                    } or None,
                    after={key: _jsonable(value) for key, value in changes.items()} or None,
                )
            )
        self._session.commit()
        if recorded_execution:
            # After the task commit, so a model failure can never roll back the
            # user's own execution record.
            self._refresh_user_model(user_id)
            try:
                self._user_models.record_prediction_outcome(user_id, task.id)
                # The outcome repository only flushes; the service owns the commit.
                self._session.commit()
            except Exception:  # noqa: BLE001 - best effort; the execution row is the record
                logger.warning(
                    "prediction outcome recording failed for user=%s task=%s",
                    user_id,
                    task.id,
                    exc_info=True,
                )
                self._session.rollback()
        refreshed = self._tasks.get_by_id(task_id)
        if refreshed is None:  # pragma: no cover - defensive
            raise NotFoundError("task not found in plan")
        return refreshed

    def delete_task(
        self,
        user_id: int,
        plan_id: int,
        task_id: int,
        reason: str | None = None,
    ) -> None:
        """Soft-delete a task, keeping its executions / standards intact.

        Permission is checked through ``get_plan`` (same 404/403 semantics as the
        other task endpoints). Idempotent: deleting an already-deleted task is a
        no-op and still succeeds.
        """
        self.get_plan(user_id, plan_id)  # permission check
        task = self._tasks.get_by_id(task_id, include_deleted=True)
        if task is None or task.plan_id != plan_id:
            raise NotFoundError("task not found in plan")
        already_deleted = task.deleted_at is not None
        if not self._tasks.soft_delete(task_id, reason):
            raise NotFoundError("task not found in plan")
        if not already_deleted:
            # Idempotent repeat deletes change nothing, so they add no event.
            self._task_events.create(
                TaskEvent(
                    user_id=user_id,
                    task_id=task_id,
                    event_type="deleted",
                    reason=reason,
                )
            )
        self._session.commit()

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def latest_changed_task_ids(self, plan_id: int) -> list[int]:
        """Changed task ids recorded by the newest ReplanEvent for this plan."""
        event = self._replan_events.get_latest_for_plan(plan_id)
        return list(event.changed_tasks) if event is not None else []

    def _require_user(self, user_id: int) -> None:
        if self._users.get_by_id(user_id) is None:
            raise NotFoundError("user not found")

    # ------------------------------------------------------------------
    # Draft handle (the frontend's `draft_id` is the LangGraph thread_id)
    # ------------------------------------------------------------------
    @property
    def max_preview_adjustments(self) -> int:
        return self.config.max_preview_adjustments

    def pending_draft(self, user_id: int, draft_id: str) -> PlannerState:
        """Return the paused draft state, enforcing ownership.

        Raises ``ConflictError`` (409) when the draft was already confirmed and
        ``NotFoundError`` (404) when it never existed / expired.
        """
        state = self._graph().pending_state(draft_id)
        if state is None:
            if self._already_confirmed(user_id, draft_id):
                raise ConflictError("draft was already confirmed")
            raise NotFoundError("draft not found or expired")
        if state.get("user_id") != user_id:
            raise PermissionDeniedError("draft belongs to another user")
        return state

    def _already_confirmed(self, user_id: int, draft_id: str) -> bool:
        """True when a confirm run already consumed this draft.

        The draft itself is gone from the checkpointer once confirmed, so the
        `agent_runs` trace is what distinguishes "already confirmed" (409) from
        "never existed" (404).
        """
        for run in self._agent_runs.list_by_user(user_id, limit=200):
            if run.trigger_type != "confirm_preview":
                continue
            if (run.result_summary or {}).get("thread_id") == draft_id:
                return True
        return False

    def _authorise_thread(self, user_id: int, thread_id: str) -> None:
        self.pending_draft(user_id, thread_id)

    # ------------------------------------------------------------------
    # Plan change history (frontend: "系统改了未来哪几天")
    # ------------------------------------------------------------------
    def list_changes(self, user_id: int, plan_id: int) -> list[PlanChange]:
        """Replan events for this plan with a per-day task diff.

        The diff is derived by comparing the task rows of the previous version
        with the new one (plan versions are immutable, so both are still in the
        database). That keeps `replan_events` unchanged - no extra column.
        """
        self.get_plan(user_id, plan_id)  # permission check
        changes: list[PlanChange] = []
        for event in self._replan_events.list_by_plan(plan_id):
            old_plan = self._plans.get_by_user_and_version(user_id, event.old_version)
            old_tasks = (
                self._tasks.list_by_plan(old_plan.id)
                if old_plan is not None and old_plan.id is not None
                else []
            )
            new_tasks = self._tasks.list_by_plan(event.plan_id)
            changes.append(
                PlanChange(
                    id=event.id or 0,
                    trigger_type=event.trigger_type,
                    reason=event.reason or "",
                    old_version=event.old_version,
                    new_version=event.new_version,
                    created_at=event.created_at,
                    days=diff_days(old_tasks, new_tasks),
                )
            )
        return changes

    def _persist_goals(self, user_id: int, request: PlannerRequest) -> dict[int, int]:
        goals: list[Goal] = []
        for goal_input in request.goals:
            goals.append(
                Goal(
                    user_id=user_id,
                    title=self._clip(goal_input.title, _TITLE_MAX_LEN),
                    description=self._clip(goal_input.description, _DESCRIPTION_MAX_LEN),
                    goal_type=goal_input.goal_type,
                    deadline=goal_input.deadline,
                    priority=goal_input.priority,
                    estimated_minutes=goal_input.estimated_minutes,
                    start_date=goal_input.start_date,
                    task_kind=goal_input.task_kind,
                    daily_target_minutes=goal_input.daily_target_minutes,
                    recurrence_weekdays=goal_input.recurrence_weekdays,
                    target_amount=goal_input.target_amount,
                    target_unit=goal_input.target_unit,
                    options={"subject": goal_input.subject, "task_type": goal_input.task_type},
                )
            )
        created = self._goals.create_many(goals)
        return {index + 1: goal.id for index, goal in enumerate(created) if goal.id is not None}

    def _planner_request_for_plan(
        self,
        user_id: int,
        plan_id: int,
        *,
        note: str | None,
        trigger_type: RequestIntent,
        feedback_route: str | None = None,
    ) -> PlannerRequest:
        detail = self.get_plan(user_id, plan_id)
        goals = _goal_inputs(detail)
        plan = detail.plan
        return PlannerRequest(
            user_id=user_id,
            plan_id=plan_id,
            trigger_type=trigger_type,
            user_note=note,
            feedback_route=feedback_route,
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
        old_tasks = (
            self._tasks.list_by_plan(previous.id)
            if previous is not None and previous.id is not None
            else []
        )
        if previous is not None and previous.id is not None:
            self._plans.update_status(previous.id, PlanStatus.SUPERSEDED)

        parent = (
            self._plans.get_by_id(parent_plan_id)
            if parent_plan_id is not None
            else None
        )
        data_origin = parent.data_origin if parent is not None else "real"
        plan = Plan(
            user_id=user_id,
            version=self._plans.next_version(user_id),
            status=PlanStatus.ACTIVE,
            title=self._clip(
                final.title or (request.plan_title if request else None), _TITLE_MAX_LEN
            )
            or (request.plan_title if request else None),
            start_date=final.start_date or (request.start_date if request else date.today()),
            end_date=final.end_date
            or (
                request.end_date
                if request
                else date.today() + timedelta(days=DEFAULT_HORIZON_DAYS)
            ),
            parent_plan_id=parent_plan_id or (previous.id if previous else None),
            confidence=final.confidence,
            data_origin=data_origin,
        )
        plan = self._plans.create(plan)

        tasks: list[Task] = []
        standards: list[TaskStandard] = []
        for order, draft in enumerate(final.tasks):
            # PROVISIONAL TASK ID CONTRACT: the scheduler keys placements by the
            # draft's own order_index, which may have gaps after a repair drop.
            slot = placed.get(draft.order_index + 1)
            tasks.append(
                Task(
                    plan_id=plan.id,
                    goal_id=goal_id_map.get(draft.goal_id or 0, draft.goal_id),
                    title=self._clip(draft.title, _TITLE_MAX_LEN),
                    description=self._clip(draft.description, _DESCRIPTION_MAX_LEN),
                    # The planner already resolved a goal-level deadline; keep it
                    # on the task row so Level 2/3 and the UI can use it.
                    deadline=draft.deadline.date() if draft.deadline is not None else None,
                    estimated_duration=max(draft.estimated_duration, 1),
                    predicted_duration=draft.predicted_duration,
                    cognitive_load=draft.cognitive_load,
                    priority=draft.priority,
                    scheduled_date=slot.scheduled_date if slot else None,
                    start_time=slot.start_time if slot else None,
                    end_time=slot.end_time if slot else None,
                    status=TaskStatus.SCHEDULED,
                    completion_probability=draft.completion_probability,
                    prediction_source=draft.prediction_source or "deterministic:workload_estimate",
                    prediction_mode="production",
                    data_origin=plan.data_origin,
                    is_flexible=draft.is_flexible,
                    task_kind=draft.task_kind,
                    series_id=draft.series_id,
                    series_index=draft.series_index,
                    occurrence_date=draft.occurrence_date,
                    target_amount=draft.target_amount,
                    target_unit=draft.target_unit,
                    order_index=order,
                )
            )
        created_tasks = self._tasks.create_many(tasks)
        prediction_origin = (
            "synthetic"
            if self._user_models.has_synthetic_observations(user_id)
            else plan.data_origin
        )
        self._log_predictions(
            user_id,
            plan.id or 0,
            list(zip(created_tasks, final.tasks, strict=False)),
            data_origin=prediction_origin,
        )

        for task, draft in zip(created_tasks, final.tasks, strict=False):
            per_standard = max(len(draft.standards), 1)
            for std_order, description in enumerate(draft.standards):
                standards.append(
                    TaskStandard(
                        task_id=task.id,
                        description=self._clip(description, _STANDARD_MAX_LEN),
                        estimated_duration=max(task.estimated_duration // per_standard, 5),
                        order_index=std_order,
                    )
                )
        if standards:
            self._standards.create_many(standards)

        if final.trigger_source in {
            "manual_replan",
            "feedback_full_replan",
            "micro_adjust",
        }:
            changed_ids = self._changed_task_ids(old_tasks, created_tasks)
            self._replan_events.create(
                ReplanEvent(
                    plan_id=plan.id or 0,
                    trigger_type=(
                        ReplanTriggerType.MANUAL
                        if final.trigger_source == "manual_replan"
                        else ReplanTriggerType.FEEDBACK_TRIGGERED
                    ),
                    reason=replan_reason or final.trigger_source,
                    old_version=plan.version - 1,
                    new_version=plan.version,
                    changed_tasks=changed_ids,
                )
            )

        self._session.commit()
        detail = self.get_plan(user_id, plan.id or 0)
        # Level 3 shadow runs only AFTER the production plan is persisted. It
        # cannot mutate the plan, scheduler or rule engine, and any failure is
        # contained to the audit table.
        self._run_level3_shadow(user_id, detail, state)
        return detail

    @staticmethod
    def _changed_task_ids(old_tasks: list[Task], new_tasks: list[Task]) -> list[int]:
        """New/changed task ids by matching stable identity, not row ids.

        Plan versions are immutable and re-created, so a row id always changes.
        A task is "changed" only when its identity (title, goal, schedule,
        duration) did not exist in the previous version.
        """
        def identity(task: Task) -> tuple:
            return (
                task.title,
                task.goal_id,
                task.scheduled_date,
                task.start_time,
                task.end_time,
                task.estimated_duration,
                task.task_kind,
                task.series_id,
                task.series_index,
            )

        old_identities = {identity(task) for task in old_tasks}
        return [
            task.id or 0
            for task in new_tasks
            if identity(task) not in old_identities
        ]

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

    @staticmethod
    def _short_source(value: str | None) -> str:
        """Fit a prediction source into ``prediction_logs`` VARCHAR(64).

        Provenance is stamped from the ML predictor by ``PlanDrafterTool``, so
        this is a last-resort guard: an over-long source must degrade, not abort
        the whole confirm transaction with a DB truncation error.
        """
        source = (value or "unknown").strip() or "unknown"
        if len(source) <= _PREDICTION_SOURCE_MAX_LEN:
            return source
        logger.warning(
            "prediction source too long (%d chars, max %d); truncating: %.80s",
            len(source),
            _PREDICTION_SOURCE_MAX_LEN,
            source,
        )
        return source[:_PREDICTION_SOURCE_MAX_LEN]

    @staticmethod
    def _clip(value: str | None, limit: int) -> str | None:
        """Fit free text into a bounded column (``limit`` chars).

        LLM output is unbounded; an over-long title/description must degrade to
        a truncated prefix rather than abort the confirm transaction with a DB
        ``StringDataRightTruncation``.
        """
        if value is None:
            return None
        text = str(value).strip()
        if len(text) <= limit:
            return text
        logger.warning(
            "text too long (%d chars, max %d); truncating: %.80s",
            len(text),
            limit,
            text,
        )
        return text[:limit]

    def _log_predictions(
        self,
        user_id: int,
        plan_id: int,
        pairs: list[tuple[Task, Any]],
        *,
        data_origin: str = "real",
    ) -> int:
        """Record every per-task prediction so it can be scored later.

        This is the missing half of the ML feedback loop: without the predicted
        value next to the later actual (``task_executions``) there is no way to
        compute MAE / Brier or to tell whether a new model is better.
        """
        entries: list[PredictionLog] = []
        for task, draft in pairs:
            if task.id is None:  # pragma: no cover - create_many assigns ids
                continue
            source = self._short_source(draft.prediction_source)
            common = {
                "user_id": user_id,
                "plan_id": plan_id,
                "task_id": task.id,
                "model_name": source,
                "model_version": "",
                "source": source,
                "data_origin": data_origin,
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

    def _update_profile_from_execution(self, user_id: int, task: Task, changes: dict) -> None:
        """Deprecated name kept for callers; refreshes Level 2 instead of EWMA."""
        self._refresh_user_model(user_id)

    def _refresh_user_model(self, user_id: int) -> None:
        """Recompute the real Level 2 state after new observations (best effort)."""
        try:
            self._user_models.refresh_dynamic_state(user_id)
        except Exception:  # noqa: BLE001 - the execution row is the record
            logger.warning("level2 refresh failed for user=%s", user_id, exc_info=True)
            self._session.rollback()

    def _run_level3_shadow(self, user_id: int, detail: PlanDetail, state: PlannerState) -> None:
        """Run Level 3 sidecar inference; never affects the persisted plan."""
        context = state.get("user_context")
        user_model = context.user_model if context is not None else None
        try:
            written = self._user_models.run_shadow_for_plan(
                user_id=user_id,
                plan_id=detail.plan.id,
                tasks=[item.task for item in detail.tasks],
                context=user_model,
                # Provenance of this plan, not a user-global flag: a real plan
                # stays 'real' even when the user once imported synthetic data.
                data_origin=detail.plan.data_origin or "real",
            )
            if written:
                self._session.commit()
        except Exception:  # noqa: BLE001 - shadow must never break production
            logger.warning(
                "level3 shadow run failed for user=%s plan=%s",
                user_id,
                detail.plan.id,
                exc_info=True,
            )
            self._session.rollback()

    def _record_execution(
        self,
        user_id: int,
        task: Task,
        changes: dict,
        *,
        completed: bool = True,
        completion_rate: float = 1.0,
    ) -> None:
        """Persist real execution data (the Level 2/3 data asset)."""
        execution_status = changes.get("execution_status")
        if execution_status is None:
            execution_status = _derive_execution_status(completed, completion_rate, changes)
        execution = TaskExecution(
            task_id=task.id,
            user_id=user_id,
            planned_duration=task.predicted_duration or task.estimated_duration,
            actual_duration=changes.get("actual_duration"),
            completion_rate=max(0.0, min(1.0, float(completion_rate))),
            started_at=changes.get("started_at"),
            finished_at=changes.get("finished_at"),
            difficulty_feedback=changes.get("difficulty_feedback"),
            stress_before=changes.get("stress_before"),
            stress_after=changes.get("stress_after"),
            failure_reason=changes.get("failure_reason"),
            interruption_count=changes.get("interruption_count"),
            execution_status=execution_status,
            failure_category=changes.get("failure_category"),
            estimate_feedback=changes.get("estimate_feedback"),
            completed=completed,
            data_origin=task.data_origin or "real",
        )
        self._executions.create(execution)


def _jsonable(value: Any) -> Any:
    """Normalise a patch value into a JSON-serialisable form."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _task_event_type(changes: dict) -> str:
    """Classify one task patch for the append-only event log."""
    keys = set(changes)
    if "status" in keys:
        return "status_changed"
    if keys and keys <= _RESCHEDULE_FIELDS:
        return "rescheduled"
    return "edited"


def _derive_execution_status(
    completed: bool, completion_rate: float, changes: dict
) -> str | None:
    """Infer the outcome label when the user did not provide one.

    Starting a task without any result is *not* an observation: without
    ``finished_at`` / ``actual_duration`` the status stays ``None``.
    """
    if completed or completion_rate >= 1:
        return "completed"
    if 0 < completion_rate < 1:
        return "partial"
    if changes.get("finished_at") is not None or changes.get("actual_duration") is not None:
        return "not_done"
    return None


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
    return AdjustmentRoute.NO_CHANGE


def _no_severity():
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
                start_date=goal.start_date,
                task_kind=goal.task_kind,
                daily_target_minutes=goal.daily_target_minutes,
                recurrence_weekdays=goal.recurrence_weekdays,
                target_amount=goal.target_amount,
                target_unit=goal.target_unit,
            )
        )
    return inputs


__all__ = ["DEFAULT_HORIZON_DAYS", "PlanService"]
