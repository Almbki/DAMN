"""``user_situation_analysis`` node: predict the user's real execution profile.

Bridges the theoretical workload to the actual user through the four ML
predictors (mock statistical set by default). The graph node builds ``Task``
objects (from the draft set when present, else from the theoretical items) and
the agent feeds each task through all four predictors.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from app.agent.nodes.plan_generation import drafts_to_tasks
from app.agent.schemas import UserSituationResult
from app.agent.state import PlannerState
from app.domain.models import Task
from app.domain.models.enums import LoadLevel, TaskStatus, TimeOfDay
from app.ml.base import PredictionRequest, TaskFeatureSet, UserFeatureSet
from app.ml.predictors import PredictorSet

#: Worst-load ordering (used to aggregate per-task load levels).
_LOAD_RANK = {
    LoadLevel.LOW: 0,
    LoadLevel.MODERATE: 1,
    LoadLevel.HIGH: 2,
    LoadLevel.OVERLOADED: 3,
}


class UserSituationAnalysisAgent:
    """Aggregates the four predictors into one :class:`UserSituationResult`.

    For every task a :class:`TaskFeatureSet` is built and fed to the duration,
    completion, stress and time-slot predictors; per-task predictions are
    aggregated (mean for scalar values, worst for fatigue, modal for the
    recommended slot).
    """

    name = "user-situation-analysis-mock-v0"

    def __init__(self, predictors: PredictorSet | None = None) -> None:
        self.predictors = predictors if predictors is not None else PredictorSet.default()

    def run(self, state: PlannerState, tasks: list[Task]) -> UserSituationResult:
        """Predict the user's situation for the given task set."""
        user: UserFeatureSet = state["user_features"]
        request = state["request"]
        subject_by_id, deadline_by_id = self._enrich(state)

        duration_ratios: list[float] = []
        completion_probs: list[float] = []
        stress_values: list[float] = []
        load_levels: list[LoadLevel] = []
        slots: list[TimeOfDay] = []
        confidences: list[float] = []
        predicted_duration: dict[int, int] = {}
        predicted_completion: dict[int, float] = {}
        should_reduce = False

        for task in tasks:
            features = TaskFeatureSet(
                task_id=task.id,
                title=task.title,
                subject=subject_by_id.get(task.id),
                estimated_duration_minutes=task.estimated_duration,
                cognitive_load=task.cognitive_load,
                priority=task.priority,
                deadline=deadline_by_id.get(task.id),
            )
            pred_request = PredictionRequest(
                task=features,
                user=user,
                available_minutes=request.available_minutes_per_day,
            )
            duration = self.predictors.duration.predict(pred_request)
            completion = self.predictors.completion.predict(pred_request)
            stress = self.predictors.stress.predict(pred_request)
            slot = self.predictors.time_slot.predict(pred_request)

            predicted_duration[task.id] = duration.predicted_minutes
            predicted_completion[task.id] = completion.probability
            duration_ratios.append(
                duration.predicted_minutes / max(duration.theoretical_minutes, 1)
            )
            completion_probs.append(completion.probability)
            stress_values.append(stress.predicted_stress)
            load_levels.append(stress.predicted_load_level)
            slots.append(slot.recommended_slot)
            should_reduce = should_reduce or stress.should_reduce_load
            confidences.extend(
                [duration.confidence, completion.confidence, stress.confidence, slot.confidence]
            )

        return UserSituationResult(
            duration_factor=round(self._mean(duration_ratios), 4)
            if duration_ratios
            else user.duration_factor,
            completion_ability=round(self._mean(completion_probs), 4)
            if completion_probs
            else user.completion_rate_7d,
            stress_state=round(self._mean(stress_values), 4)
            if stress_values
            else user.avg_stress,
            fatigue_state=self._worst_load(load_levels),
            recommended_time_slot=self._modal_slot(slots),
            predicted_duration=predicted_duration,
            predicted_completion_probability=predicted_completion,
            should_reduce_load=should_reduce,
            confidence=round(self._mean(confidences), 4) if confidences else 0.5,
        )

    @staticmethod
    def _enrich(state: PlannerState) -> tuple[dict[int, str], dict[int, datetime]]:
        """Map provisional task ids to subject / deadline.

        Prefers the plan draft (carries subject/deadline per task); falls back
        to the goals by index (``task_id = idx + 1``).
        """
        subject_by_id: dict[int, str] = {}
        deadline_by_id: dict[int, datetime] = {}

        plan_draft = state.get("plan_draft")
        if plan_draft is not None:
            for draft in plan_draft.tasks:
                task_id = draft.order_index + 1  # PROVISIONAL TASK ID CONTRACT
                if draft.subject:
                    subject_by_id[task_id] = draft.subject
                if draft.deadline is not None:
                    deadline_by_id[task_id] = draft.deadline
            return subject_by_id, deadline_by_id

        for idx, goal in enumerate(state.get("goals") or []):
            task_id = idx + 1  # PROVISIONAL TASK ID CONTRACT
            if goal.subject:
                subject_by_id[task_id] = goal.subject
            if goal.deadline is not None:
                deadline_by_id[task_id] = goal.deadline
        return subject_by_id, deadline_by_id

    @staticmethod
    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _worst_load(levels: list[LoadLevel]) -> LoadLevel:
        if not levels:
            return LoadLevel.MODERATE
        return max(levels, key=lambda level: _LOAD_RANK[level])

    @staticmethod
    def _modal_slot(slots: list[TimeOfDay]) -> TimeOfDay:
        """Most frequent slot; ties broken by TimeOfDay declaration order."""
        if not slots:
            return TimeOfDay.MORNING
        counts = Counter(slots)
        order = {slot: index for index, slot in enumerate(TimeOfDay)}
        return max(counts, key=lambda slot: (counts[slot], -order[slot]))


def user_situation_analysis_node(state: PlannerState) -> dict:
    """Node function: predict the user's situation from the current workload.

    Builds the task set from ``state["plan_draft"]`` when present, otherwise
    from ``state["theoretical_workload"].items``.
    """
    agent = state.get("situation_agent")
    if agent is None:
        agent = UserSituationAnalysisAgent(predictors=state.get("predictors"))

    if state.get("plan_draft") is not None:
        tasks = drafts_to_tasks(state["plan_draft"].tasks)
    else:
        items = state["theoretical_workload"].items
        tasks = [
            Task(
                id=idx + 1,  # PROVISIONAL TASK ID CONTRACT
                plan_id=0,
                title=item.title,
                estimated_duration=item.total_minutes,
                cognitive_load=item.cognitive_load,
                status=TaskStatus.SCHEDULED,
                order_index=idx,
            )
            for idx, item in enumerate(items)
        ]

    result = agent.run(state, tasks)
    return {
        "user_situation": result,
        "predicted_duration": dict(result.predicted_duration),
        "predicted_completion_probability": dict(result.predicted_completion_probability),
        "stress_estimation": result.stress_state,
        "notes": [
            f"user_situation_analysis: {len(tasks)} task(s) predicted, "
            f"completion={result.completion_ability:.2f}, stress={result.stress_state:.1f}."
        ],
    }
