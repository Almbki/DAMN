"""Versioned DTOs for synthetic demo scenarios.

Synthetic scenarios represent *observations* (tasks/executions/feedback), never
model outputs. The real Level 2/3 runtimes compute state/predictions afterwards.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScenarioResponse(BaseModel):
    item_id: str = Field(min_length=1, max_length=32)
    response: int = Field(ge=1, le=5)


class ScenarioLevel1(BaseModel):
    """Either replay CAT responses or import a validated TraitProfile."""

    responses: list[ScenarioResponse] | None = None
    trait_profile: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _one_source(self) -> ScenarioLevel1:
        if self.responses is None and self.trait_profile is None:
            raise ValueError("level1 needs responses or trait_profile")
        if self.responses is not None and self.trait_profile is not None:
            raise ValueError("level1 accepts responses OR trait_profile, not both")
        return self


class ScenarioTask(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    estimated_duration_minutes: int = Field(ge=1, le=1440)
    actual_duration_minutes: int | None = Field(default=None, ge=0)
    completion_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    completed: bool = False
    interruption_count: int | None = Field(default=None, ge=0)
    difficulty: int | None = Field(default=None, ge=1, le=5)
    planned_start: datetime | None = None
    actual_start: datetime | None = None


class ScenarioFeedback(BaseModel):
    completion_rate: float = Field(ge=0.0, le=1.0)
    stress_level: int | None = Field(default=None, ge=0, le=10)
    energy_level: int | None = Field(default=None, ge=0, le=10)
    free_text: str | None = Field(default=None, max_length=2000)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)


class ScenarioDay(BaseModel):
    date: date
    tasks: list[ScenarioTask] = Field(default_factory=list)
    feedback: ScenarioFeedback | None = None


class SyntheticScenario(BaseModel):
    scenario_version: str = "1.0"
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    level1: ScenarioLevel1 | None = None
    days: list[ScenarioDay] = Field(min_length=1)

    @model_validator(mode="after")
    def _valid_version(self) -> SyntheticScenario:
        if self.scenario_version != "1.0":
            raise ValueError("unsupported scenario_version")
        return self


class SyntheticImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_name: str | None = None
    scenario: SyntheticScenario | None = None

    @model_validator(mode="after")
    def _one_source(self) -> SyntheticImportRequest:
        if bool(self.scenario_name) == bool(self.scenario):
            raise ValueError("provide exactly one of scenario_name or scenario")
        return self


class SyntheticScenarioInfo(BaseModel):
    name: str
    description: str = ""
    scenario_version: str = "1.0"
    days: int = 0
    tasks: int = 0


class SyntheticScenarioList(BaseModel):
    scenarios: list[SyntheticScenarioInfo] = Field(default_factory=list)


class SyntheticImportSummary(BaseModel):
    scenario: str
    days_imported: int
    tasks_imported: int
    executions_imported: int
    feedback_imported: int
    level1_status: str
    level2_status: str
    level2_observed_on: date | None = None
    shadow_runs_before: int = 0
    shadow_runs_after: int = 0
    warnings: list[str] = Field(default_factory=list)


class SyntheticResetSummary(BaseModel):
    deleted: dict[str, int] = Field(default_factory=dict)
    level1_status: str
    level2_status: str
    warnings: list[str] = Field(default_factory=list)


class SyntheticStatus(BaseModel):
    enabled: bool
    synthetic_present: bool
    counts: dict[str, int] = Field(default_factory=dict)


__all__ = [
    "ScenarioDay",
    "ScenarioFeedback",
    "ScenarioLevel1",
    "ScenarioResponse",
    "ScenarioTask",
    "SyntheticImportRequest",
    "SyntheticImportSummary",
    "SyntheticResetSummary",
    "SyntheticScenario",
    "SyntheticScenarioInfo",
    "SyntheticScenarioList",
    "SyntheticStatus",
]