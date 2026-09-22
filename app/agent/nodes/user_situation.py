"""``user_situation_analysis`` node.

The numbers come from the ML predictors (authoritative). The optional LLM step
only contributes the narrative and may not change a single number.
"""

from __future__ import annotations

from app.agent.nodes._shared import get_context
from app.agent.schemas import AgentError, UserSituationResult
from app.agent.state import PlannerState, ToolCallRecord
from app.agent.tools.memory_retriever import MemoryQuery, MemoryRetrieverInput
from app.agent.tools.task_duration_predictor import (
    TaskDurationPredictorInput,
    TaskDurationPredictorTool,
)
from app.domain.models.enums import LoadLevel, Priority, TimeOfDay
from app.ml.base import TaskFeatureSet

NODE = "user_situation_analysis"
TOOL = "task_duration_predictor"
PROMPT = "user_situation"


def _task_features(state: PlannerState) -> list[TaskFeatureSet]:
    """One feature set per theoretical item, keyed by the provisional id."""
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
    """Predict the user's execution profile for the current workload."""
    ctx = get_context(runtime)
    ctx.publish("node.started", {"node": NODE})

    user_context = state.get("user_context")
    if user_context is None or user_context.user_features is None:
        # Degraded path: no history -> neutral defaults, clearly flagged.
        return {
            "user_situation": UserSituationResult(
                confidence=0.2,
                narrative="no user history available; using neutral defaults",
            ),
            "predicted_duration": {},
            "predicted_completion_probability": {},
            "stress_estimation": 5.0,
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

    features = _task_features(state)
    payload = TaskDurationPredictorInput(
        task_features=features,
        user=user_context.user_features,
        available_minutes=user_context.preferences.available_minutes_per_day,
    )
    outcome = ctx.tool(TOOL).invoke(payload)
    ctx.publish("tool.completed", {"tool": TOOL, "ok": outcome.ok})
    predictions = outcome.value or TaskDurationPredictorTool(ctx.predictors).run(payload)

    factors = [
        predictions.duration[feature.task_id] / max(feature.estimated_duration_minutes, 1)
        for feature in features
        if feature.task_id in predictions.duration
    ]
    result = UserSituationResult(
        duration_factor=round(sum(factors) / len(factors), 4) if factors else 1.0,
        completion_ability=(
            round(sum(predictions.completion.values()) / len(predictions.completion), 4)
            if predictions.completion
            else user_context.user_features.completion_rate_7d
        ),
        stress_state=predictions.overall_stress,
        fatigue_state=_fatigue_from_stress(predictions.overall_stress),
        recommended_time_slot=(
            next(iter(predictions.time_slot.values()))
            if predictions.time_slot
            else TimeOfDay.MORNING
        ),
        predicted_duration=dict(predictions.duration),
        predicted_completion_probability=dict(predictions.completion),
        should_reduce_load=predictions.should_reduce_load,
        confidence=predictions.confidence,
    )

    # Optional narrative from the LLM; numbers above are never overwritten.
    narrative, llm_error = _narrative(state, ctx, result)
    if narrative:
        result = result.model_copy(update={"narrative": narrative})

    updates: dict = {
        "user_situation": result,
        "predicted_duration": dict(result.predicted_duration),
        "predicted_completion_probability": dict(result.predicted_completion_probability),
        "stress_estimation": result.stress_state,
        "prediction_source": predictions.source,
        "tool_results": [
            ToolCallRecord(
                tool=TOOL,
                ok=outcome.ok,
                duration_ms=outcome.duration_ms,
                summary=f"source={predictions.source}",
                error=outcome.error,
            )
        ],
        "notes": [
            f"user_situation_analysis: factor={result.duration_factor}, "
            f"completion={result.completion_ability}, stress={result.stress_state}, "
            f"reduce_load={result.should_reduce_load}"
        ],
    }
    if llm_error is not None:
        updates["errors"] = [llm_error]
    ctx.publish("node.completed", {"node": NODE, "summary": updates["notes"][0]})
    return updates


def _fatigue_from_stress(stress: float) -> LoadLevel:
    if stress < 3:
        return LoadLevel.LOW
    if stress < 6:
        return LoadLevel.MODERATE
    if stress < 8:
        return LoadLevel.HIGH
    return LoadLevel.OVERLOADED


def _narrative(
    state: PlannerState, ctx, result: UserSituationResult
) -> tuple[str, AgentError | None]:
    """Optional LLM narrative. Never allowed to alter the numbers."""
    if ctx.llm is None or not getattr(ctx.llm, "enabled", False):
        return "", None

    user_context = state.get("user_context")
    digest = ctx.tool("memory_retriever").run(
        MemoryRetrieverInput(context=user_context, query=MemoryQuery(limit=10))
    )
    outcome = ctx.llm.complete_model(
        prompt_name=PROMPT,
        schema=UserSituationResult,
        variables={
            "user_context": digest.as_prompt_block(),
            "ml_prediction": result.model_dump(mode="json"),
            "progress": (
                state.get("progress").model_dump(mode="json") if state.get("progress") else {}
            ),
        },
        fallback=result,
    )
    if not outcome.used_llm:
        return "", AgentError(
            node=NODE,
            kind="llm_unavailable",
            message=outcome.error or "narrative step fell back to deterministic output",
            recovered=True,
        )
    return outcome.value.narrative or result.narrative, None


__all__ = ["NODE", "PROMPT", "TOOL", "user_situation_analysis_node"]
