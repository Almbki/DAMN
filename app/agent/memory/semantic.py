"""Semantic memory: stable facts, preferences and ability signals.

Pure function over domain rows - the database read happens in the application
layer's Context Builder, per the architecture rule "agents never touch the DB".
"""

from __future__ import annotations

from app.agent.context import MemoryItem, MemoryKind
from app.domain.models import User
from app.domain.profile import UserStateData


def _confidence(update_count: int, *, base: float = 0.4, span: int = 20) -> float:
    """More observations -> more confidence (capped well below certainty)."""
    return round(min(base + update_count / span, 0.9), 4)


def build_semantic_memory(
    user: User | None,
    state: UserStateData | None = None,
) -> list[MemoryItem]:
    """Derive long-lived facts about the user from their profile and state."""
    items: list[MemoryItem] = []

    if user is not None:
        if user.profile:
            items.append(
                MemoryItem(
                    kind=MemoryKind.SEMANTIC,
                    key="profile",
                    value=dict(user.profile),
                    summary="user profile fields: " + ", ".join(sorted(user.profile)),
                    confidence=0.9,
                    source="users.profile",
                )
            )
        items.append(
            MemoryItem(
                kind=MemoryKind.SEMANTIC,
                key="execution_weight",
                value={"value": float(user.execution_weight)},
                summary=f"self-reported execution weight {user.execution_weight:.2f}",
                confidence=0.6,
                source="users.execution_weight",
            )
        )
        if user.identity:
            items.append(
                MemoryItem(
                    kind=MemoryKind.SEMANTIC,
                    key="identity",
                    value={"value": user.identity},
                    summary=f"self description: {user.identity}",
                    confidence=0.7,
                    source="users.identity",
                )
            )

    if state is not None and state.level2_profile:
        items.append(
            MemoryItem(
                kind=MemoryKind.SEMANTIC,
                key="level2_state",
                value={
                    "fatigue": round(state.state_fatigue, 4),
                    "stress": round(state.state_stress, 4),
                    "self_efficacy": round(state.self_efficacy, 4),
                    "observed_on": (
                        state.level2_profile_date.isoformat()
                        if state.level2_profile_date
                        else None
                    ),
                },
                summary=(
                    f"Level 2 state (fatigue {state.state_fatigue:.2f}, "
                    f"stress {state.state_stress:.2f}, "
                    f"self-efficacy {state.self_efficacy:.2f})"
                ),
                confidence=_confidence(state.update_count),
                source="user_states.level2_profile",
            )
        )
        items.append(
            MemoryItem(
                kind=MemoryKind.SEMANTIC,
                key="preferred_time_slots",
                value={"slots": dict(state.preferred_time_slots)},
                summary=f"preferred time slots: {state.preferred_time_slots}",
                confidence=_confidence(state.update_count),
                source="user_states.preferred_time_slots",
            )
        )
    return items


__all__ = ["build_semantic_memory"]
