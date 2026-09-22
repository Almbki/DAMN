"""用户画像 (MBTI-based user profile) domain engine.

Pure domain package per ``docs/design/notes/Prompts/画像.md`` and
``docs/fin/核心闭环.md`` 环节 1. No FastAPI / SQLAlchemy imports - stdlib only.
"""

from app.domain.profile.engine import (
    init_state,
    predict_completion,
    predict_duration,
    profile_prompt_json,
    replan_decision,
    resolve_mbti_type,
    should_prompt,
    update_state,
)
from app.domain.profile.mbti_templates import (
    DIMENSION_LETTERS,
    MBTI_DIMENSIONS,
    MBTI_TEMPLATES,
    TYPE_MULTIPLIER,
)
from app.domain.profile.models import (
    CompletionEstimate,
    DurationEstimate,
    ReplanDecision,
    UserProfileData,
    UserStateData,
)

__all__ = [
    "CompletionEstimate",
    "DIMENSION_LETTERS",
    "DurationEstimate",
    "MBTI_DIMENSIONS",
    "MBTI_TEMPLATES",
    "ReplanDecision",
    "TYPE_MULTIPLIER",
    "UserProfileData",
    "UserStateData",
    "init_state",
    "predict_completion",
    "predict_duration",
    "profile_prompt_json",
    "replan_decision",
    "resolve_mbti_type",
    "should_prompt",
    "update_state",
]
