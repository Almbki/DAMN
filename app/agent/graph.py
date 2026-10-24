"""Planner runtime: one dependency graph, two explicit workflows.

The previous "Graph A / Graph B" pair duplicated the analysis and generation
chain. They are now built from the same node set and the same edge helper:

**InitialPlanningWorkflow** (``initial`` compiled graph)

```
START -> load_context -> goal_analysis -> theoretical_analysis
      -> user_situation_analysis -> plan_generation -> rule_validation
      -[repair loop]-> preview (interrupt)
      -> [adjust -> plan_generation | confirm -> plan_finalization] -> END
```

**FeedbackReplanWorkflow / ManualReplanWorkflow** (``replan`` compiled graph)

```
START -> load_context -> process_feedback -> adjustment_decision -> adjustment_router
      |- NO_CHANGE    -> END
      |- MICRO_ADJUST -> micro_adjustment -> rule_validation -[repair]-> plan_finalization
      |- FULL_REPLAN  -> goal_analysis -> theoretical_analysis
                       -> user_situation_analysis -> plan_generation
                       -> rule_validation -[repair]-> plan_finalization -> END
```

* ``PreviewAdjustmentWorkflow`` is the resume path of the initial graph.
* The workflow is explicit in ``PlannerState["workflow"]`` - never inferred from
  free text or ambiguous fields.
* LangGraph only orchestrates: no node opens a session, the Rule Engine remains
  the sole authority on hard constraints, and Level 3 is not on this path.
"""

from __future__ import annotations

import dataclasses
import threading
import uuid
from typing import Any

from app.agent.checkpointer import get_checkpointer
from app.agent.nodes import (
    adjustment_decision_node,
    adjustment_router_node,
    goal_analysis_node,
    load_context_node,
    micro_adjustment_node,
    plan_finalization_node,
    plan_generation_node,
    plan_repair_node,
    preview_node,
    process_feedback_node,
    rule_validation_node,
    theoretical_analysis_node,
    user_situation_analysis_node,
)
from app.agent.router import route_after_adjustment, route_after_preview, should_repair
from app.agent.schemas import PreviewPayload, RequestIntent
from app.agent.state import PlannerContext, PlannerRequest, PlannerState

INITIAL_WORKFLOW_VERSION = "initial-plan-v2"
REPLAN_WORKFLOW_VERSION = "replan-v2"

#: Backwards-compatible names used by older traces/tests.
GRAPH_A_VERSION = INITIAL_WORKFLOW_VERSION
GRAPH_B_VERSION = REPLAN_WORKFLOW_VERSION

WORKFLOW_INITIAL = "initial_plan"
WORKFLOW_PREVIEW_ADJUST = "preview_adjust"
WORKFLOW_PREVIEW_CONFIRM = "preview_confirm"
WORKFLOW_FEEDBACK_REPLAN = "feedback_replan"
WORKFLOW_MANUAL_REPLAN = "manual_replan"


@dataclasses.dataclass
class RunEvents:
    """Collects agent events for one run (the Service turns them into SSE)."""

    events: list[dict] = dataclasses.field(default_factory=list)

    def sink(self, name: str, payload: dict) -> None:
        self.events.append({"event": name, **payload})

    def stages(self) -> list[str]:
        return [
            str(event.get("stage") or event.get("node") or event["event"])
            for event in self.events
        ]

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self):
        return iter(self.events)


GraphRun = RunEvents


def _require_langgraph():
    try:
        from langgraph.graph import END, START, StateGraph
        from langgraph.types import Command  # noqa: F401
    except Exception as exc:  # pragma: no cover - langgraph is a hard dependency
        raise RuntimeError(
            "langgraph is required for the agent graphs; run `uv sync --extra dev`"
        ) from exc
    return START, END, StateGraph


