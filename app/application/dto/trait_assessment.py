"""Application DTOs for the Level 1 CAT assessment flow."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TraitAssessmentItemData(BaseModel):
    item_id: str
    text: str
    text_en: str = ""
    domain: str
    domain_name: str = ""
    facet: str = ""
    facet_name: str = ""


class TraitAssessmentDomainProgressData(BaseModel):
    answered: int = 0
    stopped: bool = False
    domain_name: str = ""


class TraitAssessmentProgressData(BaseModel):
    answered: int = 0
    remaining_min: int = 0
    remaining_max: int = 0
    completed_domains: int = 0
    total_domains: int = 5
    current_domain: str | None = None
    domains: dict[str, TraitAssessmentDomainProgressData] = Field(default_factory=dict)


class TraitReassessmentEligibilityData(BaseModel):
    eligible: bool
    cooldown_days: int
    last_completed_at: datetime | None = None
    next_eligible_at: datetime | None = None


class TraitAssessmentData(BaseModel):
    assessment_id: str
    status: str
    next_item: TraitAssessmentItemData | None = None
    progress: TraitAssessmentProgressData
    trait_profile: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


__all__ = [
    "TraitAssessmentData",
    "TraitAssessmentDomainProgressData",
    "TraitAssessmentItemData",
    "TraitAssessmentProgressData",
    "TraitReassessmentEligibilityData",
]