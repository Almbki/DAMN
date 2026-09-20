"""Aggregate v1 router (OpenAPI tags grouped here)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, feedback, insights, plans, tasks, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
api_router.include_router(feedback.router, prefix="/plans", tags=["feedback"])
api_router.include_router(tasks.router, prefix="/plans", tags=["tasks"])
api_router.include_router(insights.router, prefix="/plans", tags=["insights"])
