"""TEST 6: rule violation -> plan repair -> rule validation -> valid plan.

Note: the heuristic Scheduler is itself rule-aware (capacity, buffers, subject
conflicts, high-cognitive spacing), so most candidate plans already pass. To
exercise the repair loop we inject a violation the scheduler *cannot* avoid on
its own: a task whose deadline is already in the past.
"""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

from app.agent.nodes.repair import plan_repair_node
from app.agent.nodes.validation import rule_validation_node
from app.agent.schemas import GeneratedTaskDraft, PlanGenerationResult
from app.agent.state import AgentConfig, PlannerContext, PlannerRequest, PreferenceInput
from app.domain.models.enums import CognitiveLoad, Priority
from app.domain.rules.base import RuleEngine
from app.domain.scheduling.scheduler import Scheduler
from app.ml.predictors import PredictorSet


def _context() -> PlannerContext:
    return PlannerContext(
        scheduler=Scheduler(),
        rule_engine=RuleEngine(),
        predictors=PredictorSet.default(),
        config=AgentConfig(max_repair_attempts=2),
        llm=None,
        context_builder=None,
    )


def _runtime(ctx: PlannerContext) -> SimpleNamespace:
    return SimpleNamespace(context=ctx)


def _state(drafts: list[GeneratedTaskDraft], *, attempts: int = 0) -> dict:
    request = PlannerRequest(
        user_id=1,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=13),
        preferences=PreferenceInput(daily_limit_minutes=300, available_minutes_per_day=480),
    )
    return {
        "request": request,
        "user_id": 1,
        "goals": [],
        "plan_draft": PlanGenerationResult(tasks=drafts),
        "repair_attempts": attempts,
        "max_repair_attempts": 2,
        "notes": [],
    }


def _draft(
    index: int,
    minutes: int,
    *,
    deadline=None,
    priority: Priority = Priority.MEDIUM,
) -> GeneratedTaskDraft:
    return GeneratedTaskDraft(
        title=f"task-{index}",
        estimated_duration=minutes,
        cognitive_load=CognitiveLoad.MEDIUM,
        priority=priority,
        deadline=deadline,
        order_index=index,
    )


def test_deadline_violation_is_repaired_and_revalidated() -> None:
    ctx = _context()
    yesterday = date.today() - timedelta(days=1)
    drafts = [
        _draft(0, 60, priority=Priority.HIGH),
        _draft(1, 60, deadline=yesterday, priority=Priority.LOW),
    ]
    state = _state(drafts)

    # 1. Rule Engine rejects the candidate.
    state.update(rule_validation_node(state, _runtime(ctx)))
    assert state["rule_validation"].passed is False
    assert any(v.code == "deadline_exceeded" for v in state["rule_violations"])

    # 2. Repair drops the unfixable task and re-validates.
    state.update(plan_repair_node(state, _runtime(ctx)))

    assert state["repair_attempts"] == 1
    assert state["repaired_plan"].repaired is True
    assert state["repaired_plan"].changed_task_ids
    assert state["rule_validation"].passed is True
    assert state["rule_violations"] == []
    # The feasible task survives; the impossible one is gone.
    assert [draft.title for draft in state["plan_draft"].tasks] == ["task-0"]


def test_valid_plan_is_untouched_by_repair() -> None:
    ctx = _context()
    state = _state([_draft(0, 60), _draft(1, 60)])

    state.update(rule_validation_node(state, _runtime(ctx)))
    assert state["rule_validation"].passed is True

    updates = plan_repair_node(state, _runtime(ctx))
    assert updates["repaired_plan"].changed_task_ids == []
    assert updates["rule_validation"].passed is True
    assert len(updates["plan_draft"].tasks) == 2


def test_repair_records_attempts_and_never_lies_about_validity() -> None:
    ctx = _context()
    yesterday = date.today() - timedelta(days=1)
    state = _state([_draft(0, 60, deadline=yesterday)])

    state.update(rule_validation_node(state, _runtime(ctx)))
    first = plan_repair_node(state, _runtime(ctx))
    assert first["repair_attempts"] == 1
    # After the drop the plan must be genuinely valid, not just "repaired=True".
    assert first["rule_validation"].passed is True
    assert first["rule_violations"] == []