def _add_generation_chain(builder, *, exit_node: str) -> None:
    """Add the shared analysis -> generation -> validation chain."""
    builder.add_edge("goal_analysis", "theoretical_analysis")
    builder.add_edge("theoretical_analysis", "user_situation_analysis")
    builder.add_edge("user_situation_analysis", "plan_generation")
    builder.add_edge("plan_generation", "rule_validation")
    builder.add_conditional_edges(
        "rule_validation",
        should_repair,
        {"repair": "plan_repair", "continue": exit_node},
    )
    builder.add_edge("plan_repair", "rule_validation")


def build_initial_plan_graph(checkpointer: Any):
    """Compile the preview/confirm/adjust workflow."""
    START, END, StateGraph = _require_langgraph()
    builder = StateGraph(PlannerState, context_schema=PlannerContext)
    for name, node in (
        ("load_context", load_context_node),
        ("goal_analysis", goal_analysis_node),
        ("theoretical_analysis", theoretical_analysis_node),
        ("user_situation_analysis", user_situation_analysis_node),
        ("plan_generation", plan_generation_node),
        ("rule_validation", rule_validation_node),
        ("plan_repair", plan_repair_node),
        ("preview", preview_node),
        ("plan_finalization", plan_finalization_node),
    ):
        builder.add_node(name, node)

    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "goal_analysis")
    _add_generation_chain(builder, exit_node="preview")
    builder.add_conditional_edges(
        "preview",
        route_after_preview,
        {"revise": "plan_generation", "finalize": "plan_finalization"},
    )
    builder.add_edge("plan_finalization", END)
    return builder.compile(checkpointer=checkpointer)


def build_replan_graph(checkpointer: Any):
    """Compile the shared feedback/manual replan workflow."""
    START, END, StateGraph = _require_langgraph()
    builder = StateGraph(PlannerState, context_schema=PlannerContext)
    for name, node in (
        ("load_context", load_context_node),
        ("process_feedback", process_feedback_node),
        ("adjustment_decision", adjustment_decision_node),
        ("adjustment_router", adjustment_router_node),
        ("micro_adjustment", micro_adjustment_node),
        ("goal_analysis", goal_analysis_node),
        ("theoretical_analysis", theoretical_analysis_node),
        ("user_situation_analysis", user_situation_analysis_node),
        ("plan_generation", plan_generation_node),
        ("rule_validation", rule_validation_node),
        ("plan_repair", plan_repair_node),
        ("plan_finalization", plan_finalization_node),
    ):
        builder.add_node(name, node)

    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "process_feedback")
    builder.add_edge("process_feedback", "adjustment_decision")
    builder.add_edge("adjustment_decision", "adjustment_router")
    builder.add_conditional_edges(
        "adjustment_router",
        route_after_adjustment,
        {
            "no_change": END,
            "micro_adjust": "micro_adjustment",
            "full_replan": "goal_analysis",
        },
    )
    builder.add_edge("micro_adjustment", "rule_validation")
    _add_generation_chain(builder, exit_node="plan_finalization")
    builder.add_edge("plan_finalization", END)
    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------
_GRAPH_CACHE: dict[tuple[int, str], Any] = {}
_GRAPH_LOCK = threading.Lock()


def _cached_graph(kind: str, checkpointer: Any, builder) -> Any:
    key = (id(checkpointer), kind)
    graph = _GRAPH_CACHE.get(key)
    if graph is None:
        with _GRAPH_LOCK:
            graph = _GRAPH_CACHE.get(key)
            if graph is None:
                graph = builder(checkpointer)
                _GRAPH_CACHE[key] = graph
    return graph


