"""Goal identity helpers shared by the agent nodes.

Contract
--------
``AnalyzedGoal.goal_id`` and ``GeneratedTaskDraft.goal_id`` are **request-local
1-based indices** (1..N). A persisted ``goals.id`` is stored separately in
``GoalInput.existing_goal_id`` and is only used for stable work-unit keys and
for the final index -> database-id mapping.

The resolver below is defensive: an LLM (or legacy code) may echo a persisted
id instead of the local index. Such a reference is mapped back to its request
position when it matches one of this request's goals. Anything else is invalid
and must fail closed at the caller.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def goal_index_for_ref(ref: int | None, goals: Sequence[Any]) -> int | None:
    """Resolve an LLM/draft goal reference to a request-local 1-based index."""
    if ref is None:
        return None
    count = len(goals)
    if 1 <= ref <= count:
        return ref
    for index, goal in enumerate(goals, start=1):
        if getattr(goal, "existing_goal_id", None) == ref:
            return index
    return None


def goal_id_map_for(goals: Sequence[Any]) -> dict[int, int]:
    """Build ``{request index: persisted goal id}`` for this request."""
    return {
        index: goal.existing_goal_id
        for index, goal in enumerate(goals, start=1)
        if getattr(goal, "existing_goal_id", None) is not None
    }


__all__ = ["goal_id_map_for", "goal_index_for_ref"]
