"""User-profile API schemas (环节 1 基础画像 / 环节 2 画像注入)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.schemas.auth import RegisterRequest
from app.schemas.user import UserUpdate

#: The four MBTI dimension keys, in positional order.
MBTI_DIM_KEYS: tuple[str, ...] = ("ie", "sn", "tf", "jp")

#: The 16 valid MBTI type codes (the cartesian product of the four axes).
_VALID_MBTI_TYPES: frozenset[str] = frozenset(
    a + b + c + d
    for a in ("I", "E")
    for b in ("S", "N")
    for c in ("T", "F")
    for d in ("J", "P")
)


class ProfileFields(BaseModel):
    """Shared optional profile fields plus their validators.

    Mixed into the upsert body and the extended register / patch bodies so the
    validation rules stay identical across entry points.
    """

    mbti_type: str | None = None
    mbti_dims: dict[str, float] | None = None
    identity: str | None = Field(default=None, max_length=200)

    @field_validator("mbti_type")
    @classmethod
    def _validate_mbti_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalised = value.strip().upper()
        if normalised not in _VALID_MBTI_TYPES:
            raise ValueError("mbti_type must be one of the 16 valid MBTI types")
        return normalised

    @field_validator("mbti_dims")
    @classmethod
    def _validate_mbti_dims(cls, value: dict[str, float] | None) -> dict[str, float] | None:
        if value is None:
            return None
        unknown = set(value) - set(MBTI_DIM_KEYS)
        if unknown:
            raise ValueError(f"unknown MBTI dimension(s): {sorted(unknown)}")
        for key, weight in value.items():
            if not 0.0 <= float(weight) <= 1.0:
                raise ValueError(f"mbti_dims[{key!r}] must be within [0, 1]")
        return value


class ProfileUpsert(ProfileFields):
    """Body accepted by :meth:`ProfileService.upsert_profile`."""


class ProfileUpdateRequest(UserUpdate, ProfileFields):
    """``PATCH /users/me`` body: user fields plus optional profile fields."""


class RegisterRequestWithProfile(RegisterRequest, ProfileFields):
    """``POST /auth/register`` body with optional profile fields."""


class UserProfileRead(BaseModel):
    mbti_type: str | None = None
    mbti_dims: dict[str, float] | None = None
    identity: str | None = None


class UserStateRead(BaseModel):
    duration_factor: float
    completion_prob: float
    stress_baseline: float
    energy_drain_rate: float
    proactive_score: float
    procrastination_tendency: float
    preferred_time_slots: dict[str, str] = Field(default_factory=dict)
    stress_response: float
    state_energy: float
    state_fatigue: float
    self_efficacy: float
    update_count: int
    degraded: bool


class ProfileResponse(BaseModel):
    profile: UserProfileRead
    state: UserStateRead
