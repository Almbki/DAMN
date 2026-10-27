"""``plan_drafter`` tool - produce task drafts for the three planning modes.

* ``INITIAL``    - first plan from the theoretical workload + user situation
* ``ADJUSTMENT`` - apply one bounded user change to an existing preview
* ``REPLAN``     - rebuild from the full context after a FULL_REPLAN decision

LLM-backed (``llm_exposed=True``) with a deterministic fallback per mode. The
tool never emits scheduled dates or times: the scheduler owns placement.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time
from enum import StrEnum

from pydantic import BaseModel, Field

from app.agent.features import PlanProgress
from app.agent.goal_identity import goal_index_for_ref
from app.agent.llm import StructuredLLM
from app.agent.schemas import (
    AnalyzedGoal,
    GeneratedTaskDraft,
    GoalAnalysisResult,
    GoalKind,
    PlanGenerationResult,
    PreviewPayload,
    RecurrenceSpec,
    UserSituationResult,
    WorkUnit,
)
from app.agent.state import GoalInput, PreferenceInput
from app.agent.tools.base import BaseTool
from app.domain.feedback.models import AdjustmentDecision
from app.domain.models.enums import (
    CognitiveLoad,
    GoalType,
    PlanningMode,
    Priority,
    TaskKind,
    TimeOfDay,
)
from app.domain.planning import derive_planning_mode, derive_recurrence_interval
from app.domain.recurrence import (
    RecurrenceError,
    RecurrenceFrequency,
    RecurrenceRule,
    SeriesSpec,
)
from app.domain.workload import normalise_total_minutes

#: Deterministic adjustment keywords -> duration scale.
_SCALE_DOWN_RE = re.compile(r"太多|减少|少一点|少排|轻松|too much|less|reduce|overload", re.I)
_MORNING_RE = re.compile(r"上午|早上|morning", re.I)
_EVENING_RE = re.compile(r"晚上|evening|night", re.I)


class PlanDrafterMode(StrEnum):
    INITIAL = "INITIAL"
    ADJUSTMENT = "ADJUSTMENT"
    REPLAN = "REPLAN"


_PROMPT_BY_MODE: dict[PlanDrafterMode, str] = {
    PlanDrafterMode.INITIAL: "initial_plan",
    PlanDrafterMode.ADJUSTMENT: "adjustment",
    PlanDrafterMode.REPLAN: "replanning",
}


#: Hard safety cap for a finite project/curriculum (fail closed, never truncate).
MAX_PROJECT_WORK_UNITS = 60


def _analysis_by_goal(payload: PlanDrafterInput) -> dict[int, AnalyzedGoal]:
    """Index goal_analysis items by their request-local 1-based goal index."""
    analysis: GoalAnalysisResult | None = payload.goal_analysis
    if analysis is None:
        return {}
    indexed: dict[int, AnalyzedGoal] = {}
    for item in analysis.goals:
        index = goal_index_for_ref(item.goal_id, payload.goals)
        if index is None:
            continue
        indexed[index] = (
            item if item.goal_id == index else item.model_copy(update={"goal_id": index})
        )
    return indexed


def _normalise_generated_goal_ids(
    generated: PlanGenerationResult, goals: list[GoalInput]
) -> PlanGenerationResult:
    """Enforce the request-local goal reference contract on every draft.

    ``goal_id`` is 1..N for this request. A persisted database id that matches
    one of the request's goals is mapped back to its position (defensive: older
    prompts or a model echo may emit it); anything else fails closed so a task
    can never be attached to the wrong goal.
    """
    tasks: list[GeneratedTaskDraft] = []
    for task in generated.tasks:
        if task.goal_id is None:
            if not goals:
                index = None
            elif len(goals) == 1:
                index = 1
            else:
                raise ValueError(
                    f"task {task.title!r} has no valid goal_id; refusing to "
                    "attach it to another goal"
                )
        else:
            index = goal_index_for_ref(task.goal_id, goals)
            if index is None:
                raise ValueError(
                    f"task {task.title!r} has invalid goal_id {task.goal_id}; "
                    f"expected a 1..{len(goals)} request index or one of this "
                    "request's persisted goal ids"
                )
        tasks.append(
            task if task.goal_id == index else task.model_copy(update={"goal_id": index})
        )
    return generated.model_copy(update={"tasks": tasks})


def _goal_key(goal: GoalInput | None, goal_index: int) -> str:
    """Stable goal identity for cross-version work-unit keys."""
    if goal is not None and goal.existing_goal_id is not None:
        return str(goal.existing_goal_id)
    return str(goal_index)


def _resolve_earliest(
    goal: GoalInput | None, analyzed: AnalyzedGoal | None
) -> date | None:
    """Later of explicit goal start and the analyzed explicit earliest day."""
    explicit = goal.start_date if goal is not None else None
    inferred = analyzed.earliest_start_date if analyzed is not None else None
    dates = [day for day in (explicit, inferred) if day is not None]
    earliest = max(dates) if dates else None
    if (
        earliest is not None
        and goal is not None
        and goal.deadline is not None
        and earliest > goal.deadline.date()
    ):
        raise ValueError(
            f"goal {goal.title!r}: earliest start {earliest.isoformat()} is "
            f"after deadline {goal.deadline.date().isoformat()}"
        )
    return earliest


def _goal_index_for(task: GeneratedTaskDraft, goal_count: int) -> int | None:
    """Resolve a draft's goal index.

    A valid ``goal_id`` wins. When the model omitted it and there is exactly one
    goal, attributing the draft to that goal is safe and prevents the historical
    "unexpanded recurring drafts" escape.
    """
    if task.goal_id is not None and 0 < task.goal_id <= goal_count:
        return task.goal_id
    if goal_count == 1:
        return 1
    return None


def _resolve_planning_mode(
    goal: GoalInput | None, analyzed: AnalyzedGoal | None
) -> PlanningMode:
    """Resolve the product-level four-way mode.

    Explicit ``planning_mode`` wins; then explicit legacy ``task_kind``; then the
    LLM classification. ``project_recurring`` is ``goal_kind=project`` plus a
    cadence (LLM recurrence or explicit recurrence fields).
    """
    if goal is None:
        return PlanningMode.ONE_OFF
    if goal.planning_mode is not None:
        return PlanningMode(goal.planning_mode)
    # ROUTINE / ONE_OFF are unambiguous. LONG_TERM is ambiguous (habit vs
    # curriculum), so the analysis classification decides it.
    if goal.task_kind in {TaskKind.ROUTINE, TaskKind.ONE_OFF}:
        return derive_planning_mode(
            None,
            goal_type=goal.goal_type,
            task_kind=goal.task_kind,
            recurrence_frequency=goal.recurrence_frequency,
            recurrence_weekdays=goal.recurrence_weekdays,
        )
    if analyzed is not None:
        if analyzed.goal_kind is GoalKind.PROJECT:
            has_cadence = (
                analyzed.recurrence is not None
                or goal.recurrence_frequency is not None
                or bool(goal.recurrence_weekdays)
            )
            return (
                PlanningMode.PROJECT_RECURRING
                if has_cadence
                else PlanningMode.PROJECT
            )
        if analyzed.goal_kind is GoalKind.RECURRING:
            return PlanningMode.RECURRING
        return PlanningMode.ONE_OFF
    return derive_planning_mode(
        None,
        goal_type=goal.goal_type,
        task_kind=goal.task_kind,
        recurrence_frequency=goal.recurrence_frequency,
        recurrence_weekdays=goal.recurrence_weekdays,
    )


def _resolve_goal_kind(goal: GoalInput | None, analyzed: AnalyzedGoal | None) -> GoalKind:
    """Three-value semantic kind used by the base-draft builder."""
    mode = _resolve_planning_mode(goal, analyzed)
    if mode is PlanningMode.RECURRING:
        return GoalKind.RECURRING
    if mode in {PlanningMode.PROJECT, PlanningMode.PROJECT_RECURRING}:
        return GoalKind.PROJECT
    return GoalKind.ONE_OFF


def _task_kind_for(kind: GoalKind, goal: GoalInput | None) -> TaskKind:
    if kind is not GoalKind.RECURRING:
        return TaskKind.ONE_OFF
    if goal is not None and goal.task_kind is not None:
        return goal.task_kind
    if goal is not None and goal.goal_type is GoalType.HABIT:
        return TaskKind.ROUTINE
    return TaskKind.LONG_TERM


def _resolve_recurrence(
    goal: GoalInput | None, analyzed: AnalyzedGoal | None
) -> tuple[RecurrenceFrequency, int, list[int]]:
    """Resolve frequency/interval/weekdays without parsing text.

    Explicit ``recurrence_weekdays`` wins; an all-seven-day list is daily.
    Otherwise the analysis classification fills the gap, then daily is the default.
    """
    weekdays: list[int] = []
    if goal is not None and goal.recurrence_weekdays:
        weekdays = sorted({int(day) for day in goal.recurrence_weekdays})
    interval = (
        derive_recurrence_interval(goal.recurrence_interval)
        if goal is not None
        else 1
    )
    frequency: RecurrenceFrequency | None = None

    if goal is not None and goal.recurrence_frequency is not None:
        frequency = RecurrenceFrequency(goal.recurrence_frequency)

    if analyzed is not None and analyzed.recurrence is not None:
        spec: RecurrenceSpec = analyzed.recurrence
        interval = max(1, int(spec.interval))
        frequency = RecurrenceFrequency(spec.frequency)
        if not weekdays and spec.weekdays:
            weekdays = sorted({int(day) for day in spec.weekdays})

    if weekdays:
        if len(weekdays) >= 7:
            return RecurrenceFrequency.DAILY, 1, []
        return RecurrenceFrequency.WEEKLY, interval, weekdays

    return frequency or RecurrenceFrequency.DAILY, interval, []


class PlanDrafterInput(BaseModel):
    mode: PlanDrafterMode = PlanDrafterMode.INITIAL
    title: str = "Adaptive Plan"
    goals: list[GoalInput] = Field(default_factory=list)
    #: Machine-readable classification from the ``goal_analysis`` node.
    goal_analysis: GoalAnalysisResult | None = None
    user_situation: UserSituationResult | None = None
    theoretical: dict = Field(default_factory=dict)
    preferences: PreferenceInput | None = None
    #: Plan horizon, used as the date range for long-term/routine splitting.
    start_date: date | None = None
    end_date: date | None = None

    # adjustment mode
    preview: PreviewPayload | None = None
    user_adjustment: str | None = None
    adjustment_count: int = 0

    # replan mode
    planning_context: str = ""
    #: Replan: completed minutes per stable work-unit key.
    completed_work_by_unit: dict[str, int] = Field(default_factory=dict)
    #: Replan: work units whose every required chunk is already completed.
    completed_work_unit_keys: set[str] = Field(default_factory=set)
    adjustment: AdjustmentDecision | None = None
    progress: PlanProgress | None = None
    #: Read-only current-plan snapshot (replan prompt; never regenerated here).
    current_plan: dict = Field(default_factory=dict)
    replan_reason: str | None = None
    completed_task_titles: list[str] = Field(default_factory=list)
    #: Truthful origin of the per-task production estimates.
    prediction_source: str | None = None
    #: Typed user-model snapshot rendered into the prompt (Level 1 + Level 2).
    user_model_context: str = ""


class PlanDrafterTool(BaseTool[PlanDrafterInput, PlanGenerationResult]):
    name = "plan_drafter"
    description = (
        "Produce structured task drafts for an initial plan, a bounded preview "
        "adjustment, or a full replan. Never returns dates or times."
    )
    llm_exposed = True

    def __init__(self, llm: StructuredLLM | None = None) -> None:
        self._llm = llm

    def prompt_name(self, mode: PlanDrafterMode) -> str:
        return _PROMPT_BY_MODE[mode]

    def run(self, payload: PlanDrafterInput) -> PlanGenerationResult:
        fallback = self._fallback(payload)
        if self._llm is None or not self._llm.enabled:
            generated = fallback
        else:
            result = self._llm.complete_model(
                prompt_name=self.prompt_name(payload.mode),
                schema=PlanGenerationResult,
                variables=self._prompt_variables(payload),
                fallback=fallback,
            )
            generated = self._with_truthful_source(result.value, payload.prediction_source)
            generated = self._strip_unsupplemented_standards(generated, payload.goals)

        # Adjustment operates on an already-materialized preview: its
        # occurrence dates/series are authoritative and must not be regenerated.
        if payload.mode is PlanDrafterMode.ADJUSTMENT:
            return generated
        return self._materialize(generated, payload)

    # -- deterministic materialization ------------------------------------
    @classmethod
    def _materialize(
        cls, generated: PlanGenerationResult, payload: PlanDrafterInput
    ) -> PlanGenerationResult:
        """Turn model output into deterministic task instances.

        The LLM decides *what* the work is. This method decides *which dates
        exist*: recurring goals become one draft per occurrence, projects become
        a finite ordered work-unit sequence, and one-offs stay one-off. Any
        date-like field the model emitted is ignored for recurring/project
        goals — the model is not allowed to enumerate occurrences.
        """
        goals = payload.goals
        analysis = _analysis_by_goal(payload)
        # Drafts may carry either a local index or (defensively) a persisted id
        # echoed by a model. Normalise before any grouping/mapping happens.
        generated = _normalise_generated_goal_ids(generated, goals)

        # A draft must belong to a real goal, and it must not claim a deadline
        # beyond that goal. Otherwise the LLM can silently attach one goal's
        # work (and deadline) to another goal id.
        for task in generated.tasks:
            if not goals or task.goal_id is None:
                continue
            task_goal = goals[task.goal_id - 1]
            if (
                task.deadline is not None
                and task_goal.deadline is not None
                and task.deadline.date() > task_goal.deadline.date()
            ):
                raise ValueError(
                    f"task {task.title!r} deadline {task.deadline.date()} is "
                    f"after goal {task_goal.title!r} deadline "
                    f"{task_goal.deadline.date()}"
                )

        grouped: dict[int, list[GeneratedTaskDraft]] = {}
        unanchored: list[GeneratedTaskDraft] = []
        for task in generated.tasks:
            index = _goal_index_for(task, len(goals))
            if index is None:
                unanchored.append(task)
            else:
                grouped.setdefault(index, []).append(task)

        expanded: list[GeneratedTaskDraft] = list(unanchored)
        series_specs: list[SeriesSpec] = []
        for index, goal in enumerate(goals, start=1):
            analyzed = analysis.get(index)
            mode = _resolve_planning_mode(goal, analyzed)
            templates = grouped.get(index, [])
            if mode is PlanningMode.RECURRING:
                drafts, spec = cls._materialize_recurring(
                    goal, index, templates, analyzed, payload
                )
                expanded.extend(drafts)
                series_specs.append(spec)
            elif mode is PlanningMode.PROJECT:
                expanded.extend(
                    cls._materialize_project(goal, index, templates, analyzed, payload)
                )
            elif mode is PlanningMode.PROJECT_RECURRING:
                drafts, spec = cls._materialize_project_recurring(
                    goal, index, templates, analyzed, payload
                )
                expanded.extend(drafts)
                series_specs.append(spec)
            else:
                expanded.extend(
                    cls._materialize_one_off(goal, index, templates, analyzed)
                )

        # Replan dedup: never re-create completed work. Partial work units are
        # reduced by the completed minutes; fully completed units disappear.
        deduped: list[GeneratedTaskDraft] = []
        for draft in expanded:
            key = draft.work_unit_key
            if key and key in payload.completed_work_unit_keys:
                continue
            if key and key in payload.completed_work_by_unit:
                done = max(0, int(payload.completed_work_by_unit[key]))
                remaining = int(draft.estimated_duration) - done
                if remaining <= 0:
                    continue
                predicted = draft.predicted_duration
                if predicted is not None:
                    predicted = max(1, min(int(predicted), remaining))
                draft = draft.model_copy(
                    update={
                        "estimated_duration": remaining,
                        "predicted_duration": predicted,
                    }
                )
            deduped.append(draft)
        expanded = deduped

        ordered = [
            task.model_copy(update={"order_index": position})
            for position, task in enumerate(expanded)
        ]
        return generated.model_copy(
            update={"tasks": ordered, "series_specs": series_specs}
        )

    @classmethod
    def _materialize_recurring(
        cls,
        goal: GoalInput | None,
        goal_index: int,
        templates: list[GeneratedTaskDraft],
        analyzed: AnalyzedGoal | None,
        payload: PlanDrafterInput,
    ) -> tuple[list[GeneratedTaskDraft], SeriesSpec]:
        try:
            start = _resolve_earliest(goal, analyzed) or payload.start_date
        except ValueError as exc:
            # An inverted earliest/deadline window is an invalid recurrence
            # range, not a generic one-off date error.
            raise RecurrenceError(str(exc)) from exc
        end = (
            goal.deadline.date()
            if goal is not None and goal.deadline is not None
            else payload.end_date
        )
        if start is None or end is None:
            raise RecurrenceError(
                f"recurring goal {goal_index} has no start/end date to expand"
            )

        frequency, interval, weekdays = _resolve_recurrence(goal, analyzed)
        rule = RecurrenceRule(
            frequency=frequency,
            start_date=start,
            end_date=end,
            interval=interval,
            weekdays=tuple(weekdays),
        )
        occurrences = rule.occurrences()

        template = templates[0] if templates else None
        if template is None:
            template = cls._default_template(goal, goal_index, analyzed)
        duration = (
            int(goal.daily_target_minutes)
            if goal is not None and goal.daily_target_minutes
            else max(1, int(template.estimated_duration))
        )
        duration = normalise_total_minutes(
            mode=PlanningMode.RECURRING,
            total_minutes=duration,
            cognitive_load=template.cognitive_load,
        )
        task_kind = _task_kind_for(GoalKind.RECURRING, goal)
        series_id = f"goal-{goal_index}-{task_kind.value}"

        drafts = [
            template.model_copy(
                update={
                    "goal_id": goal_index,
                    "estimated_duration": duration,
                    "predicted_duration": duration,
                    "task_kind": task_kind,
                    "series_id": series_id,
                    "series_index": position,
                    "occurrence_date": day,
                    "deadline": datetime.combine(day, time.max),
                    "is_flexible": False,
                    # Recurring habits are opaque execution blocks by default:
                    # the external app owns the internal checklist.
                    "standards": [],
                }
            )
            for position, day in enumerate(occurrences)
        ]
        spec = SeriesSpec(
            series_id=series_id,
            start_date=start,
            end_date=end,
            frequency=frequency,
            interval=interval,
            weekdays=weekdays,
        )
        return drafts, spec

    @classmethod
    def _materialize_project(
        cls,
        goal: GoalInput | None,
        goal_index: int,
        templates: list[GeneratedTaskDraft],
        analyzed: AnalyzedGoal | None,
        payload: PlanDrafterInput | None = None,
    ) -> list[GeneratedTaskDraft]:
        """A project is a finite ordered curriculum, never a daily copy."""
        units: list[WorkUnit] = []
        if analyzed is not None and analyzed.work_units:
            units = list(analyzed.work_units)
        elif templates:
            units = [
                WorkUnit(
                    title=task.title,
                    description=task.description or "",
                    estimated_minutes=max(1, int(task.estimated_duration)),
                )
                for task in templates
            ]

        if not units:
            # Never fake a project unit from the goal title. The clarification
            # contract (decomposition_status=needs_clarification) is the correct
            # path; this is the fail-closed backstop.
            raise RecurrenceError(
                f"project goal {goal_index} needs work units; "
                "ask the user for curriculum/progress (clarification required)"
            )
        if len(units) > MAX_PROJECT_WORK_UNITS:
            raise RecurrenceError(
                f"project goal {goal_index} produced {len(units)} work units; "
                f"the maximum is {MAX_PROJECT_WORK_UNITS}"
            )

        theoretical_by_unit: dict[int, dict] = {}
        if payload is not None:
            for item in payload.theoretical.get("items") or []:
                if (
                    int(item.get("goal_id") or 0) == goal_index
                    and item.get("work_unit_index") is not None
                ):
                    theoretical_by_unit[int(item["work_unit_index"])] = item

        series_id = f"goal-{goal_index}-project"
        earliest = _resolve_earliest(goal, analyzed)
        drafts: list[GeneratedTaskDraft] = []
        for position, unit in enumerate(units):
            base = templates[position] if position < len(templates) else None
            unit_minutes = max(1, int(unit.estimated_minutes))
            theoretical = theoretical_by_unit.get(position)
            if theoretical is not None:
                unit_minutes = max(
                    1, int(theoretical.get("total_minutes") or unit_minutes)
                )
            unit_minutes = normalise_total_minutes(
                mode=PlanningMode.PROJECT,
                total_minutes=unit_minutes,
                cognitive_load=(
                    base.cognitive_load if base is not None else CognitiveLoad.MEDIUM
                ),
            )
            if base is not None:
                draft = base.model_copy(
                    update={
                        "title": unit.title,
                        "description": unit.description or base.description,
                        "goal_id": goal_index,
                        "estimated_duration": unit_minutes,
                        "predicted_duration": unit_minutes,
                        "deadline": goal.deadline if goal is not None else base.deadline,
                        "earliest_start_date": earliest,
                        "task_kind": TaskKind.ONE_OFF,
                    "work_unit_key": (
                        f"wg-{_goal_key(goal, goal_index)}-project-{position}"
                    ),
                    "series_id": series_id,
                    "series_index": position,
                    "occurrence_date": None,
                    "is_flexible": True,
                }
            )
            else:
                draft = GeneratedTaskDraft(
                    title=unit.title,
                    description=unit.description or None,
                    goal_id=goal_index,
                    estimated_duration=unit_minutes,
                    predicted_duration=unit_minutes,
                    priority=goal.priority if goal is not None else Priority.MEDIUM,
                    subject=goal.subject if goal is not None else None,
                    deadline=goal.deadline if goal is not None else None,
                    earliest_start_date=earliest,
                    task_kind=TaskKind.ONE_OFF,
                    work_unit_key=(
                        f"wg-{_goal_key(goal, goal_index)}-project-{position}"
                    ),
                    series_id=series_id,
                    series_index=position,
                    is_flexible=True,
                )
            drafts.append(draft)
        return drafts

    @classmethod
    def _materialize_project_recurring(
        cls,
        goal: GoalInput | None,
        goal_index: int,
        templates: list[GeneratedTaskDraft],
        analyzed: AnalyzedGoal | None,
        payload: PlanDrafterInput,
    ) -> tuple[list[GeneratedTaskDraft], SeriesSpec]:
        """Pair a finite project's work units with recurrence dates.

        One work unit advances per occurrence. If the deadline has fewer slots
        than work units, the excess units stay as deadline-bound one-off steps
        (never dropped). If the curriculum ends before the deadline, the series
        ends with the last used occurrence.
        """
        drafts = cls._materialize_project(
            goal, goal_index, templates, analyzed, payload
        )
        try:
            start = _resolve_earliest(goal, analyzed) or payload.start_date
        except ValueError as exc:
            raise RecurrenceError(str(exc)) from exc
        end = (
            goal.deadline.date()
            if goal is not None and goal.deadline is not None
            else payload.end_date
        )
        if start is None or end is None:
            raise RecurrenceError(
                f"project_recurring goal {goal_index} has no start/end date"
            )
        frequency, interval, weekdays = _resolve_recurrence(goal, analyzed)
        rule = RecurrenceRule(
            frequency=frequency,
            start_date=start,
            end_date=end,
            interval=interval,
            weekdays=tuple(weekdays),
        )
        occurrences = rule.occurrences()
        paired = min(len(drafts), len(occurrences))
        if paired == 0:
            raise RecurrenceError(
                f"project_recurring goal {goal_index} has no work units or "
                "no occurrence dates"
            )
        series_id = f"goal-{goal_index}-project"
        updated: list[GeneratedTaskDraft] = []
        for position, draft in enumerate(drafts):
            if position < paired:
                day = occurrences[position]
                updated.append(
                    draft.model_copy(
                        update={
                            "series_id": series_id,
                            "series_index": position,
                            "occurrence_date": day,
                            "deadline": datetime.combine(day, time.max),
                            "is_flexible": False,
                        }
                    )
                )
            else:
                updated.append(
                    draft.model_copy(
                        update={
                            "series_id": series_id,
                            "series_index": position,
                            "occurrence_date": None,
                            "deadline": (
                                goal.deadline if goal is not None else draft.deadline
                            ),
                            "is_flexible": True,
                        }
                    )
                )
        spec = SeriesSpec(
            series_id=series_id,
            start_date=occurrences[0],
            end_date=occurrences[paired - 1],
            frequency=frequency,
            interval=interval,
            weekdays=weekdays,
        )
        return updated, spec

    @staticmethod
    def _materialize_one_off(
        goal: GoalInput | None,
        goal_index: int,
        templates: list[GeneratedTaskDraft],
        analyzed: AnalyzedGoal | None,
    ) -> list[GeneratedTaskDraft]:
        deadline = goal.deadline if goal is not None else None
        earliest = _resolve_earliest(goal, analyzed)
        drafts: list[GeneratedTaskDraft] = []
        for task in templates:
            total = normalise_total_minutes(
                mode=PlanningMode.ONE_OFF,
                total_minutes=task.estimated_duration,
                explicit_minutes=(
                    goal.estimated_minutes if goal is not None else None
                ),
                cognitive_load=task.cognitive_load,
            )
            predicted = task.predicted_duration
            if predicted is None or predicted > total:
                predicted = total
            drafts.append(
                task.model_copy(
                    update={
                        "goal_id": goal_index,
                        "estimated_duration": total,
                        "predicted_duration": predicted,
                        "deadline": deadline,
                        "earliest_start_date": earliest,
                        "task_kind": TaskKind.ONE_OFF,
                        "work_unit_key": (
                            f"wg-{_goal_key(goal, goal_index)}-one_off"
                        ),
                        "series_id": None,
                        "series_index": None,
                        "occurrence_date": None,
                    }
                )
            )
        return drafts

    @staticmethod
    def _default_template(
        goal: GoalInput | None,
        goal_index: int,
        analyzed: AnalyzedGoal | None,
    ) -> GeneratedTaskDraft:
        title = goal.title if goal is not None else "Task"
        if analyzed is not None and analyzed.title:
            title = analyzed.title
        minutes = 60
        if goal is not None:
            minutes = goal.daily_target_minutes or goal.estimated_minutes or 60
        return GeneratedTaskDraft(
            title=title,
            description=goal.description if goal is not None else None,
            goal_id=goal_index,
            estimated_duration=minutes,
            predicted_duration=minutes,
            priority=goal.priority if goal is not None else Priority.MEDIUM,
            subject=goal.subject if goal is not None else None,
        )

    @staticmethod
    def _strip_unsupplemented_standards(
        generated: PlanGenerationResult, goals: list[GoalInput]
    ) -> PlanGenerationResult:
        """A blank supplement field means no substeps, even if the model invented them."""
        if not generated.tasks:
            return generated
        cleaned = []
        for task in generated.tasks:
            index = goal_index_for_ref(task.goal_id, goals)
            goal = goals[index - 1] if index is not None else None
            if goal is None or not goal.description or not goal.description.strip():
                task = task.model_copy(update={"standards": []})
            cleaned.append(task)
        return generated.model_copy(update={"tasks": cleaned})

    @staticmethod
    def _with_truthful_source(
        generated: PlanGenerationResult, source: str | None
    ) -> PlanGenerationResult:
        """Stamp the ML predictor's origin onto LLM-generated drafts.

        ``GeneratedTaskDraft.prediction_source`` is part of the LLM output schema,
        so a successful call would otherwise let the model invent the provenance
        of the numbers (observed: a full sentence describing the user-situation
        inputs). That is untruthful, and it is wider than
        ``prediction_logs.source`` (VARCHAR(64)), which aborted the whole confirm
        transaction. The deterministic fallback path already uses the injected
        source; the LLM path must match it.
        """
        if not generated.tasks:
            return generated
        return generated.model_copy(
            update={
                "tasks": [
                    task.model_copy(update={"prediction_source": source})
                    for task in generated.tasks
                ]
            }
        )

    # -- prompt variables --------------------------------------------------
    @staticmethod
    def _prompt_variables(payload: PlanDrafterInput) -> dict[str, object]:
        return {
            "theoretical_analysis": payload.theoretical,
            "user_situation": (
                payload.user_situation.model_dump(mode="json")
                if payload.user_situation
                else {}
            ),
            "goals": [
                {
                    "goal_index": index,
                    **goal.model_dump(
                        mode="json", exclude={"existing_goal_id"}
                    ),
                }
                for index, goal in enumerate(payload.goals, start=1)
            ],
            "goal_analysis": (
                payload.goal_analysis.model_dump(mode="json")
                if payload.goal_analysis
                else {}
            ),
            "preferences": (
                payload.preferences.model_dump(mode="json") if payload.preferences else {}
            ),
            "preview": payload.preview.model_dump(mode="json") if payload.preview else {},
            "user_adjustment": payload.user_adjustment or "",
            "adjustment_count": payload.adjustment_count,
            "planning_context": payload.planning_context,
            "adjustment_decision": (
                payload.adjustment.model_dump(mode="json") if payload.adjustment else {}
            ),
            "current_plan": (
                payload.current_plan
                or (
                    payload.preview.model_dump(mode="json")
                    if payload.preview
                    else {}
                )
            ),
            "progress": payload.progress.model_dump(mode="json") if payload.progress else {},
            "replan_reason": payload.replan_reason or "",
            "user_model": payload.user_model_context or "(no user model available)",
        }

    # -- deterministic fallback -------------------------------------------
    @classmethod
    def _fallback(cls, payload: PlanDrafterInput) -> PlanGenerationResult:
        if payload.mode is PlanDrafterMode.ADJUSTMENT and payload.preview is not None:
            drafts = cls._adjust(
                cls._preview_to_drafts(payload.preview, payload.prediction_source),
                payload.user_adjustment,
            )
        else:
            drafts = cls._from_theoretical(payload)

        return PlanGenerationResult(
            title=payload.title,
            tasks=drafts,
            confidence=0.5,
        )

    @staticmethod
    def _from_theoretical(payload: PlanDrafterInput) -> list[GeneratedTaskDraft]:
        """Produce one base draft per theoretical item.

        Expansion into occurrence instances / project work units is done later
        by ``_materialize`` so the fallback and LLM paths share one contract.
        """
        items = list(payload.theoretical.get("items") or [])
        situation = payload.user_situation
        completed = {title.strip().lower() for title in payload.completed_task_titles}
        drafts: list[GeneratedTaskDraft] = []

        analysis = _analysis_by_goal(payload)
        for idx, item in enumerate(items):
            raw_goal_id = item.get("goal_id")
            try:
                parsed_goal_id = (
                    int(raw_goal_id) if raw_goal_id is not None else idx + 1
                )
            except (TypeError, ValueError):
                parsed_goal_id = idx + 1
            goal_id = goal_index_for_ref(parsed_goal_id, payload.goals)
            if goal_id is None:
                goal_id = parsed_goal_id
            goal = (
                payload.goals[goal_id - 1]
                if 0 < goal_id <= len(payload.goals)
                else None
            )
            analyzed = analysis.get(goal_id)
            title = str(item.get("title", f"Task {idx + 1}"))
            kind = _resolve_goal_kind(goal, analyzed)
            # Only one-off titles are filtered by title: a single completed
            # occurrence must never hide the rest of a long-term series.
            if (
                payload.mode is PlanDrafterMode.REPLAN
                and kind is GoalKind.ONE_OFF
                # Stable work-unit keys are authoritative when present. The
                # legacy title fallback must not skip a partially completed
                # chunked work unit.
                and not payload.completed_work_by_unit
                and not payload.completed_work_unit_keys
                and title.strip().lower() in completed
            ):
                continue
            provisional_id = idx + 1
            mode = _resolve_planning_mode(goal, analyzed)
            total = normalise_total_minutes(
                mode=mode,
                total_minutes=int(item.get("total_minutes") or 60),
                explicit_minutes=(
                    goal.estimated_minutes
                    if goal is not None and mode is PlanningMode.ONE_OFF
                    else None
                ),
                cognitive_load=item.get("cognitive_load") or CognitiveLoad.MEDIUM,
            )
            predicted = None
            completion = None
            slot = None
            stress = None
            if situation is not None:
                predicted = situation.predicted_duration.get(provisional_id)
                completion = situation.predicted_completion_probability.get(provisional_id)
                stress = situation.stress_state
                slot = situation.recommended_time_slot
            if predicted is None:
                predicted = max(1, total)

            # A recurring goal's per-day quota is the template duration; the
            # materializer applies it to every occurrence.
            duration = total
            if mode is PlanningMode.RECURRING:
                duration = (
                    int(goal.daily_target_minutes)
                    if goal is not None and goal.daily_target_minutes
                    else total
                )
                duration = normalise_total_minutes(
                    mode=PlanningMode.RECURRING,
                    total_minutes=duration,
                    cognitive_load=item.get("cognitive_load") or CognitiveLoad.MEDIUM,
                )

            drafts.append(
                GeneratedTaskDraft(
                    title=title,
                    description=str(item.get("learning_content") or "") or None,
                    goal_id=goal_id,
                    estimated_duration=duration,
                    predicted_duration=duration if kind is GoalKind.RECURRING else predicted,
                    completion_probability=completion,
                    recommended_time_slot=slot,
                    predicted_stress=stress,
                    cognitive_load=item.get("cognitive_load") or "medium",
                    priority=goal.priority if goal else Priority.MEDIUM,
                    subject=goal.subject if goal else None,
                    standards=(
                        list(item.get("subtasks") or [])
                        if goal and goal.description and goal.description.strip()
                        else []
                    ),
                    deadline=goal.deadline if goal else None,
                    prediction_source=payload.prediction_source,
                    order_index=len(drafts),
                    task_kind=_task_kind_for(kind, goal),
                    target_amount=goal.target_amount if goal else None,
                    target_unit=goal.target_unit if goal else None,
                )
            )
        return drafts

    @staticmethod
    def _preview_to_drafts(
        preview: PreviewPayload, prediction_source: str | None = None
    ) -> list[GeneratedTaskDraft]:
        return [
            GeneratedTaskDraft(
                title=task.title,
                description=task.description,
                goal_id=task.goal_id,
                estimated_duration=task.estimated_duration,
                predicted_duration=task.predicted_duration,
                completion_probability=task.completion_probability,
                recommended_time_slot=task.recommended_time_slot,
                cognitive_load=task.cognitive_load,
                priority=task.priority,
                subject=task.subject,
                standards=list(task.standards),
                prediction_source=prediction_source,
                order_index=index,
                task_kind=task.task_kind,
                series_id=task.series_id,
                series_index=task.series_index,
                occurrence_date=task.occurrence_date,
                target_amount=task.target_amount,
                target_unit=task.target_unit,
                is_flexible=task.is_flexible,
            )
            for index, task in enumerate(preview.tasks)
        ]

    @staticmethod
    def _adjust(
        drafts: list[GeneratedTaskDraft], note: str | None
    ) -> list[GeneratedTaskDraft]:
        """Minimal deterministic adjustment: scale load and/or bias the slot."""
        if not note:
            return drafts

        scale = 0.8 if _SCALE_DOWN_RE.search(note) else 1.0
        prefer: TimeOfDay | None = None
        if _MORNING_RE.search(note):
            prefer = TimeOfDay.MORNING
        elif _EVENING_RE.search(note):
            prefer = TimeOfDay.EVENING

        adjusted: list[GeneratedTaskDraft] = []
        for index, draft in enumerate(drafts):
            estimated = max(5, round(draft.estimated_duration * scale))
            predicted = (
                max(5, round(draft.predicted_duration * scale))
                if draft.predicted_duration is not None
                else None
            )
            adjusted.append(
                draft.model_copy(
                    update={
                        "estimated_duration": estimated,
                        "predicted_duration": predicted,
                        "recommended_time_slot": prefer or draft.recommended_time_slot,
                        "order_index": index,
                    }
                )
            )
        return adjusted

    def summarize(self, value: PlanGenerationResult) -> str:
        return f"{len(value.tasks)} draft(s) [{self.name}]"


__all__ = ["PlanDrafterInput", "PlanDrafterMode", "PlanDrafterTool"]
