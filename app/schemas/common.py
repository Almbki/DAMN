"""Shared API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
    #: Rule violations arrive as ``app.domain.rules.base.RuleViolation`` (a
    #: Pydantic model), not as a dict; without this, ``model_validate`` raises
    #: "Input should be a valid dictionary or instance of ViolationRead" whenever
    #: a plan actually violates a hard rule.
    model_config = ConfigDict(from_attributes=True)

    rule: str
    severity: str
    task_ids: list[int] = Field(default_factory=list)
    message: str = ""
    code: str | None = None
