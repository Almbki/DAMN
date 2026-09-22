"""LangGraph state machines + the :class:`PlannerGraph` facade.

Two graphs, one responsibility each:

**Graph A - initial plan** (``GRAPH_A_VERSION``)

```
START -> load_context -> classify_request -> goal_analysis
      -> theoretical_analysis -> user_situation_analysis -> plan_generation
      -> rule_validation -[repair loop]-> preview (interrupt)
      -> [adjust -> plan_generation | confirm -> plan_finalization] -> END
```

**Graph B - feedback loop** (``GRAPH_B_VERSION``)

```
START -> load_context -> process_feedback -> ml_prediction -> adjustment_router
      |- NO_CHANGE   -> END
      |- MICRO_ADJUST -> micro_adjustment -> rule_validation -[repair]-> new_plan -> END
      |- FULL_REPLAN  -> goal_analysis -> theoretical_analysis -> user_situation_analysis
                      -> plan_generation -> rule_validation -[repair]-> new_plan -> END
```

LangGraph orchestrates only: no node opens a session, and the Rule Engine remains
the sole authority on hard constraints. Dependencies arrive through the run
context (:class:`PlannerContext`), never through the state.
"""

from __future__ import annotations

import dataclasses
import uuid
from datetime import UTC, datetime
from typing import Any

from app.agent.checkpointer import get_checkpointer
from app.agent.nodes import (
    adjustment_router_node,
    classify_request_node,
    goal_analysis_node,
    load_context_node,
    micro_adjustment_node,
    ml_prediction_node,
    new_plan_node,
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
from app.agent.schemas import FinalPlanPayload, PreviewPayload
from app.agent.state import (
    PlannerContext,
    PlannerRequest,
    PlannerState,
    RunMetadata,
)

GRAPH_A_VERSION = "initial-plan-v1"
GRAPH_B_VERSION = "feedback-loop-v1"


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


#: Alias kept for readability in type hints.
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


# ---------------------------------------------------------------------------
# Graph A
# ---------------------------------------------------------------------------
def build_initial_plan_graph(checkpointer: Any):
    """Compile the preview/confirm/adjust state machine."""
    START, END, StateGraph = _require_langgraph()

    builder = StateGraph(PlannerState, context_schema=PlannerContext)
    builder.add_node("load_context", load_context_node)
    builder.add_node("classify_request", classify_request_node)
    builder.add_node("goal_analysis", goal_analysis_node)
    builder.add_node("theoretical_analysis", theoretical_analysis_node)
    builder.add_node("user_situation_analysis", user_situation_analysis_node)
    builder.add_node("plan_generation", plan_generation_node)
    builder.add_node("rule_validation", rule_validation_node)
    builder.add_node("plan_repair", plan_repair_node)
    builder.add_node("preview", preview_node)
    builder.add_node("plan_finalization", plan_finalization_node)

    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "classify_request")
    builder.add_edge("classify_request", "goal_analysis")
    builder.add_edge("goal_analysis", "theoretical_analysis")
    builder.add_edge("theoretical_analysis", "user_situation_analysis")
    builder.add_edge("user_situation_analysis", "plan_generation")
    builder.add_edge("plan_generation", "rule_validation")
    builder.add_conditional_edges(
        "rule_validation", should_repair, {"repair": "plan_repair", "continue": "preview"}
    )
    builder.add_edge("plan_repair", "rule_validation")
    builder.add_conditional_edges(
        "preview",
        route_after_preview,
        {"revise": "plan_generation", "finalize": "plan_finalization"},
    )
    builder.add_edge("plan_finalization", END)
    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Graph B
