"""Format checks for LLM-produced task drafts (pure, stdlib only).

This module is the *format gate* for task decomposition. It answers one
question only: can these drafts be passed on to the scheduler and persisted
without breaking the task model? It deliberately does not judge quality
("is this task too big?", "does the plan cover the goal?") - those are
advisory and must never hard-reject a draft.

The tasks argument is duck-typed: any objects exposing the attributes below
(or mappings with the same keys) work, so the domain layer never imports the
agent schemas.

Checks and issue codes
----------------------
title_empty
    The title is missing or blank.
invalid_duration
    estimated_duration is not a positive number.
invalid_order_index
    order_index is missing, not an integer, or negative.
duplicate_order_index
    Two or more tasks share the same order_index.
invalid_goal_id
    goal_id is present but not a positive 1-based goal index (or is out of
    range when goal_count is supplied).
inconsistent_goal
    Tasks of one series_id disagree about their goal_id.
target_unit_mismatch
    Only one of target_amount / target_unit is set.
invalid_dependency
    depends_on is not a list of integer order indexes.
unknown_dependency
    depends_on references an order index that does not exist in the draft.
self_dependency
    A task depends on its own order index.
dependency_cycle
    The dependency graph contains a cycle.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

__all__ = ["DraftIssue", "validate_draft_tasks"]


@dataclass(frozen=True, slots=True)
class DraftIssue:
    """One format problem found in a draft task.

    task_index is the 0-based position in the validated task list (not the
    task's order_index); -1 is reserved for plan-level issues.
    """

    code: str
    message: str
    task_index: int


def validate_draft_tasks(
    tasks: Sequence[object],
    *,
    goal_count: int | None = None,
) -> list[DraftIssue]:
    """Return every format problem in tasks (empty means the draft is valid).

    goal_count is optional: when the caller knows how many goals the draft was
    generated for, every supplied goal_id must be within 1..goal_count. Without
    it, a supplied goal_id only has to be a positive 1-based index.
    """
    issues: list[DraftIssue] = []
    positions_by_order: dict[int, list[int]] = {}
    order_by_position: dict[int, int] = {}
    goal_by_series: dict[str, Any] = {}

    for position, task in enumerate(tasks):
        title = _read(task, "title")
        if not isinstance(title, str) or not title.strip():
            issues.append(
                DraftIssue(
                    code="title_empty",
                    message=f"task {position} has an empty title",
                    task_index=position,
                )
            )

        duration = _read(task, "estimated_duration")
        if not _is_positive_number(duration):
            issues.append(
                DraftIssue(
                    code="invalid_duration",
                    message=(
                        f"task {position} has estimated_duration={duration!r}; "
                        "it must be a positive number"
                    ),
                    task_index=position,
                )
            )

        order_index = _read(task, "order_index")
        if not _is_non_negative_int(order_index):
            issues.append(
                DraftIssue(
                    code="invalid_order_index",
                    message=(
                        f"task {position} has order_index={order_index!r}; "
                        "it must be a non-negative integer"
                    ),
                    task_index=position,
                )
            )
        else:
            order_by_position[position] = order_index
            positions_by_order.setdefault(order_index, []).append(position)

        goal_id = _read(task, "goal_id")
        if goal_id is not None and not _is_positive_int(goal_id):
            issues.append(
                DraftIssue(
                    code="invalid_goal_id",
                    message=(
                        f"task {position} has goal_id={goal_id!r}; "
                        "it must be a positive 1-based goal index"
                    ),
                    task_index=position,
                )
            )
        elif goal_id is not None and goal_count is not None and goal_id > goal_count:
            issues.append(
                DraftIssue(
                    code="invalid_goal_id",
                    message=(
                        f"task {position} has goal_id={goal_id}; "
                        f"only goals 1..{goal_count} were supplied"
                    ),
                    task_index=position,
                )
            )

        series_id = _read(task, "series_id")
        if isinstance(series_id, str) and series_id.strip():
            key = series_id.strip()
            if key in goal_by_series and goal_by_series[key] != goal_id:
                issues.append(
                    DraftIssue(
                        code="inconsistent_goal",
                        message=(
                            f"task {position} belongs to series '{key}' but has "
                            f"goal_id={goal_id!r}, while the series uses "
                            f"{goal_by_series[key]!r}"
                        ),
                        task_index=position,
                    )
                )
            else:
                goal_by_series.setdefault(key, goal_id)

        amount = _read(task, "target_amount")
        unit = _read(task, "target_unit")
        unit_present = unit is not None and (
            not isinstance(unit, str) or bool(unit.strip())
        )
        if (amount is not None) != unit_present:
            issues.append(
                DraftIssue(
                    code="target_unit_mismatch",
                    message=(
                        f"task {position} must set target_amount and target_unit "
                        f"together (amount={amount!r}, unit={unit!r})"
                    ),
                    task_index=position,
                )
            )

    for order_index, positions in positions_by_order.items():
        if len(positions) < 2:
            continue
        for position in positions:
            issues.append(
                DraftIssue(
                    code="duplicate_order_index",
                    message=(
                        f"order_index {order_index} is used by "
                        f"{len(positions)} tasks"
                    ),
                    task_index=position,
                )
            )

    issues.extend(
        _dependency_issues(
            tasks,
            positions_by_order=positions_by_order,
            order_by_position=order_by_position,
        )
    )
    return issues


def _dependency_issues(
    tasks: Sequence[object],
    *,
    positions_by_order: Mapping[int, list[int]],
    order_by_position: Mapping[int, int],
) -> list[DraftIssue]:
    """Validate depends_on references and reject self-dependencies/cycles."""
    issues: list[DraftIssue] = []
    graph: dict[int, list[int]] = {position: [] for position in range(len(tasks))}
    # With duplicate order indexes the first task wins for reference resolution;
    # the duplicate itself is reported separately.
    first_position_by_order = {
        order_index: positions[0] for order_index, positions in positions_by_order.items()
    }

    for position, task in enumerate(tasks):
        depends_on = _read(task, "depends_on")
        if depends_on is None:
            continue
        if isinstance(depends_on, (str, bytes)) or not isinstance(depends_on, Iterable):
            issues.append(
                DraftIssue(
                    code="invalid_dependency",
                    message=(
                        f"task {position} has depends_on={depends_on!r}; "
                        "it must be a list of integer order indexes"
                    ),
                    task_index=position,
                )
            )
            continue

        own_order = order_by_position.get(position)
        for dependency in depends_on:
            if not _is_non_negative_int(dependency):
                issues.append(
                    DraftIssue(
                        code="invalid_dependency",
                        message=(
                            f"task {position} has depends_on entry {dependency!r}; "
                            "order indexes must be non-negative integers"
                        ),
                        task_index=position,
                    )
                )
                continue
            target = first_position_by_order.get(dependency)
            if target is None:
                issues.append(
                    DraftIssue(
                        code="unknown_dependency",
                        message=(
                            f"task {position} depends on order_index {dependency}, "
                            "which does not exist in this draft"
                        ),
                        task_index=position,
                    )
                )
                continue
            if own_order is not None and dependency == own_order:
                issues.append(
                    DraftIssue(
                        code="self_dependency",
                        message=(
                            f"task {position} depends on itself "
                            f"(order_index {dependency})"
                        ),
                        task_index=position,
                    )
                )
                continue
            if target not in graph[position]:
                graph[position].append(target)

    cycle_nodes = _find_cycle_nodes(graph)
    cycle_orders = sorted(
        {order_by_position[node] for node in cycle_nodes if node in order_by_position}
    )
    for position in sorted(cycle_nodes):
        issues.append(
            DraftIssue(
                code="dependency_cycle",
                message=(
                    f"task {position} is part of a dependency cycle "
                    f"(order_index values: {cycle_orders})"
                ),
                task_index=position,
            )
        )
    return issues


def _find_cycle_nodes(graph: Mapping[int, list[int]]) -> set[int]:
    """Return the nodes that participate in at least one dependency cycle."""
    state: dict[int, int] = {}  # absent = white, 1 = gray, 2 = black
    parent: dict[int, int] = {}
    in_cycle: set[int] = set()

    for start in graph:
        if state.get(start, 0) != 0:
            continue
        state[start] = 1
        stack: list[tuple[int, Any]] = [(start, iter(graph[start]))]
        while stack:
            node, children = stack[-1]
            try:
                child = next(children)
            except StopIteration:
                state[node] = 2
                stack.pop()
                continue

            child_state = state.get(child, 0)
            if child_state == 0:
                parent[child] = node
                state[child] = 1
                stack.append((child, iter(graph.get(child, ()))))
            elif child_state == 1:
                in_cycle.add(child)
                current = node
                while current != child and current in parent:
                    in_cycle.add(current)
                    current = parent[current]
    return in_cycle


def _read(task: object, field: str) -> Any:
    if isinstance(task, Mapping):
        return task.get(field)
    return getattr(task, field, None)


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_non_negative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_positive_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0
