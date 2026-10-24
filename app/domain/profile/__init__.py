"""Profile data contracts (no model maths).

The old EWMA/MBTI engine was a second, competing source of dynamic state. It has
been removed; traits come from ``app.user_models.level1`` and dynamic state from
``app.user_models.level2``. This package now only holds the persistence-facing
dataclasses used by repositories and the compatibility API.
"""

from app.domain.profile.models import (
    UserProfileData,
    UserStateData,
)

__all__ = [
    "UserProfileData",
    "UserStateData",
]