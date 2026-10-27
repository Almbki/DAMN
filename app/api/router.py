"""Aggregate v1 router (OpenAPI tags grouped here)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    dev,
    feedback,
    goal_sets,
    goals,
    insights,
    plans,
    schedules,
    tasks,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
api_router.include_router(feedback.router, prefix="/plans", tags=["feedback"])
api_router.include_router(feedback.obligations_router, prefix="/feedback", tags=["feedback"])
api_router.include_router(tasks.router, prefix="/plans", tags=["tasks"])
api_router.include_router(insights.router, prefix="/plans", tags=["insights"])
api_router.include_router(goals.router, prefix="/goals", tags=["goals"])
api_router.include_router(goal_sets.router, prefix="/goal-sets", tags=["goal-sets"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(dev.router, prefix="/dev", tags=["dev"])
