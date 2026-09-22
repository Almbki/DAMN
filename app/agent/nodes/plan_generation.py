"""``plan_generation`` node: turn theory items into task drafts (MOCK).

Each :class:`~app.agent.schemas.TheoreticalItem` becomes exactly one
:class:`~app.agent.schemas.GeneratedTaskDraft`. Subject / priority / deadline
are copied from the matching :class:`~app.agent.state.GoalInput` by index.
"""

from __future__ import annotations

import json

from app.agent.schemas import (
    GeneratedTaskDraft,
    PlanGenerationResult,
    TheoreticalItem,
    UserSituationResult,
)
from app.agent.state import GoalInput, PlannerState
from app.domain.models import Task
from app.domain.models.enums import Priority, TaskStatus


class PlanGenerationAgent:
    """Creates one :class:`GeneratedTaskDraft` per :class:`TheoreticalItem`.

    PROVISIONAL TASK ID CONTRACT
    ----------------------------
    Task ids are provisional throughout the graph: ``task_id = order_index + 1``
    (1-based). ``rule_validation`` and ``plan_repair`` rely on this exact
    mapping and the Plan Service remaps the ids to real primary keys after
    persisting the plan.
    """

    name = "plan-generation-mock-v0"

    def run(self, state: PlannerState) -> PlanGenerationResult:
        """Build the candidate drafts from the theoretical workload."""
        theoretical = state.get("theoretical_workload")
        items: list[TheoreticalItem] = list(theoretical.items) if theoretical is not None else []
        goals: list[GoalInput] = list(state.get("goals") or [])
        situation: UserSituationResult | None = state.get("user_situation")
        request = state["request"]

        drafts: list[GeneratedTaskDraft] = []
        for idx, item in enumerate(items):
            goal = goals[idx] if idx < len(goals) else None
            drafts.append(
                GeneratedTaskDraft(
                    title=item.title,
                    description=item.learning_content or None,
                    goal_id=idx + 1,  # 1-based, matches AnalyzedGoal.goal_id
                    estimated_duration=item.total_minutes,
                    predicted_duration=self._predicted_duration(idx, item, situation),
                    cognitive_load=item.cognitive_load,
                    priority=goal.priority if goal else Priority.MEDIUM,
                    subject=goal.subject if goal else None,
                    standards=list(item.subtasks),
                    deadline=goal.deadline if goal else None,
                    order_index=idx,  # 0-based; provisional task id == order_index + 1
                )
            )

        self._send_prompt(state)
        return PlanGenerationResult(
            title=request.plan_title or "Adaptive Plan",
            start_date=request.start_date,
            end_date=request.end_date,
            tasks=drafts,
            confidence=0.5,  # MOCK: fixed heuristic confidence
        )

    def _send_prompt(self, state: PlannerState) -> str | None:
        """Assemble the generation prompt and append the 画像提示词 if present.

        Nodes are deterministic MOCK heuristics: the LLM (when one has been
        injected into the graph) is called only to receive the prompt; its reply
        is intentionally ignored so the node output is unchanged.
        """
        profile_prompt = state.get("profile_prompt")
        if not profile_prompt:
            return None

        sections = ["请根据以下用户画像与目标生成学习任务计划。"]
        goals: list[GoalInput] = list(state.get("goals") or [])
        if goals:
            sections.append("目标: " + "; ".join(goal.title for goal in goals))
        # 环节 2 画像提示词: compact JSON so it stays cheap in the prompt.
        sections.append(
            "画像提示词: "
            + json.dumps(profile_prompt, ensure_ascii=False, separators=(",", ":"))
        )
        prompt = "\n".join(sections)

        llm = state.get("llm")
        complete = getattr(llm, "complete", None)
        if callable(complete):
            try:
                complete(prompt)
            except Exception:  # noqa: BLE001 - prompt injection must never break planning
                pass
        return prompt

    @staticmethod
    def _predicted_duration(
        idx: int, item: TheoreticalItem, situation: UserSituationResult | None
    ) -> int:
        """Predicted duration: per-task ML value, else ``total * duration_factor``."""
        task_id = idx + 1  # PROVISIONAL TASK ID CONTRACT
        if situation is not None:
            direct = situation.predicted_duration.get(task_id)
            if direct is not None:
                return max(1, direct)
            factor = situation.duration_factor if situation.duration_factor > 0 else 1.0
            return max(1, round(item.total_minutes * factor))
        return item.total_minutes


def drafts_to_tasks(
    drafts: list[GeneratedTaskDraft],
    *,
    plan_id: int = 0,
    subject_by_order: dict[int, str] | None = None,
) -> list[Task]:
    """Convert drafts into schedulable domain :class:`Task` objects.

    Applies the PROVISIONAL TASK ID CONTRACT (``id = order_index + 1``).
    ``subject_by_order`` is accepted for interface symmetry with future
    schedulers that read a subject from the task entity; the current
    ``Task`` model has no subject field, so it is unused (RuleContext carries
    subjects instead).
    """
    tasks: list[Task] = []
    for draft in drafts:
        tasks.append(
            Task(
                id=draft.order_index + 1,  # PROVISIONAL TASK ID CONTRACT
                plan_id=plan_id,
                goal_id=draft.goal_id,
                title=draft.title,
                description=draft.description,
                estimated_duration=draft.estimated_duration,
                predicted_duration=draft.predicted_duration,
                cognitive_load=draft.cognitive_load,
                priority=draft.priority,
                scheduled_date=None,
                start_time=None,
                end_time=None,
                status=TaskStatus.SCHEDULED,
                order_index=draft.order_index,
            )
        )
    return tasks


def plan_generation_node(state: PlannerState) -> dict:
    """Node function: propose one task draft per theoretical item."""
    result = PlanGenerationAgent().run(state)
    return {
        "plan_draft": result,
        "notes": [f"plan_generation: {len(result.tasks)} draft(s) proposed."],
    }