# ---------------------------------------------------------------------------
def build_feedback_loop_graph(checkpointer: Any):
    """Compile the feedback -> route -> adjust/replan state machine."""
    START, END, StateGraph = _require_langgraph()

    builder = StateGraph(PlannerState, context_schema=PlannerContext)
    builder.add_node("load_context", load_context_node)
    builder.add_node("process_feedback", process_feedback_node)
    builder.add_node("ml_prediction", ml_prediction_node)
    builder.add_node("adjustment_router", adjustment_router_node)
    builder.add_node("micro_adjustment", micro_adjustment_node)
    builder.add_node("goal_analysis", goal_analysis_node)
    builder.add_node("theoretical_analysis", theoretical_analysis_node)
    builder.add_node("user_situation_analysis", user_situation_analysis_node)
    builder.add_node("plan_generation", plan_generation_node)
    builder.add_node("rule_validation", rule_validation_node)
    builder.add_node("plan_repair", plan_repair_node)
    builder.add_node("new_plan", new_plan_node)

    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "process_feedback")
    builder.add_edge("process_feedback", "ml_prediction")
    builder.add_edge("ml_prediction", "adjustment_router")
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

    builder.add_edge("goal_analysis", "theoretical_analysis")
    builder.add_edge("theoretical_analysis", "user_situation_analysis")
    builder.add_edge("user_situation_analysis", "plan_generation")
    builder.add_edge("plan_generation", "rule_validation")
    builder.add_conditional_edges(
        "rule_validation", should_repair, {"repair": "plan_repair", "continue": "new_plan"}
    )
    builder.add_edge("plan_repair", "rule_validation")
    builder.add_edge("new_plan", END)
    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------
#: Compiled graphs are stateless once built, so cache them per checkpointer.
#: (Compiling a StateGraph on every request would be wasteful.)
_GRAPH_CACHE: dict[tuple[int, str], Any] = {}


def _cached_graph(kind: str, checkpointer: Any, builder) -> Any:
    key = (id(checkpointer), kind)
    if key not in _GRAPH_CACHE:
        _GRAPH_CACHE[key] = builder(checkpointer)
    return _GRAPH_CACHE[key]


