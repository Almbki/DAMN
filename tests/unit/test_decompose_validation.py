"""Format checks for decomposed task drafts (Phase 3).

The validator is pure domain logic; the small node-wiring tests below use a stub
tool, so nothing here touches the database or the HTTP API. The validator must
catch every structural problem the plan pipeline cannot persist while leaving
valid drafts - including planned dependency chains - untouched.
"""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

from app.agent.nodes.plan_generation import plan_generation_node
from app.agent.schemas import GeneratedTaskDraft, PlanGenerationResult
from app.agent.state import (
    AgentConfig,
    PlannerContext,
    PlannerRequest,
    PreferenceInput,
)
from app.agent.tools.base import BaseTool, ToolRegistry
from app.agent.tools.plan_drafter import PlanDrafterInput
from app.domain.decomposition.validation import DraftIssue, validate_draft_tasks
from app.domain.rules.base import RuleEngine
from app.domain.scheduling.scheduler import Scheduler


def _task(**overrides):
    base = {
        "title": "Study limits",
        "estimated_duration": 30,
        "order_index": 0,
        "goal_id": None,
        "series_id": None,
        "target_amount": None,
        "target_unit": None,
        "depends_on": [],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _codes(issues: list[DraftIssue]) -> set[str]:
    return {issue.code for issue in issues}


def test_valid_draft_with_dependency_chain_has_no_issues() -> None:
    tasks = [
        _task(order_index=0, goal_id=1),
        _task(order_index=1, goal_id=1, depends_on=[0]),
        _task(order_index=2, goal_id=2, depends_on=[0, 1]),
    ]

    assert validate_draft_tasks(tasks) == []


def test_generated_task_draft_defaults_depends_on_to_empty_list() -> None:
    assert GeneratedTaskDraft(title="Read chapter").depends_on == []
    assert GeneratedTaskDraft(title="Read chapter", depends_on=[0]).depends_on == [0]


def test_validator_accepts_the_real_pydantic_schema() -> None:
    tasks = [
        GeneratedTaskDraft(title="Read chapter", order_index=0),
        GeneratedTaskDraft(title="Do exercises", order_index=1, depends_on=[0]),
    ]

    assert validate_draft_tasks(tasks) == []


def test_empty_or_whitespace_title_is_rejected() -> None:
    issues = validate_draft_tasks(
        [_task(title=""), _task(title="   ", order_index=1)]
    )

    assert _codes(issues) == {"title_empty"}
    assert {issue.task_index for issue in issues} == {0, 1}


def test_non_positive_duration_is_rejected() -> None:
    for duration in (0, -5, "30", None):
        issues = validate_draft_tasks([_task(estimated_duration=duration)])
        assert "invalid_duration" in _codes(issues), duration


def test_order_index_must_be_non_negative_integer() -> None:
    for order_index in (-1, None, "0"):
        issues = validate_draft_tasks([_task(order_index=order_index)])
        assert "invalid_order_index" in _codes(issues), order_index


def test_duplicate_order_index_is_reported_on_every_duplicate() -> None:
    issues = validate_draft_tasks(
        [_task(order_index=2), _task(order_index=2)]
    )

    duplicates = [issue for issue in issues if issue.code == "duplicate_order_index"]
    assert {issue.task_index for issue in duplicates} == {0, 1}
    assert "2" in duplicates[0].message


def test_goal_id_is_a_positive_1_based_index_when_given() -> None:
    assert "invalid_goal_id" in _codes(validate_draft_tasks([_task(goal_id=0)]))
    assert "invalid_goal_id" in _codes(validate_draft_tasks([_task(goal_id=-1)]))

    issues = validate_draft_tasks([_task(goal_id=3)], goal_count=2)
    assert "invalid_goal_id" in _codes(issues)
    assert validate_draft_tasks([_task(goal_id=2)], goal_count=2) == []


def test_tasks_of_one_series_must_agree_on_goal_id() -> None:
    issues = validate_draft_tasks(
        [
            _task(order_index=0, series_id="goal-1-daily", goal_id=1),
            _task(order_index=1, series_id="goal-1-daily", goal_id=2),
        ]
    )

    assert _codes(issues) == {"inconsistent_goal"}
    assert issues[0].task_index == 1


def test_target_amount_and_unit_must_be_set_together() -> None:
    amount_only = validate_draft_tasks([_task(target_amount=30)])
    assert "target_unit_mismatch" in _codes(amount_only)

    unit_only = validate_draft_tasks(
        [_task(target_amount=None, target_unit="pages")]
    )
    assert "target_unit_mismatch" in _codes(unit_only)

    assert (
        validate_draft_tasks([_task(target_amount=30, target_unit="pages")]) == []
    )
    assert validate_draft_tasks([_task(target_amount=0, target_unit="pages")]) == []


def test_dependency_must_reference_an_existing_order_index() -> None:
    issues = validate_draft_tasks([_task(order_index=0, depends_on=[5])])

    assert _codes(issues) == {"unknown_dependency"}
    assert issues[0].task_index == 0


def test_self_dependency_is_rejected() -> None:
    issues = validate_draft_tasks([_task(order_index=3, depends_on=[3])])

    assert _codes(issues) == {"self_dependency"}
    assert issues[0].task_index == 0


def test_two_task_dependency_cycle_is_rejected() -> None:
    issues = validate_draft_tasks(
        [
            _task(order_index=0, depends_on=[1]),
            _task(order_index=1, depends_on=[0]),
        ]
    )

    cycles = [issue for issue in issues if issue.code == "dependency_cycle"]
    assert {issue.task_index for issue in cycles} == {0, 1}


def test_three_task_dependency_cycle_is_rejected() -> None:
    issues = validate_draft_tasks(
        [
            _task(order_index=0, depends_on=[2]),
            _task(order_index=1, depends_on=[0]),
            _task(order_index=2, depends_on=[1]),
        ]
    )

    cycles = [issue for issue in issues if issue.code == "dependency_cycle"]
    assert {issue.task_index for issue in cycles} == {0, 1, 2}


def test_forward_dependency_without_a_cycle_is_valid() -> None:
    tasks = [
        _task(order_index=0, depends_on=[1]),
        _task(order_index=1),
    ]

    assert validate_draft_tasks(tasks) == []


def test_malformed_dependency_field_is_rejected() -> None:
    assert "invalid_dependency" in _codes(
        validate_draft_tasks([_task(order_index=0, depends_on="0")])
    )
    assert "invalid_dependency" in _codes(
        validate_draft_tasks([_task(order_index=0, depends_on=[-1])])
    )


def test_mapping_tasks_are_supported() -> None:
    issues = validate_draft_tasks(
        [{"title": "", "estimated_duration": 10, "order_index": 0}]
    )

    assert _codes(issues) == {"title_empty"}


def test_issue_contains_code_message_and_task_index() -> None:
    issue = validate_draft_tasks([_task(title="")])[0]

    assert isinstance(issue, DraftIssue)
    assert issue.code == "title_empty"
    assert issue.message
    assert issue.task_index == 0


# ---------------------------------------------------------------------------
# Node wiring: bounded format retry
# ---------------------------------------------------------------------------
class _StubDrafter(BaseTool):
    """Returns pre-canned drafts and counts how often it was asked to retry."""

    name = "plan_drafter"

    def __init__(self, results: list[PlanGenerationResult]) -> None:
        self._results = results
        self.calls = 0

    def run(self, payload: PlanDrafterInput) -> PlanGenerationResult:
        index = min(self.calls, len(self._results) - 1)
        self.calls += 1
        return self._results[index]


def _node_runtime(
    results: list[PlanGenerationResult],
) -> tuple[SimpleNamespace, _StubDrafter, list[tuple[str, dict]]]:
    drafter = _StubDrafter(results)
    registry = ToolRegistry()
    registry.register(drafter)
    events: list[tuple[str, dict]] = []
    context = PlannerContext(
        scheduler=Scheduler(),
        rule_engine=RuleEngine(),
        config=AgentConfig(llm_max_retries=2),
        tools=registry,
        emit=lambda name, payload: events.append((name, payload)),
    )
    return SimpleNamespace(context=context), drafter, events


def _node_state() -> dict:
    start = date.today()
    request = PlannerRequest(
        user_id=1,
        start_date=start,
        end_date=start + timedelta(days=2),
        preferences=PreferenceInput(daily_limit_minutes=300),
    )
    return {"request": request, "goals": []}


def test_plan_generation_retries_an_invalid_draft_and_recovers() -> None:
    invalid = PlanGenerationResult(
        tasks=[GeneratedTaskDraft(title="", estimated_duration=30, order_index=0)]
    )
    valid = PlanGenerationResult(
        tasks=[GeneratedTaskDraft(title="Read", estimated_duration=30, order_index=0)]
    )
    runtime, drafter, events = _node_runtime([invalid, valid])

    updates = plan_generation_node(_node_state(), runtime)

    assert drafter.calls == 2
    assert updates["plan_draft"].tasks[0].title == "Read"
    assert "errors" not in updates
    assert "format retry" in updates["notes"][0]
    assert any(name == "draft.format_invalid" for name, _ in events)


def test_plan_generation_surfaces_errors_when_format_retries_are_exhausted() -> None:
    invalid = PlanGenerationResult(
        tasks=[GeneratedTaskDraft(title="", estimated_duration=30, order_index=0)]
    )
    runtime, drafter, _events = _node_runtime([invalid])

    updates = plan_generation_node(_node_state(), runtime)

    assert drafter.calls == 3  # one generation + two bounded retries
    errors = updates["errors"]
    assert any(error.kind == "draft_format_invalid" for error in errors)
    assert "title_empty" in errors[-1].message
    assert "draft format check failed" in updates["notes"][0]
    # The preview stays available (the user can adjust), but the state is explicit.
    assert updates["plan_draft"] is not None
