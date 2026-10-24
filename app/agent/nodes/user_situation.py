"""``user_situation_analysis`` node.

Numbers come from observed aggregates + the real Level 2 state. No production
model emits a completion probability here: Level 3 is shadow-only in v1, and a
missing model degrades to an explicit estimate, never a fabricated number.
"""

from __future__ import annotations

from app.agent.features import TaskFeatureSet
from app.agent.nodes._shared import get_context
from app.agent.schemas import AgentError, UserSituationNarrative, UserSituationResult
from app.agent.state import PlannerState, ToolCallRecord
from app.agent.tools.memory_retriever import MemoryQuery, MemoryRetrieverInput
from app.agent.tools.task_estimator import TaskEstimatorInput, TaskEstimatorTool
from app.domain.models.enums import LoadLevel, Priority

NODE = "user_situation_analysis"
TOOL = "task_estimator"
PROMPT = "user_situation"
PRODUCTION_SOURCE = "deterministic:workload_estimate"


def _task_features(state: PlannerState) -> list[TaskFeatureSet]:
    theoretical = state.get("theoretical_analysis")
    goals = list(state.get("goals") or [])
    features: list[TaskFeatureSet] = []
    if theoretical is None:
        return features
    for idx, item in enumerate(theoretical.items):
        goal = goals[idx] if idx < len(goals) else None
        features.append(
            TaskFeatureSet(
                task_id=idx + 1,  # PROVISIONAL TASK ID CONTRACT
                title=item.title,
                task_type=goal.task_type if goal else None,
                subject=goal.subject if goal else None,
                estimated_duration_minutes=max(item.total_minutes, 1),
                difficulty=item.difficulty,
                cognitive_load=item.cognitive_load,
                priority=goal.priority if goal else Priority.MEDIUM,
                deadline=goal.deadline if goal else None,
            )
        )
    return features


def user_situation_analysis_node(state: PlannerState, runtime: object) -> dict:
    ctx = get_context(runtime)
    ctx.publish("node.started", {"node": NODE})

    user_context = state.get("user_context")
    model = user_context.user_model if user_context is not None else None
    features = _task_features(state)

    if user_context is None or user_context.user_features is None or not features:
        return {
            "user_situation": UserSituationResult(
                confidence=0.2,
                narrative="no user history available; using neutral defaults",
            ),
            "prediction_source": "fallback:no_features",
            "errors": [
                AgentError(
                    node=NODE,
                    kind="no_user_features",
                    message="planning context has no user features; using defaults",
                    recovered=True,
                )
            ],
            "notes": ["user_situation_analysis: no user features (degraded)"],
        }

    payload = TaskEstimatorInput(
        task_features=features,
        user=user_context.user_features,
        available_minutes=user_context.preferences.available_minutes_per_day,
    )
    outcome = ctx.tool(TOOL).invoke(payload)
    ctx.publish("tool.completed", {"tool": TOOL, "ok": outcome.ok})
    estimates = outcome.value or TaskEstimatorTool().run(payload)

    state_snapshot = model.state if model is not None else None
    stress = (
        round(state_snapshot.stress.value * 10.0, 2)
        if state_snapshot is not None
        else user_context.user_features.avg_stress
    )
    completion_ability = user_context.user_features.completion_rate_7d
    result = UserSituationResult(
        duration_factor=1.0,
        completion_ability=(
            round(completion_ability, 4) if completion_ability is not None else 0.5
        ),
        stress_state=stress if stress is not None else 5.0,
        fatigue_state=_fatigue_level(
            state_snapshot.fatigue.value if state_snapshot else None
        ),
        recommended_time_slot=next(iter(estimates.time_slot.values()), None),
        predicted_duration=dict(estimates.duration),
        # No production model emits this; Level 3 is shadow-only.
        predicted_completion_probability={},
        should_reduce_load=estimates.should_reduce_load,
        confidence=0.5 if state_snapshot is not None else 0.2,
    )

    narrative, llm_error = _narrative(state, ctx, result)
    if narrative:
        result = result.model_copy(update={"narrative": narrative})

    errors: list[AgentError] = []
    if state_snapshot is None and model is not None and model.trait is not None:
        errors.append(
            AgentError(
                node=NODE,
                kind="level2_unavailable",
                message="no Level 2 dynamic state; using observed aggregates only",
                recovered=True,
            )
        )
    if model is not None and model.degraded:
        actionable = [
            reason
            for reason in model.degraded_reasons
            if reason not in {"level1:no_trait_profile", "level2:no_state_profile"}
        ]
        if actionable:
            errors.append(
                AgentError(
                    node=NODE,
                    kind="user_model_degraded",
                    message="; ".join(actionable),
                    recovered=True,
                )
            )
    if llm_error is not None:
        errors.append(llm_error)

    updates: dict = {
        "user_situation": result,
        "prediction_source": PRODUCTION_SOURCE,
        "tool_results": [
            ToolCallRecord(
                tool=TOOL,
                ok=outcome.ok,
                duration_ms=outcome.duration_ms,
                summary=f"source={estimates.source}",
                error=outcome.error,
            )
        ],
        "notes": [
            f"user_situation_analysis: completion_data={completion_ability is not None}, "
            f"stress={result.stress_state}, level2={state_snapshot is not None}, "
            f"level3_mode={model.level3_mode.value if model else 'unavailable'}"
        ],
    }
    if errors:
        updates["errors"] = errors
    ctx.publish("node.completed", {"node": NODE, "summary": updates["notes"][0]})
    return updates


def _fatigue_level(fatigue: float | None) -> LoadLevel:
    """Display bucket for the Level 2 fatigue value (not a model formula)."""
    if fatigue is None:
        return LoadLevel.MODERATE
    if fatigue < 0.35:
        return LoadLevel.LOW
    if fatigue < 0.65:
        return LoadLevel.MODERATE
    if fatigue < 0.85:
        return LoadLevel.HIGH
    return LoadLevel.OVERLOADED


def _narrative(
    state: PlannerState, ctx, result: UserSituationResult
) -> tuple[str, AgentError | None]:
    if ctx.llm is None or not getattr(ctx.llm, "enabled", False):
        return "", None
    user_context = state.get("user_context")
    digest = ctx.tool("memory_retriever").run(
        MemoryRetrieverInput(context=user_context, query=MemoryQuery(limit=10))
    )
    model = user_context.user_model if user_context is not None else None
    outcome = ctx.llm.complete_model(
        prompt_name=PROMPT,
        schema=UserSituationNarrative,
        variables={
            "user_context": digest.as_prompt_block(),
            "user_model": model.model_dump(mode="json") if model else {},
            "situation_estimate": result.model_dump(mode="json"),
            "progress": (
                state.get("progress").model_dump(mode="json")
                if state.get("progress")
                else {}
            ),
        },
        fallback=UserSituationNarrative(narrative=result.narrative),
    )
    if not outcome.used_llm:
        return "", AgentError(
            node=NODE,
            kind="llm_unavailable",
            message=outcome.error or "narrative step fell back to deterministic output",
            recovered=True,
        )
    return outcome.value.narrative or result.narrative, None


__all__ = ["NODE", "PRODUCTION_SOURCE", "PROMPT", "TOOL", "user_situation_analysis_node"]