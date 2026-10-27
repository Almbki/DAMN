"""Deterministic execution chunking for long work units.

Two complementary paths:

* ``chunk_long_drafts`` runs *before* scheduling and proactively splits a long
  one-off/project block into realistic execution blocks. This prevents a
  300-minute work unit from being parked as one five-hour block on the only day
  that happens to have enough contiguous capacity.
* ``chunk_unscheduled_drafts`` remains the bounded fallback for a task that
  still cannot be placed (using the scheduler's real free window).

Recurring occurrences and already-chunked drafts are never re-chunked. Chunks
share a stable ``parent_key``, carry ``chunk_index``, and their durations sum
exactly to the original total.
"""

from __future__ import annotations

from app.agent.schemas import GeneratedTaskDraft
from app.domain.workload import (
    MIN_CHUNK_MINUTES,
    chunk_minutes,
    max_chunk_minutes,
)


def _expanded_chunks(
    draft: GeneratedTaskDraft,
    *,
    max_block: int | None = None,
    max_per_goal_minutes: int | None = None,
) -> list[GeneratedTaskDraft] | None:
    """Return chunks for one draft, or ``None`` when it must stay whole."""
    if draft.occurrence_date is not None or draft.parent_key is not None:
        return None

    max_chunk = max_chunk_minutes(draft.cognitive_load)
    if max_block is not None:
        max_chunk = min(max_chunk, int(max_block))
    if draft.goal_id is not None and max_per_goal_minutes is not None:
        # A single execution block can never exceed its goal's daily budget.
        max_chunk = min(max_chunk, int(max_per_goal_minutes))
    if max_chunk < MIN_CHUNK_MINUTES:
        return None
    if draft.estimated_duration <= max_chunk:
        return None

    sizes = chunk_minutes(
        draft.estimated_duration,
        draft.cognitive_load,
        max_block=max_block,
    )
    if len(sizes) <= 1:
        return None

    parent_key = f"chunk-{draft.goal_id or 0}-{draft.order_index}"
    return [
        draft.model_copy(
            update={
                "estimated_duration": size,
                "predicted_duration": (
                    size if draft.predicted_duration is not None else None
                ),
                "parent_key": parent_key,
                "chunk_index": index,
                "is_flexible": draft.is_flexible,
            }
        )
        for index, size in enumerate(sizes)
    ]


def _renumber(drafts: list[GeneratedTaskDraft]) -> list[GeneratedTaskDraft]:
    return [
        draft.model_copy(update={"order_index": index})
        for index, draft in enumerate(drafts)
    ]


def chunk_long_drafts(
    drafts: list[GeneratedTaskDraft],
    *,
    daily_limit_minutes: int,
    available_minutes_per_day: int | None = None,
    max_per_goal_minutes: int | None = None,
) -> list[GeneratedTaskDraft] | None:
    """Proactively split long drafts into realistic blocks before scheduling.

    The block cap is the smaller of the daily limit and the usable daily window;
    the load-specific ``MAX_SINGLE_BLOCK`` still applies inside
    :func:`chunk_minutes`. A 300-minute medium project unit therefore becomes
    four 75-minute chunks instead of one five-hour block.
    """
    block_cap = max(1, int(daily_limit_minutes))
    if available_minutes_per_day is not None:
        block_cap = min(block_cap, max(1, int(available_minutes_per_day)))

    expanded: list[GeneratedTaskDraft] = []
    changed = False
    for draft in drafts:
        chunks = _expanded_chunks(
            draft,
            max_block=block_cap,
            max_per_goal_minutes=max_per_goal_minutes,
        )
        if chunks is None:
            expanded.append(draft)
        else:
            expanded.extend(chunks)
            changed = True

    if not changed:
        return None
    return _renumber(expanded)


def chunk_unscheduled_drafts(
    drafts: list[GeneratedTaskDraft],
    unscheduled_ids: set[int],
    *,
    daily_limit_minutes: int,
    max_block_by_id: dict[int, int] | None = None,
) -> list[GeneratedTaskDraft] | None:
    """Return a renumbered draft list with unscheduled long tasks chunked.

    ``None`` means nothing changed. Chunks share a stable ``parent_key`` and
    carry ``chunk_index``; their durations sum exactly to the original total.
    """
    changed = False
    expanded: list[GeneratedTaskDraft] = []

    for draft in drafts:
        provisional_id = draft.order_index + 1
        if provisional_id not in unscheduled_ids:
            expanded.append(draft)
            continue
        max_block = (
            max_block_by_id.get(provisional_id)
            if max_block_by_id is not None
            else None
        )
        chunks = _expanded_chunks(draft, max_block=max_block)
        if chunks is None:
            expanded.append(draft)
        else:
            expanded.extend(chunks)
            changed = True

    if not changed:
        return None
    return _renumber(expanded)


__all__ = ["chunk_long_drafts", "chunk_unscheduled_drafts"]
