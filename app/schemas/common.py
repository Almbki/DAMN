"""Shared API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error envelope returned by every non-2xx response."""

    code: str = Field(examples=["not_found"])
    message: str = Field(examples=["plan not found"])
    detail: Any | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str
    environment: str


class ViolationRead(BaseModel):
    rule: str
    severity: str
    task_ids: list[int] = Field(default_factory=list)
    message: str = ""
    code: str | None = None
