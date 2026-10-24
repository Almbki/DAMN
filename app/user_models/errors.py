"""Errors raised by the user-model runtime.

They are deliberately narrow: callers degrade (record + continue) rather than
letting a missing model break planning.
"""

from __future__ import annotations


class UserModelError(Exception):
    """Base class for user-model failures."""


class ArtifactLoadError(UserModelError):
    """An artifact is missing, unreadable or internally inconsistent."""


class ModelInputError(UserModelError):
    """A caller supplied malformed model input."""


class ModelUnavailableError(UserModelError):
    """A model cannot be used right now (not loaded / no validated profile)."""


__all__ = [
    "ArtifactLoadError",
    "ModelInputError",
    "ModelUnavailableError",
    "UserModelError",
]