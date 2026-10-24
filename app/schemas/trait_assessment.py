"""Request schemas for the Level 1 CAT assessment."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TraitAssessmentAnswerRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=32)
    response: int = Field(ge=1, le=5, description="Raw 1..5 Likert response")


__all__ = ["TraitAssessmentAnswerRequest"]