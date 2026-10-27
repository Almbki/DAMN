"""Execution observation helpers shared by the lifecycle and ML seams."""

from __future__ import annotations


def is_observed_execution(execution) -> bool:
    """True once an execution has an observed outcome, not just a start time."""
    return bool(
        execution.completed
        or execution.finished_at is not None
        or (execution.completion_rate or 0.0) > 0.0
        or execution.actual_duration is not None
    )
