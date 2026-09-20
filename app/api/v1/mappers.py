"""Domain -> API schema mappers.

Keeps ORM/domain objects out of the response models without cluttering routes.
"""

from __future__ import annotations

from app.application.dto.insight import InsightReport
from app.application.dto.plan import PlanDetail
from app.domain.models import Plan
from app.schemas.plan import (
    DailyCompletionRead,
    GoalRead,
    InsightRead,
    PlanListItem,
    PlanRead,
)
from app.schemas.task import TaskRead, TaskStandardRead


def task_read(task_with_standards) -> TaskRead:
    schema = TaskRead.model_validate(task_with_standards.task)
    schema.standards = [
        TaskStandardRead.model_validate(standard) for standard in task_with_standards.standards
    ]
    return schema


def plan_read(detail: PlanDetail) -> PlanRead:
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
        tasks=[task_read(item) for item in detail.tasks],
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
    )
