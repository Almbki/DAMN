"""Domain -> API schema mappers.

Keeps ORM/domain objects out of the response models without cluttering routes.
"""

from __future__ import annotations

from datetime import date, time

from app.application.dto.insight import InsightReport
from app.application.dto.plan import PlanChange, PlanDetail
from app.domain.models import Plan
from app.domain.models.enums import TaskStatus
from app.schemas.common import ViolationRead
from app.schemas.plan import (
    DailyCompletionRead,
    DecomposeDay,
    DecomposeDraftTask,
    DecomposeResponse,
    GoalRead,
    InsightRead,
    PlanChangeDayRead,
    PlanChangeRead,
    PlanListItem,
    PlanRead,
    PreviewRead,
    PreviewTaskRead,
)
from app.schemas.task import TaskRead, TaskStandardRead
from app.schemas.user import DataSufficiency

#: The frontend contract exposes priority as 1 (low) .. 3 (high).
_MAX_CONTRACT_PRIORITY = 3


def decompose_response(draft_id: str, preview) -> DecomposeResponse:
    """Group a draft preview into the contract's per-day shape.

    ``source_index`` maps a task back to the 0-based request ``goals[]`` index
    (the graph tracks it as a 1-based `goal_id`).
    """
    grouped: dict[date, list[DecomposeDraftTask]] = {}
    fallback_day = preview.start_date or date.today()
    for task in preview.tasks:
        day = task.scheduled_date or fallback_day
        grouped.setdefault(day, []).append(
            DecomposeDraftTask(
                title=task.title,
                priority=min(int(task.priority), _MAX_CONTRACT_PRIORITY),
                estimated_minutes=max(int(task.estimated_duration), 1),
                start_time=task.start_time,
                end_time=task.end_time,
                source_index=max(0, (task.goal_id or 1) - 1),
            )
        )

    days = [
        DecomposeDay(
            date=day,
            tasks=sorted(tasks, key=lambda item: (item.start_time or time.min, item.title)),
        )
        for day, tasks in sorted(grouped.items())
    ]
    return DecomposeResponse(draft_id=draft_id, days=days)


def plan_change_read(change: PlanChange) -> PlanChangeRead:
    return PlanChangeRead(
        id=change.id,
        trigger_type=change.trigger_type,
        reason=change.reason,
        old_version=change.old_version,
        new_version=change.new_version,
        created_at=change.created_at,
        days=[
            PlanChangeDayRead(
                date=day.date,
                added=day.added,
                moved=day.moved,
                removed=day.removed,
                summary=day.summary,
                task_ids=list(day.task_ids),
            )
            for day in change.days
        ],
    )


def preview_read(payload) -> PreviewRead:
    """Map the agent's PreviewPayload onto the API schema."""
    return PreviewRead(
        thread_id=payload.thread_id,
        title=payload.title,
        start_date=payload.start_date,
        end_date=payload.end_date,
        tasks=[
            PreviewTaskRead(
                order_index=task.order_index,
                title=task.title,
                description=task.description,
                goal_id=task.goal_id,
                subject=task.subject,
                cognitive_load=task.cognitive_load,
                priority=task.priority,
                estimated_duration=task.estimated_duration,
                predicted_duration=task.predicted_duration,
                completion_probability=task.completion_probability,
                recommended_time_slot=task.recommended_time_slot,
                standards=list(task.standards),
                scheduled_date=task.scheduled_date,
                start_time=task.start_time,
                end_time=task.end_time,
                task_kind=task.task_kind,
                series_id=task.series_id,
                series_index=task.series_index,
                occurrence_date=task.occurrence_date,
                target_amount=task.target_amount,
                target_unit=task.target_unit,
                is_flexible=task.is_flexible,
                work_unit_key=task.work_unit_key,
                parent_key=task.parent_key,
                chunk_index=task.chunk_index,
                scheduling_reason=task.scheduling_reason,
                scheduling_detail=task.scheduling_detail,
            )
            for task in payload.tasks
        ],
        confidence=payload.confidence,
        adjustment_count=payload.adjustment_count,
        max_adjustments=payload.max_adjustments,
        can_adjust=payload.can_adjust,
        violations=[ViolationRead.model_validate(v) for v in payload.rule_violations],
    )


def task_read(task_with_standards, group=None) -> TaskRead:
    schema = TaskRead.model_validate(task_with_standards.task)
    schema.standards = [
        TaskStandardRead.model_validate(standard) for standard in task_with_standards.standards
    ]
    members = [task_with_standards.task] if group is None else list(group)
    schema.chunk_count = len(members)
    schema.completed_chunks = sum(
        1 for member in members if member.status == TaskStatus.COMPLETED
    )
    schema.work_unit_completed = bool(members) and all(
        member.status == TaskStatus.COMPLETED for member in members
    )
    return schema


def plan_read(detail: PlanDetail) -> PlanRead:
    # Only tasks with a chunk_index participate in execution-group aggregation;
    # an ordinary parent_task_id/subtask relationship keeps its old semantics.
    chunk_groups: dict[int, list] = {}
    for item in detail.tasks:
        task = item.task
        if task.chunk_index is None:
            continue
        root = task.parent_task_id or task.id
        chunk_groups.setdefault(root, []).append(task)

    def group_for(task):
        if task.chunk_index is None:
            return None
        return chunk_groups.get(task.parent_task_id or task.id)

    return PlanRead(
        id=detail.plan.id,
        user_id=detail.plan.user_id,
        version=detail.plan.version,
        status=detail.plan.status,
        title=detail.plan.title,
        start_date=detail.plan.start_date,
        end_date=detail.plan.end_date,
        parent_plan_id=detail.plan.parent_plan_id,
        confidence=detail.plan.confidence,
        created_at=detail.plan.created_at,
        tasks=[task_read(item, group_for(item.task)) for item in detail.tasks],
        goals=[GoalRead.model_validate(goal) for goal in detail.goals],
    )


def plan_list_item(plan: Plan, *, task_count: int = 0, completed_count: int = 0) -> PlanListItem:
    return PlanListItem(
        id=plan.id or 0,
        version=plan.version,
        status=plan.status,
        title=plan.title,
        start_date=plan.start_date,
        end_date=plan.end_date,
        confidence=plan.confidence,
        created_at=plan.created_at,
        task_count=task_count,
        completed_count=completed_count,
    )


def insight_read(report: InsightReport) -> InsightRead:
    return InsightRead(
        plan_id=report.plan_id,
        total_tasks=report.total_tasks,
        completed_tasks=report.completed_tasks,
        completion_rate=report.completion_rate,
        total_planned_minutes=report.total_planned_minutes,
        total_actual_minutes=report.total_actual_minutes,
        avg_stress=report.avg_stress,
        avg_energy=report.avg_energy,
        high_cognitive_minutes=report.high_cognitive_minutes,
        predicted_vs_actual_ratio=report.predicted_vs_actual_ratio,
        cognitive_load_breakdown=report.cognitive_load_breakdown,
        daily=[DailyCompletionRead(**item.model_dump()) for item in report.daily],
        recommendations=report.recommendations,
        data_sufficiency=(
            DataSufficiency(**report.data_sufficiency)
            if report.data_sufficiency is not None
            else None
        ),
        drivers=report.drivers or None,
    )
