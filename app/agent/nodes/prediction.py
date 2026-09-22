"""``ml_prediction`` node - ask the adjustment predictor what to do.

The node owns no model: it assembles an :class:`AdjustmentRequest` and calls the
injected ``PredictorSet.adjustment``. If the predictor is unavailable the
request fails soft and the router falls back to the deterministic policy.
"""

from __future__ import annotations

from app.agent.nodes._shared import current_drafts, get_context
from app.agent.schemas import AgentError
from app.agent.state import PlannerState, ToolCallRecord
from app.ml.base import (
    AdjustmentPrediction,
    AdjustmentRequest,
    AdjustmentRoute,
    AdjustmentSeverity,
    FeedbackSignal,
    TaskFeatureSet,
)

NODE = "ml_prediction"


def _task_features(state: PlannerState) -> list[TaskFeatureSet]:
    """Features for the adjustment predictor.

    In the feedback graph there is no ``plan_draft`` yet (drafts are only built
    during a replan), so fall back to the *current plan's* tasks. Without this
    fallback every ``AdjustmentRequest`` carried an empty feature list.
    """
    drafts = current_drafts(state)
    features: list[TaskFeatureSet] = []
    for draft in drafts:
        features.append(
            TaskFeatureSet(
                task_id=draft.order_index + 1,  # PROVISIONAL TASK ID CONTRACT
                title=draft.title,
                subject=draft.subject,
                estimated_duration_minutes=max(draft.estimated_duration, 1),
                cognitive_load=draft.cognitive_load,
                priority=draft.priority,
                deadline=draft.deadline,
            )
        )
    if features:
        return features

    plan = state.get("current_plan")
    if plan is None:
        return []
    for task in plan.pending_tasks():
        features.append(
            TaskFeatureSet(
                task_id=task.task_id,  # real persisted id in this graph
                title=task.title,
                subject=task.subject,
                estimated_duration_minutes=max(
                    task.predicted_duration or task.estimated_duration, 1
                ),
                cognitive_load=task.cognitive_load,
                priority=task.priority,
            )
        )
    return features


def _recent_signals(state: PlannerState) -> list[FeedbackSignal]:
    context = state.get("user_context")
    if context is None:
        return []
    return [
        FeedbackSignal(
            date=signal.date,
            completion_rate=signal.completion_rate,
            stress_level=signal.stress_level,
            energy_level=signal.energy_level,
            delay_reason=signal.delay_reason,
        )
        for signal in context.recent_feedback
    ]


def ml_prediction_node(state: PlannerState, runtime: object) -> dict:
    """Produce the adjustment prediction consumed by the router."""
    ctx = get_context(runtime)
    ctx.publish("ml.started", {"node": NODE})

    context = state.get("user_context")
    if context is None or context.user_features is None:
        prediction = AdjustmentPrediction(
            route=AdjustmentRoute.FULL_REPLAN,
            severity=AdjustmentSeverity.MEDIUM,
            confidence=0.2,
            reasons=["no user features available; defaulting to a rebuild"],
            source="fallback:no_features",
        )
        ctx.publish("ml.completed", {"route": prediction.route.value})
        return {
            "ml_prediction": prediction,
            "errors": [
                AgentError(
                    node=NODE,
                    kind="no_user_features",
                    message="planning context has no user features",
                    recovered=True,
                )
            ],
            "notes": [f"ml_prediction: {prediction.route.value} (degraded)"],
        }

    preferences = context.preferences
    request = AdjustmentRequest(
        user=context.user_features,
        progress=context.progress,
        recent_feedback=_recent_signals(state),
        task_features=_task_features(state),
        current_daily_load_minutes=preferences.daily_limit_minutes,
        available_minutes_per_day=preferences.available_minutes_per_day,
        user_note=state["request"].user_note,
    )

    try:
        prediction = ctx.predictors.adjustment.predict_adjustment(request)
    except Exception as exc:  # noqa: BLE001 - ML must never break the loop
        prediction = AdjustmentPrediction(
            route=AdjustmentRoute.NO_CHANGE,
            severity=AdjustmentSeverity.NONE,
            confidence=0.0,
            reasons=[f"predictor failed: {type(exc).__name__}"],
            source="fallback:predictor_error",
        )

    ctx.publish("ml.completed", {"route": prediction.route.value, "source": prediction.source})
    return {
        "ml_prediction": prediction,
        "tool_results": [
            ToolCallRecord(
                tool="adjustment_predictor",
                ok=prediction.source != "fallback:predictor_error",
                summary=f"route={prediction.route.value}, source={prediction.source}",
                used_llm=False,
            )
        ],
        "notes": [
            f"ml_prediction: {prediction.route.value} "
            f"(severity={prediction.severity.value}, source={prediction.source})"
        ],
    }


__all__ = ["NODE", "ml_prediction_node"]
