"""Derive automatic TaskLog indicators from plans and executions.

Missing logs are represented as ``None``/unavailable, never as failure.  Start
delay is computed for transparency but is *only* a candidate flag; it is never
promoted to procrastination inside this module.
"""

from __future__ import annotations

from .config import DDSRConfig
from .schemas import (
    BehavioralIndicators,
    DayInput,
    EvidenceItem,
    EvidenceType,
    GoalAttainmentIndicator,
    InitiationIndicator,
    PersistenceIndicator,
    ProcrastinationEvidenceIndicator,
    TaskDerived,
    TaskExecution,
    TaskPlan,
)


def _minutes_between(later, earlier) -> float:
    return (later - earlier).total_seconds() / 60.0


def derive_task_metrics(
    day: DayInput, config: DDSRConfig
) -> list[TaskDerived]:
    executions: dict[str, TaskExecution] = {
        execution.task_id: execution for execution in day.task_executions
    }
    derived: list[TaskDerived] = []
    for plan in day.task_plans:
        execution = executions.get(plan.task_id)
        started = execution is not None and execution.actual_start is not None
        start_delay = (
            _minutes_between(execution.actual_start, plan.planned_start)
            if started
            else None
        )
        duration_ratio = (
            execution.actual_duration_minutes / plan.estimated_duration_minutes
            if execution is not None
            and execution.actual_duration_minutes is not None
            else None
        )
        if execution is None:
            completion_ratio = None
            completed = False
            interruption_count = None
        else:
            completed = execution.completed
            if execution.completion_ratio is not None:
                completion_ratio = execution.completion_ratio
            elif execution.completed:
                completion_ratio = 1.0
            else:
                completion_ratio = None
            interruption_count = execution.interruption_count
        derived.append(
            TaskDerived(
                task_id=plan.task_id,
                started=started,
                start_delay_minutes=start_delay,
                duration_ratio=duration_ratio,
                completion_ratio=completion_ratio,
                completed=completed,
                interruption_count=interruption_count,
                late_start_candidate=(
                    start_delay is not None
                    and start_delay >= config.late_start_candidate_minutes
                ),
                evidence_available=execution is not None,
            )
        )
    return derived


def derive_behavioral_indicators(
    day: DayInput,
    config: DDSRConfig,
    evidence: list[EvidenceItem],
    reflection_present: bool,
) -> BehavioralIndicators:
    derived = derive_task_metrics(day, config)
    by_id = {item.task_id: item for item in derived}

    tasks_planned = len(derived)
    tasks_with_log = len(day.task_executions)
    started_items = [item for item in derived if item.started]
    tasks_started = len(started_items)
    on_time_tasks = sum(
        1
        for item in started_items
        if item.start_delay_minutes is not None and item.start_delay_minutes <= 0
    )
    delays = [
        item.start_delay_minutes
        for item in started_items
        if item.start_delay_minutes is not None
    ]
    initiation = InitiationIndicator(
        tasks_planned=tasks_planned,
        tasks_with_log=tasks_with_log,
        tasks_started=tasks_started,
        on_time_tasks=on_time_tasks,
        mean_start_delay_minutes=(sum(delays) / len(delays)) if delays else None,
        start_rate=(tasks_started / tasks_with_log) if tasks_with_log else None,
        planned_coverage=(tasks_with_log / tasks_planned) if tasks_planned else None,
        evidence_available=tasks_with_log > 0,
    )

    duration_items = [
        item
        for item in started_items
        if item.duration_ratio is not None
    ]
    ratios = [float(item.duration_ratio) for item in duration_items]
    clipped = [min(1.0, max(0.0, ratio)) for ratio in ratios]
    observed_interruptions = [
        execution.interruption_count
        for execution in day.task_executions
        if execution.interruption_count is not None
    ]
    persistence = PersistenceIndicator(
        tasks_started=tasks_started,
        mean_duration_ratio=(sum(ratios) / len(ratios)) if ratios else None,
        total_actual_duration_minutes=sum(
            float(execution.actual_duration_minutes or 0.0)
            for execution in day.task_executions
        ),
        total_estimated_duration_minutes=float(
            sum(plan.estimated_duration_minutes for plan in day.task_plans)
        ),
        interruption_count=(
            sum(observed_interruptions) if observed_interruptions else None
        ),
        continuation_rate=(sum(clipped) / len(clipped)) if clipped else None,
        evidence_available=bool(ratios),
    )

    completion_values = [
        item.completion_ratio for item in derived if item.completion_ratio is not None
    ]
    goal_attainment = GoalAttainmentIndicator(
        value=(sum(completion_values) / len(completion_values))
        if completion_values
        else None,
        tasks_planned=tasks_planned,
        tasks_logged=tasks_with_log,
        tasks_completed=sum(1 for item in derived if item.completed),
        evidence_available=bool(completion_values),
    )

    confirmed = [
        item for item in evidence if item.evidence_type is EvidenceType.PROCRASTINATION
    ]
    candidates = sorted(
        item.task_id for item in by_id.values() if item.late_start_candidate
    )
    procrastination = ProcrastinationEvidenceIndicator(
        confirmed=confirmed,
        candidate_task_ids=candidates,
        late_start_candidate_count=len(candidates),
        evidence_available=reflection_present or bool(candidates),
    )

    return BehavioralIndicators(
        initiation=initiation,
        persistence=persistence,
        goal_attainment=goal_attainment,
        procrastination_evidence=procrastination,
    )


def plan_for(day: DayInput, task_id: str) -> TaskPlan | None:
    for plan in day.task_plans:
        if plan.task_id == task_id:
            return plan
    return None
