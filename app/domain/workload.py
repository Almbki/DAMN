"""Deterministic workload semantics.

Three different numbers must not be conflated:

* ``total_minutes``      - the theoretical work needed for a one-off, a project
                           work unit, or one recurring occurrence.
* ``estimated_duration`` - one schedulable execution block.
* ``actual_duration``    - what the user actually spent (TaskExecution).

The LLM may propose a workload, but this module bounds/sanity-checks it before
the scheduler sees it. It never invents semantic subtasks or course chapters.
"""

from __future__ import annotations

from app.domain.models.enums import CognitiveLoad, PlanningMode

# One-off defaults are deliberately conservative: a generic deliverable is not
# a multi-hour block unless the user explicitly says so.
ONE_OFF_DEFAULT_TOTAL = 60
ONE_OFF_MAX_TOTAL = 120
RECURRING_DEFAULT_OCCURRENCE = 30
RECURRING_MAX_OCCURRENCE = 120
PROJECT_UNIT_MAX_TOTAL = 480
MIN_CHUNK_MINUTES = 25
MAX_CHUNKS_PER_TASK = 8

#: A single execution block is kept short enough to be realistically
#: schedulable in one contiguous window. Long work is chunked only after the
#: scheduler cannot place it as one block.
MAX_SINGLE_BLOCK = {
    CognitiveLoad.HIGH: 120,
    CognitiveLoad.MEDIUM: 90,
    CognitiveLoad.LOW: 60,
    CognitiveLoad.RESTORATIVE: 45,
}


def max_chunk_minutes(load: CognitiveLoad) -> int:
    return MAX_SINGLE_BLOCK.get(load, 90)


def normalise_total_minutes(
    *,
    mode: PlanningMode,
    total_minutes: int | None,
    explicit_minutes: int | None = None,
    cognitive_load: CognitiveLoad = CognitiveLoad.MEDIUM,
) -> int:
    """Normalise the *total* workload, never the execution chunk.

    Explicit user minutes are authoritative. Otherwise a one-off is capped at
    a conservative total; a project work unit may be large; a recurring
    occurrence is one occurrence, not the whole lifecycle.
    """
    if explicit_minutes is not None and explicit_minutes > 0:
        return int(explicit_minutes)

    total = int(total_minutes or 0)
    if total <= 0:
        if mode is PlanningMode.ONE_OFF:
            total = ONE_OFF_DEFAULT_TOTAL
        elif mode is PlanningMode.RECURRING:
            total = RECURRING_DEFAULT_OCCURRENCE
        else:
            total = ONE_OFF_DEFAULT_TOTAL

    if mode is PlanningMode.ONE_OFF:
        return min(total, ONE_OFF_MAX_TOTAL)
    if mode is PlanningMode.RECURRING:
        return min(total, RECURRING_MAX_OCCURRENCE)
    return min(total, PROJECT_UNIT_MAX_TOTAL)


def rescale_split(
    total: int, video: int, reading: int, practice: int
) -> tuple[int, int, int]:
    """Scale a theoretical split so it sums to the normalised total."""
    old = max(1, int(video) + int(reading) + int(practice))
    if old == total:
        return int(video), int(reading), int(practice)
    scaled_video = round(int(video) * total / old)
    scaled_reading = round(int(reading) * total / old)
    scaled_practice = max(0, total - scaled_video - scaled_reading)
    return scaled_video, scaled_reading, scaled_practice


def chunk_minutes(
    total: int,
    load: CognitiveLoad,
    *,
    max_block: int | None = None,
) -> list[int]:
    """Return the fewest reasonable chunks whose sum is exactly ``total``.

    ``max_block`` is the scheduler's largest actually available contiguous
    window. An empty list means the task cannot be responsibly chunked (too
    many chunks / no window >= MIN_CHUNK); the caller keeps it PENDING.
    """
    total = int(total)
    if total <= 0:
        return []
    max_chunk = max_chunk_minutes(load)
    if max_block is not None:
        max_chunk = min(max_chunk, int(max_block))
    if max_chunk < MIN_CHUNK_MINUTES:
        return []
    if total <= max_chunk:
        return [total]

    count = (total + max_chunk - 1) // max_chunk
    if count > MAX_CHUNKS_PER_TASK:
        return []
    # Ensure the smallest chunk is not below the minimum effective block.
    if total // count < MIN_CHUNK_MINUTES:
        count = max(1, total // MIN_CHUNK_MINUTES)
    if count > MAX_CHUNKS_PER_TASK:
        return []

    base = total // count
    remainder = total % count
    chunks = [base + (1 if index < remainder else 0) for index in range(count)]
    if any(chunk <= 0 or chunk > max_chunk for chunk in chunks):
        return []
    if any(chunk < MIN_CHUNK_MINUTES for chunk in chunks) and len(chunks) > 1:
        return []
    return chunks


__all__ = [
    "MAX_CHUNKS_PER_TASK",
    "MAX_SINGLE_BLOCK",
    "MIN_CHUNK_MINUTES",
    "ONE_OFF_DEFAULT_TOTAL",
    "ONE_OFF_MAX_TOTAL",
    "PROJECT_UNIT_MAX_TOTAL",
    "RECURRING_DEFAULT_OCCURRENCE",
    "RECURRING_MAX_OCCURRENCE",
    "chunk_minutes",
    "max_chunk_minutes",
    "normalise_total_minutes",
    "rescale_split",
]
