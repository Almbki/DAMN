"""Deterministic execution chunking fallback."""

from __future__ import annotations

from datetime import date

from app.agent.schemas import GeneratedTaskDraft
from app.agent.tools.execution_chunker import chunk_unscheduled_drafts
from app.domain.models.enums import CognitiveLoad, TaskKind


def _draft(
    minutes: int,
    *,
    load: CognitiveLoad = CognitiveLoad.HIGH,
    occurrence: date | None = None,
) -> GeneratedTaskDraft:
    return GeneratedTaskDraft(
        title="长任务",
        estimated_duration=minutes,
        cognitive_load=load,
        occurrence_date=occurrence,
        task_kind=TaskKind.ONE_OFF if occurrence is None else TaskKind.LONG_TERM,
    )


def test_long_high_task_chunks_into_fewest_blocks_and_preserves_total() -> None:
    chunks = chunk_unscheduled_drafts(
        [_draft(240)], {1}, daily_limit_minutes=120
    )

    assert chunks is not None
    assert [draft.estimated_duration for draft in chunks] == [120, 120]
    assert sum(draft.estimated_duration for draft in chunks) == 240
    assert {draft.parent_key for draft in chunks} == {"chunk-0-0"}
    assert [draft.chunk_index for draft in chunks] == [0, 1]
    assert [draft.order_index for draft in chunks] == [0, 1]


def test_recurring_occurrence_is_never_chunked() -> None:
    chunks = chunk_unscheduled_drafts(
        [_draft(240, occurrence=date(2026, 10, 26))],
        {1},
        daily_limit_minutes=120,
    )

    assert chunks is None


def test_short_task_is_not_chunked() -> None:
    chunks = chunk_unscheduled_drafts(
        [_draft(60, load=CognitiveLoad.LOW)],
        {1},
        daily_limit_minutes=300,
    )

    assert chunks is None


def test_medium_task_chunks_without_over_max() -> None:
    chunks = chunk_unscheduled_drafts(
        [_draft(240, load=CognitiveLoad.MEDIUM)],
        {1},
        daily_limit_minutes=300,
    )

    assert chunks is not None
    assert sum(draft.estimated_duration for draft in chunks) == 240
    assert all(draft.estimated_duration <= 90 for draft in chunks)


def test_already_chunked_draft_is_not_chunked_again() -> None:
    draft = _draft(120).model_copy(
        update={"parent_key": "chunk-0-0", "chunk_index": 1}
    )

    chunks = chunk_unscheduled_drafts([draft], {1}, daily_limit_minutes=60)

    assert chunks is None