class PlannerRuntime:
    """Stable entry point used by the application layer.

    The Service never touches LangGraph internals: it calls one of the four
    workflow methods and receives plain :class:`PlannerState` dictionaries plus
    :class:`PreviewPayload` objects.
    """

    def __init__(
        self,
        context: PlannerContext,
        *,
        checkpointer: Any | None = None,
    ) -> None:
        self.context = context
        self.checkpointer = checkpointer if checkpointer is not None else get_checkpointer()
        self.initial_graph = _cached_graph(
            "initial", self.checkpointer, build_initial_plan_graph
        )
        self.replan_graph = _cached_graph(
            "replan", self.checkpointer, build_replan_graph
        )

    # -- helpers -----------------------------------------------------------
    def _with_emit(self, sink) -> PlannerContext:
        return dataclasses.replace(self.context, emit=sink or self.context.emit)

    def _seed_state(
        self,
        request: PlannerRequest,
        *,
        workflow: str,
        run_id: str,
        thread_id: str,
        goal_id_map: dict[int, int] | None = None,
        replan_reason: str | None = None,
        user_adjustment: str | None = None,
    ) -> PlannerState:
        config = self.context.config
        return {
            "request": request,
            "user_id": request.user_id,
            "goals": list(request.goals),
            "goal_id_map": dict(goal_id_map or {}),
            "workflow": workflow,
            "run_id": run_id,
            "thread_id": thread_id,
            "adjustment_count": 0,
            "adjustment_rejected": False,
            "repair_attempts": 0,
            "max_repair_attempts": config.max_repair_attempts,
            "limit_factor": 1.0,
            "replan_reason": replan_reason,
            "user_adjustment": user_adjustment,
            "notes": [],
            "errors": [],
            "tool_results": [],
        }

    @staticmethod
    def _config(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def extract_preview(result: Any) -> PreviewPayload | None:
        interrupts = result.get("__interrupt__") if isinstance(result, dict) else None
        if not interrupts:
            return None
        interrupt = interrupts[0]
        value = getattr(interrupt, "value", interrupt)
        return PreviewPayload.model_validate(value)

    def pending_state(self, thread_id: str) -> PlannerState | None:
        snapshot = self.initial_graph.get_state(self._config(thread_id))
        if snapshot is None or not getattr(snapshot, "next", None):
            return None
        return dict(snapshot.values)

    # -- workflows ---------------------------------------------------------
    def start_initial(
        self,
        request: PlannerRequest,
        *,
        run_id: str | None = None,
        thread_id: str | None = None,
        goal_id_map: dict[int, int] | None = None,
        emit=None,
    ) -> tuple[PlannerState, PreviewPayload | None]:
        """InitialPlanningWorkflow: run until the preview interrupt."""
        run_id = run_id or uuid.uuid4().hex
        thread_id = thread_id or run_id
        ctx = self._with_emit(emit)
        state = self._seed_state(
            request,
            workflow=WORKFLOW_INITIAL,
            run_id=run_id,
            thread_id=thread_id,
            goal_id_map=goal_id_map,
        )
        ctx.publish(
            "workflow_started",
            {"workflow": WORKFLOW_INITIAL, "run_id": run_id, "version": INITIAL_WORKFLOW_VERSION},
        )
        result = self.initial_graph.invoke(state, self._config(thread_id), context=ctx)
        ctx.publish("agent.completed", {"run_id": run_id, "thread_id": thread_id})
        preview = self.extract_preview(result)
        if preview is not None:
            preview = preview.model_copy(update={"thread_id": thread_id})
        return result, preview

    def resume_preview(
        self,
        *,
        thread_id: str,
        action: str,
        feedback: str | None = None,
        emit=None,
    ) -> tuple[PlannerState, PreviewPayload | None]:
        """PreviewAdjustmentWorkflow / confirm resume."""
        from langgraph.types import Command

        ctx = self._with_emit(emit)
        workflow = (
            WORKFLOW_PREVIEW_ADJUST if action == "adjust" else WORKFLOW_PREVIEW_CONFIRM
        )
        ctx.publish(
            "workflow_started",
            {"workflow": workflow, "thread_id": thread_id, "action": action},
        )
        result = self.initial_graph.invoke(
            Command(resume={"action": action, "feedback": feedback}),
            self._config(thread_id),
            context=ctx,
        )
        ctx.publish("agent.completed", {"thread_id": thread_id, "action": action})
        preview = self.extract_preview(result)
        if preview is not None:
            preview = preview.model_copy(update={"thread_id": thread_id})
        return result, preview

    def run_feedback(
        self,
        request: PlannerRequest,
        *,
        run_id: str | None = None,
        thread_id: str | None = None,
        emit=None,
    ) -> PlannerState:
        """FeedbackReplanWorkflow."""
        run_id = run_id or uuid.uuid4().hex
        thread_id = thread_id or run_id
        ctx = self._with_emit(emit)
        state = self._seed_state(
            request,
            workflow=WORKFLOW_FEEDBACK_REPLAN,
            run_id=run_id,
            thread_id=thread_id,
        )
        ctx.publish(
            "workflow_started",
            {"workflow": WORKFLOW_FEEDBACK_REPLAN, "run_id": run_id,
             "version": REPLAN_WORKFLOW_VERSION},
        )
        result = self.replan_graph.invoke(state, self._config(thread_id), context=ctx)
        ctx.publish("agent.completed", {"run_id": run_id, "thread_id": thread_id})
        return result

    def run_manual_replan(
        self,
        request: PlannerRequest,
        *,
        reason: str | None = None,
        run_id: str | None = None,
        thread_id: str | None = None,
        emit=None,
    ) -> PlannerState:
        """ManualReplanWorkflow - same pipeline, explicit trigger + audit reason."""
        run_id = run_id or uuid.uuid4().hex
        thread_id = thread_id or run_id
        ctx = self._with_emit(emit)
        state = self._seed_state(
            request,
            workflow=WORKFLOW_MANUAL_REPLAN,
            run_id=run_id,
            thread_id=thread_id,
            replan_reason=reason or "user requested replan",
        )
        state["route"] = None
        ctx.publish(
            "workflow_started",
            {"workflow": WORKFLOW_MANUAL_REPLAN, "run_id": run_id, "reason": reason},
        )
        result = self.replan_graph.invoke(state, self._config(thread_id), context=ctx)
        ctx.publish("agent.completed", {"run_id": run_id, "thread_id": thread_id})
        return result

    # -- intent dispatch ---------------------------------------------------
    def run(
        self,
        intent: RequestIntent | str,
        request: PlannerRequest,
        **kwargs,
    ):
        """Explicit intent -> workflow. No state-field guessing."""
        try:
            resolved = RequestIntent(intent) if not isinstance(intent, RequestIntent) else intent
        except ValueError as exc:
            raise ValueError(f"unknown workflow intent: {intent}") from exc
        if resolved is RequestIntent.INITIAL_PLAN:
            return self.start_initial(request, **kwargs)
        if resolved is RequestIntent.REPLAN_REQUEST:
            return self.run_manual_replan(request, **kwargs)
        if resolved is RequestIntent.FEEDBACK_DRIVEN:
            return self.run_feedback(request, **kwargs)
        raise ValueError(f"intent {resolved.value} is a resume action, not an entry workflow")

    # -- deprecated aliases (remove after 1 release) -----------------------
    def generate_preview(self, request: PlannerRequest, **kwargs):
        return self.start_initial(request, **kwargs)

    def process_feedback(self, request: PlannerRequest, **kwargs):
        return self.run_feedback(request, **kwargs)

    def replan(self, request: PlannerRequest, **kwargs):
        return self.run_manual_replan(request, **kwargs)


#: Backwards-compatible alias for the previous facade name.
PlannerGraph = PlannerRuntime


__all__ = [
    "GRAPH_A_VERSION",
    "GRAPH_B_VERSION",
    "INITIAL_WORKFLOW_VERSION",
    "REPLAN_WORKFLOW_VERSION",
    "PlannerGraph",
    "PlannerRuntime",
    "RunEvents",
    "WORKFLOW_FEEDBACK_REPLAN",
    "WORKFLOW_INITIAL",
    "WORKFLOW_MANUAL_REPLAN",
    "WORKFLOW_PREVIEW_ADJUST",
    "WORKFLOW_PREVIEW_CONFIRM",
    "build_initial_plan_graph",
    "build_replan_graph",
]