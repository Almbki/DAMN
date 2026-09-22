"""LangGraph orchestration for the planning pipeline.

The graph has six nodes with the exact names below. LangGraph only
orchestrates: it never touches the database, never imports
``app.infrastructure`` at runtime and never decides hard constraints - the Rule
Engine does. Every node returns structured Pydantic schemas (or schedule value
objects) into the :class:`PlannerState`.

If ``langgraph`` is unavailable (or the graph build fails) :class:`PlannerGraph`
silently falls back to a deterministic sequential executor implementing the
same node order and repair loop, so the project always starts.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from app.agent.nodes import (
    goal_analysis_node,
    plan_generation_node,
    plan_repair_node,
    rule_validation_node,
    theoretical_analysis_node,
    user_situation_analysis_node,
)
from app.agent.state import GenerationRequest, PlannerState
from app.domain.rules.base import RuleEngine
from app.domain.scheduling.scheduler import Scheduler
from app.ml.base import UserFeatureSet
from app.ml.predictors import PredictorSet

if TYPE_CHECKING:  # pragma: no cover
    from app.infrastructure.llm.client import LLMClient

#: Fixed node names. Used verbatim by LangGraph AND the fallback executor.
NODE_ORDER: tuple[str, ...] = (
    "goal_analysis",
    "theoretical_analysis",
    "user_situation_analysis",
    "plan_generation",
    "rule_validation",
)

NODE_FUNCTIONS: dict[str, Callable[[dict], dict]] = {
    "goal_analysis": goal_analysis_node,
    "theoretical_analysis": theoretical_analysis_node,
    "user_situation_analysis": user_situation_analysis_node,
    "plan_generation": plan_generation_node,
    "rule_validation": rule_validation_node,
    "plan_repair": plan_repair_node,
}


class GenerationEvent(BaseModel):
    """One observable step of a plan generation run."""

    node: str
    stage: str = "complete"
    status: str = "ok"
    summary: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# --------------------------------------------------------------------------
# event helpers
# --------------------------------------------------------------------------


def _event_summary(node_name: str, updates: dict) -> str:
    """Short human-readable summary derived from a node's state updates."""
    if node_name == "goal_analysis":
        result = updates.get("goal_analysis")
        return f"Analyzed {len(result.goals)} goal(s)" if result else "Goal analysis"
    if node_name == "theoretical_analysis":
        result = updates.get("theoretical_workload")
        if result:
            return (
                f"Estimated {result.total_theoretical_minutes} min across "
                f"{len(result.items)} item(s)"
            )
        return "Theoretical analysis"
    if node_name == "user_situation_analysis":
        result = updates.get("user_situation")
        if result:
            return (
                f"Completion {result.completion_ability:.2f}, stress "
                f"{result.stress_state:.1f}, load {result.fatigue_state.value}"
            )
        return "User situation analysis"
    if node_name == "plan_generation":
        result = updates.get("plan_draft")
        return f"Proposed {len(result.tasks)} task draft(s)" if result else "Plan generation"
    if node_name == "rule_validation":
        violations = updates.get("rule_violations") or []
        return f"{len(violations)} hard violation(s)" if violations else "Schedule valid"
    if node_name == "plan_repair":
        result = updates.get("repaired_plan")
        if result:
            return (
                f"Changed {len(result.changed_task_ids)} task(s)"
                if result.changed_task_ids
                else "No change needed"
            )
        return "Plan repair"
    return node_name


def _normalize_progress(events: list[GenerationEvent]) -> None:
    """Fill ``progress`` uniformly once the run length is known."""
    total = max(len(events), 1)
    for index, event in enumerate(events):
        event.progress = round((index + 1) / total, 4)


def _synthesize_events(state: dict) -> list[GenerationEvent]:
    """Linear event list reconstructed from a final state (fallback path)."""
    events: list[GenerationEvent] = []
    key_by_node = {
        "goal_analysis": "goal_analysis",
        "theoretical_analysis": "theoretical_workload",
        "user_situation_analysis": "user_situation",
        "plan_generation": "plan_draft",
        "rule_validation": "rule_validation",
    }
    for node_name, state_key in key_by_node.items():
        value = state.get(state_key)
        if value is None:
            continue
        updates: dict = {state_key: value}
        if node_name == "rule_validation":
            violations = getattr(value, "violations", None)
            updates["rule_violations"] = list(violations) if violations else []
        events.append(
            GenerationEvent(
                node=node_name,
                stage=node_name,
                summary=_event_summary(node_name, updates),
                payload=updates,
            )
        )
    repaired = state.get("repaired_plan")
    if repaired is not None:
        events.append(
            GenerationEvent(
                node="plan_repair",
                stage="plan_repair",
                summary=_event_summary("plan_repair", {"repaired_plan": repaired}),
                payload={"repaired_plan": repaired},
            )
        )
    return events


# --------------------------------------------------------------------------
# state finalization
# --------------------------------------------------------------------------


