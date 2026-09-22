"""Semantic memory: stable facts, preferences and ability signals.

Pure function over domain rows - the database read happens in the application
layer's Context Builder, per the architecture rule "agents never touch the DB".
"""

from __future__ import annotations

from app.agent.context import MemoryItem, MemoryKind
from app.domain.models import User, UserModel


def build_semantic_memory(
    user: User | None, user_model: UserModel | None, *, mbti: str | None = None
) -> list[MemoryItem]:
    """Derive long-lived facts about the user from their profile and model."""
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

    # MBTI is a soft profile input only - never a diagnosis.
    if mbti:
        items.append(
            MemoryItem(
                kind=MemoryKind.SEMANTIC,
                key="mbti",
                value={"value": mbti.upper()},
                summary=f"MBTI self-report {mbti.upper()} (soft signal, not a diagnosis)",
                confidence=0.4,
                source="users.profile.mbti",
            )
        )

    if user_model is not None:
        items.append(
            MemoryItem(
                kind=MemoryKind.SEMANTIC,
                key="duration_factors",
                value={"factors": dict(user_model.duration_factors)},
                summary=f"duration multipliers: {user_model.duration_factors}",
                confidence=min(0.4 + user_model.sample_size / 50, 0.9),
                source="user_models.duration_factors",
            )
        )
        items.append(
            MemoryItem(
                kind=MemoryKind.SEMANTIC,
                key="preferred_time_slots",
                value={"slots": dict(user_model.preferred_time_slots)},
                summary=f"preferred time slots: {user_model.preferred_time_slots}",
                confidence=min(0.4 + user_model.sample_size / 50, 0.9),
                source="user_models.preferred_time_slots",
            )
        )
    return items


__all__ = ["build_semantic_memory"]