class PlannerGraph:
    """Stable entry point used by the application layer.

    The Service never touches LangGraph internals: it calls the high level
    methods below and receives plain :class:`PlannerState` dictionaries plus
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
        self.feedback_graph = _cached_graph(
            "feedback", self.checkpointer, build_feedback_loop_graph
        )

    # -- helpers -----------------------------------------------------------
    def _with_emit(self, sink) -> PlannerContext:
        """Per-call context copy carrying this call's event sink.

        ``sink=None`` falls back to the sink already installed on the context, so
        a Service that wires the sink once (``self._graph(emit)``) does not have
        to pass it to every graph call.
        """
        return dataclasses.replace(self.context, emit=sink or self.context.emit)

    def _seed_state(
        self,
        request: PlannerRequest,
        *,
        graph_version: str,
        run_id: str,
        goal_id_map: dict[int, int] | None = None,
        replan_reason: str | None = None,
        user_adjustment: str | None = None,
    ) -> PlannerState:
        # Budgets come from AgentConfig (Settings) - never hardcode them here,
        # otherwise AGENT_MAX_REPAIR_ATTEMPTS is silently ignored.
        config = self.context.config
        return {
            "request": request,
            "user_id": request.user_id,
            "goals": list(request.goals),
            "goal_id_map": dict(goal_id_map or {}),
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
            "metadata": RunMetadata(
                run_id=run_id,
                user_id=request.user_id,
                trigger_type=request.trigger_type.value,
                graph_version=graph_version,
                prompt_version=config.prompt_version,
                started_at=datetime.now(UTC),
            ),
        }

    @staticmethod
    def _config(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def extract_preview(result: Any) -> PreviewPayload | None:
        """Pull the paused preview out of an interrupted run, if any."""
        interrupts = result.get("__interrupt__") if isinstance(result, dict) else None
        if not interrupts:
            return None
        interrupt = interrupts[0]
        value = getattr(interrupt, "value", interrupt)
        payload = PreviewPayload.model_validate(value)
        return payload

    @staticmethod
    def extract_final_plan(result: Any) -> FinalPlanPayload | None:
        if not isinstance(result, dict):
            return None
        final = result.get("final_plan")
        return final if isinstance(final, FinalPlanPayload) else None

    def pending_state(self, thread_id: str) -> PlannerState | None:
        """State of a paused preview, or ``None`` when the thread is finished.

        Used by the Service to authorise a confirm/adjust *before* resuming.
        """
        snapshot = self.initial_graph.get_state(self._config(thread_id))
        if snapshot is None or not getattr(snapshot, "next", None):
            return None
        return dict(snapshot.values)

    # -- high level API ----------------------------------------------------
    def generate_preview(
        self,
        request: PlannerRequest,
        *,
        run_id: str | None = None,
        thread_id: str | None = None,
        goal_id_map: dict[int, int] | None = None,
        emit=None,
    ) -> tuple[PlannerState, PreviewPayload | None]:
        """Run graph A until it pauses for confirmation."""
        run_id = run_id or uuid.uuid4().hex
        thread_id = thread_id or run_id
        ctx = self._with_emit(emit)
        state = self._seed_state(
            request, graph_version=GRAPH_A_VERSION, run_id=run_id, goal_id_map=goal_id_map
        )
        ctx.publish("agent.started", {"run_id": run_id, "graph": GRAPH_A_VERSION})
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
        """Resume a paused preview with ``confirm`` or ``adjust``."""
        from langgraph.types import Command

        ctx = self._with_emit(emit)
        ctx.publish("agent.started", {"thread_id": thread_id, "action": action})
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

    def process_feedback(
        self,
        request: PlannerRequest,
        *,
        run_id: str | None = None,
        thread_id: str | None = None,
        emit=None,
    ) -> PlannerState:
        """Run graph B: feedback -> prediction -> route -> adjust/replan."""
        run_id = run_id or uuid.uuid4().hex
        thread_id = thread_id or run_id
        ctx = self._with_emit(emit)
        state = self._seed_state(request, graph_version=GRAPH_B_VERSION, run_id=run_id)
        ctx.publish("agent.started", {"run_id": run_id, "graph": GRAPH_B_VERSION})
        result = self.feedback_graph.invoke(state, self._config(thread_id), context=ctx)
        ctx.publish("agent.completed", {"run_id": run_id, "thread_id": thread_id})
        return result

    def replan(
        self,
        request: PlannerRequest,
        *,
        reason: str | None = None,
        run_id: str | None = None,
        thread_id: str | None = None,
        emit=None,
    ) -> PlannerState:
        """Explicit replan: graph B with a forced replan reason."""
        run_id = run_id or uuid.uuid4().hex
        thread_id = thread_id or run_id
        ctx = self._with_emit(emit)
        state = self._seed_state(
            request,
            graph_version=GRAPH_B_VERSION,
            run_id=run_id,
            replan_reason=reason or "user requested replan",
        )
        state["route"] = None
        ctx.publish("replanning.started", {"run_id": run_id, "reason": reason})
        result = self.feedback_graph.invoke(state, self._config(thread_id), context=ctx)
        ctx.publish("replanning.completed", {"run_id": run_id})
        return result

    # -- low level (kept for compatibility) --------------------------------
    def invoke(
        self,
        request: PlannerRequest,
        *,
        user_features: Any = None,
        goal_id_map: dict[int, int] | None = None,
    ) -> PlannerState:
        """Non-interactive run of graph A (no preview pause).

        Used by tests and by callers that do not need user confirmation.
        """
        state = self._seed_state(
            request,
            graph_version=GRAPH_A_VERSION,
            run_id=uuid.uuid4().hex,
            goal_id_map=goal_id_map,
        )
        ctx = self._with_emit(None)
        return self.initial_graph.invoke(state, self._config(uuid.uuid4().hex), context=ctx)

    def run_with_events(
        self,
        request: PlannerRequest,
        *,
        user_features: Any = None,
        goal_id_map: dict[int, int] | None = None,
    ) -> tuple[PlannerState, list[dict]]:
        """Non-interactive run that also returns the emitted event list."""
        events: list[dict] = []

        def sink(name: str, payload: dict) -> None:
            events.append({"event": name, **payload})

        state = self._seed_state(
            request,
            graph_version=GRAPH_A_VERSION,
            run_id=uuid.uuid4().hex,
            goal_id_map=goal_id_map,
        )
        ctx = self._with_emit(sink)
        result = self.initial_graph.invoke(
            state, self._config(uuid.uuid4().hex), context=ctx
        )
        return result, events


def create_planner_graph(context: PlannerContext, **kwargs: Any) -> PlannerGraph:
    """Convenience factory used by the Service layer."""
    return PlannerGraph(context, **kwargs)


__all__ = [
    "GRAPH_A_VERSION",
    "GRAPH_B_VERSION",
    "PlannerGraph",
    "build_feedback_loop_graph",
    "build_initial_plan_graph",
    "create_planner_graph",
]