def _finalize(state: dict) -> PlannerState:
    """Fill the output keys a run may leave unset (final plan / confidence)."""
    state = dict(state)

    if state.get("final_plan") is None:
        state["final_plan"] = state.get("candidate_plan")
    if state.get("final_tasks") is None:
        repaired = state.get("repaired_plan")
        plan_draft = state.get("plan_draft")
        if repaired is not None and getattr(repaired, "tasks", None):
            state["final_tasks"] = list(repaired.tasks)
        elif plan_draft is not None and getattr(plan_draft, "tasks", None):
            state["final_tasks"] = list(plan_draft.tasks)
        else:
            state["final_tasks"] = []

    if state.get("confidence") is None:
        confidences = [
            float(obj.confidence)
            for key in ("goal_analysis", "theoretical_workload", "user_situation")
            if (obj := state.get(key)) is not None
            and getattr(obj, "confidence", None) is not None
        ]
        state["confidence"] = round(sum(confidences) / len(confidences), 4) if confidences else 0.5

    if state.get("notes") is None:
        state["notes"] = []
    if state.get("events") is None:
        state["events"] = []
    return state  # type: ignore[return-value]  # PlannerState is a TypedDict


# --------------------------------------------------------------------------
# runners
# --------------------------------------------------------------------------


def _should_repair(state: dict, max_repair_attempts: int) -> str:
    """Conditional edge: repair while hard violations remain and budget allows."""
    violations = state.get("rule_violations") or []
    attempts = state.get("repair_attempts") or 0
    if violations and attempts < max_repair_attempts:
        return "repair"
    return "done"


class _LangGraphRunner:
    """StateGraph-backed runner (used when ``langgraph`` is installed)."""

    def __init__(
        self,
        *,
        llm: LLMClient | None,
        predictors: PredictorSet | None,
        scheduler: Scheduler | None,
        rule_engine: RuleEngine | None,
        max_repair_attempts: int,
    ) -> None:
        # Imported lazily so this module is importable without langgraph.
        from langgraph.graph import END, START, StateGraph

        self.max_repair_attempts = max_repair_attempts
        graph = StateGraph(PlannerState)
        for name, func in NODE_FUNCTIONS.items():
            graph.add_node(name, func)
        graph.add_edge(START, "goal_analysis")
        graph.add_edge("goal_analysis", "theoretical_analysis")
        graph.add_edge("theoretical_analysis", "user_situation_analysis")
        graph.add_edge("user_situation_analysis", "plan_generation")
        graph.add_edge("plan_generation", "rule_validation")
        graph.add_conditional_edges(
            "rule_validation",
            lambda state: _should_repair(state, self.max_repair_attempts),
            {"repair": "plan_repair", "done": END},
        )
        graph.add_edge("plan_repair", "rule_validation")
        self._graph = graph.compile()

    def run(self, state: dict) -> PlannerState:
        return _finalize(self._graph.invoke(dict(state)))

    def run_with_events(self, state: dict) -> tuple[PlannerState, list[GenerationEvent]]:
        events: list[GenerationEvent] = []
        merged = dict(state)
        try:
            for chunk in self._graph.stream(dict(state), stream_mode="updates"):
                for node_name, updates in chunk.items():
                    merged.update(updates)
                    events.append(
                        GenerationEvent(
                            node=node_name,
                            stage=node_name,
                            summary=_event_summary(node_name, updates),
                            payload=updates,
                        )
                    )
            final = _finalize(merged)
        except Exception:  # noqa: BLE001 - stream API drift between langgraph versions
            final = _finalize(self._graph.invoke(dict(state)))
            events = _synthesize_events(final)
        _normalize_progress(events)
        return final, events


class _SequentialRunner:
    """Deterministic fallback executor - same node order + repair loop.

    Used only when ``langgraph`` cannot be imported or the graph build fails.
    """

    def __init__(
        self,
        *,
        llm: LLMClient | None,
        predictors: PredictorSet | None,
        scheduler: Scheduler | None,
        rule_engine: RuleEngine | None,
        max_repair_attempts: int,
    ) -> None:
        self.max_repair_attempts = max_repair_attempts

    def _step(self, state: dict, node_name: str, events: list[GenerationEvent] | None) -> dict:
        updates = NODE_FUNCTIONS[node_name](state)
        state.update(updates)
        if events is not None:
            events.append(
                GenerationEvent(
                    node=node_name,
                    stage=node_name,
                    summary=_event_summary(node_name, updates),
                    payload=updates,
                )
            )
        return state

    def _pipeline(self, state: dict, events: list[GenerationEvent] | None = None) -> dict:
        for name in NODE_ORDER:
            self._step(state, name, events)
        while True:
            violations = state.get("rule_violations") or []
            attempts = state.get("repair_attempts") or 0
            if not (violations and attempts < self.max_repair_attempts):
                break
            self._step(state, "plan_repair", events)
            self._step(state, "rule_validation", events)
        return state

    def run(self, state: dict) -> PlannerState:
        return _finalize(self._pipeline(dict(state)))

    def run_with_events(self, state: dict) -> tuple[PlannerState, list[GenerationEvent]]:
        events: list[GenerationEvent] = []
        final = _finalize(self._pipeline(dict(state), events))
        _normalize_progress(events)
        return final, events


