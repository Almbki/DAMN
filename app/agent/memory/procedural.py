"""Procedural memory: "how this user should be scheduled" rules of thumb.

Derived statistically from history. These are *hints* handed to the LLM and the
scheduler context - they are never hard constraints (the Rule Engine owns those).
"""

from __future__ import annotations

from statistics import mean

from app.agent.context import MemoryItem, MemoryKind
from app.domain.models import Feedback, TaskExecution
from app.domain.profile import UserStateData

#: Minimum samples before a pattern is reported at all.
_MIN_SAMPLES = 3


def derive_procedural_memory(
    state: UserStateData | None,
    executions: list[TaskExecution],
    feedbacks: list[Feedback],
) -> list[MemoryItem]:
    """Extract scheduling heuristics from executions and daily feedback."""
    items: list[MemoryItem] = []

    # 1. Time-of-day performance pattern.
    by_slot: dict[str, list[float]] = {}
    for execution in executions:
        slot = getattr(execution.time_of_day, "value", execution.time_of_day)
        if not slot:
            continue
        by_slot.setdefault(str(slot), []).append(execution.completion_rate)

    scored = {
        slot: (mean(rates), len(rates))
        for slot, rates in by_slot.items()
        if len(rates) >= _MIN_SAMPLES
    }
    if scored:
        best = max(scored, key=lambda slot: scored[slot][0])
        worst = min(scored, key=lambda slot: scored[slot][0])
        items.append(
            MemoryItem(
                kind=MemoryKind.PROCEDURAL,
                key="best_time_of_day",
                value={"slot": best, "completion_rate": round(scored[best][0], 3)},
                summary=f"{best} has the highest completion rate for this user",
                confidence=min(0.4 + scored[best][1] / 20, 0.85),
                source="task_executions.time_of_day",
            )
        )
        if worst != best and scored[worst][0] < 0.5:
            items.append(
                MemoryItem(
                    kind=MemoryKind.PROCEDURAL,
                    key="avoid_time_of_day",
                    value={"slot": worst, "completion_rate": round(scored[worst][0], 3)},
                    summary=f"avoid scheduling demanding work in the {worst}",
                    confidence=min(0.4 + scored[worst][1] / 20, 0.85),
                    source="task_executions.time_of_day",
                )
            )

    # 2. Overrun pattern (actual vs planned).
    ratios = [
        (execution.actual_duration or 0) / execution.planned_duration
        for execution in executions
        if execution.planned_duration and execution.actual_duration
    ]
    if len(ratios) >= _MIN_SAMPLES:
        factor = round(mean(ratios), 3)
        direction = "overruns" if factor > 1.15 else "finishes early" if factor < 0.85 else "tracks"
        items.append(
            MemoryItem(
                kind=MemoryKind.PROCEDURAL,
                key="duration_overrun",
                value={"factor": factor, "samples": len(ratios)},
                summary=f"this user {direction} planned durations (factor {factor})",
                confidence=min(0.4 + len(ratios) / 25, 0.9),
                source="task_executions",
            )
        )

    # 3. Overload / stress signal from daily feedback.
    if feedbacks:
        stress = [f.stress_level for f in feedbacks if f.stress_level is not None]
        energy = [f.energy_level for f in feedbacks if f.energy_level is not None]
        if stress and mean(stress) >= 7:
            items.append(
                MemoryItem(
                    kind=MemoryKind.PROCEDURAL,
                    key="high_stress",
                    value={"avg_stress": round(mean(stress), 2)},
                    summary="average stress is high; keep the daily load conservative",
                    confidence=0.7,
                    source="feedbacks.stress_level",
                )
            )
        if energy and mean(energy) <= 3.5:
            items.append(
                MemoryItem(
                    kind=MemoryKind.PROCEDURAL,
                    key="low_energy",
                    value={"avg_energy": round(mean(energy), 2)},
                    summary="average energy is low; prefer shorter, lighter sessions",
                    confidence=0.7,
                    source="feedbacks.energy_level",
                )
            )

    # 4. Reuse the portrait's own completion prior when it has observations.
    if state is not None and state.update_count > 0:
        items.append(
            MemoryItem(
                kind=MemoryKind.PROCEDURAL,
                key="completion_prior",
                value={
                    "completion_prob": round(state.completion_prob, 4),
                    "update_count": state.update_count,
                },
                summary=(
                    f"completion prior {state.completion_prob:.2f} "
                    f"(from {state.update_count} observed update(s))"
                ),
                confidence=min(0.4 + state.update_count / 20, 0.9),
                source="user_states.completion_prob",
            )
        )
    return items


__all__ = ["derive_procedural_memory"]