# --------------------------------------------------------------------------
# public factories
# --------------------------------------------------------------------------


def _build_runner(
    *,
    llm: LLMClient | None,
    predictors: PredictorSet | None,
    scheduler: Scheduler | None,
    rule_engine: RuleEngine | None,
    max_repair_attempts: int,
):
    """Pick the LangGraph runner or the deterministic sequential fallback.

    The StateGraph construction is wrapped in ``try/except`` so the project
    always starts even when ``langgraph`` is missing or a build step fails.
    """
    try:
        return _LangGraphRunner(
            llm=llm,
            predictors=predictors,
            scheduler=scheduler,
            rule_engine=rule_engine,
            max_repair_attempts=max_repair_attempts,
        )
    except Exception:  # noqa: BLE001 - ImportError and any graph-build failure
        return _SequentialRunner(
            llm=llm,
            predictors=predictors,
            scheduler=scheduler,
            rule_engine=rule_engine,
            max_repair_attempts=max_repair_attempts,
        )


def build_planner_graph(
    *,
    llm: LLMClient | None = None,
    predictors: PredictorSet | None = None,
    scheduler: Scheduler | None = None,
    rule_engine: RuleEngine | None = None,
    max_repair_attempts: int = 2,
) -> PlannerGraph:
    """Build a :class:`PlannerGraph` backed by LangGraph (or the fallback)."""
    return PlannerGraph(
        llm=llm,
        predictors=predictors,
        scheduler=scheduler,
        rule_engine=rule_engine,
        max_repair_attempts=max_repair_attempts,
    )


def create_planner_graph(*args: Any, **kwargs: Any) -> PlannerGraph:
    """Alias of :func:`build_planner_graph`."""
    return build_planner_graph(*args, **kwargs)


class PlannerGraph:
    """Public entry point of the agent planning pipeline.

    ``invoke`` runs the full pipeline synchronously and returns the final
    :class:`PlannerState`. ``run_with_events`` additionally returns a
    :class:`GenerationEvent` per executed node.
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
        predictors: PredictorSet | None = None,
        scheduler: Scheduler | None = None,
        rule_engine: RuleEngine | None = None,
        max_repair_attempts: int = 2,
    ) -> None:
        self.llm = llm
        self.predictors = predictors if predictors is not None else PredictorSet.default()
        self.scheduler = scheduler if scheduler is not None else Scheduler()
        self.rule_engine = rule_engine if rule_engine is not None else RuleEngine()
        self.max_repair_attempts = max_repair_attempts
        self._runner = _build_runner(
            llm=self.llm,
            predictors=self.predictors,
            scheduler=self.scheduler,
            rule_engine=self.rule_engine,
            max_repair_attempts=self.max_repair_attempts,
        )

    def invoke(
        self,
        request: GenerationRequest,
        *,
        user_features: UserFeatureSet,
        goal_id_map: dict[int, int] | None = None,
        profile_prompt: dict | None = None,
    ) -> PlannerState:
        """Run the pipeline and return the final planner state."""
        return self._runner.run(
            self._initial_state(request, user_features, goal_id_map, profile_prompt)
        )

    def run_with_events(
        self,
        request: GenerationRequest,
        *,
        user_features: UserFeatureSet,
        goal_id_map: dict[int, int] | None = None,
        profile_prompt: dict | None = None,
    ) -> tuple[PlannerState, list[GenerationEvent]]:
        """Run the pipeline and return ``(final state, generation events)``."""
        return self._runner.run_with_events(
            self._initial_state(request, user_features, goal_id_map, profile_prompt)
        )

    def _initial_state(
        self,
        request: GenerationRequest,
        user_features: UserFeatureSet,
        goal_id_map: dict[int, int] | None = None,
        profile_prompt: dict | None = None,
    ) -> dict:
        """Seed the state with the request and the injected collaborators."""
        return {
            "user_id": request.user_id,
            "goals": list(request.goals),
            "user_profile": dict(request.user_profile),
            "request": request,
            "user_features": user_features,
            # goal_key (1-based goal index) -> persisted goal id, so drafts can
            # reference real Goal rows without the graph touching the database.
            "goal_id_map": dict(goal_id_map or {}),
            # 环节 2 画像提示词 injected by the Service (None when unprofiled).
            "profile_prompt": dict(profile_prompt) if profile_prompt else None,
            "llm": self.llm,
            "predictors": self.predictors,
            "scheduler": self.scheduler,
            "rule_engine": self.rule_engine,
            "repair_attempts": 0,
            "notes": [],
            "events": [],
        }
