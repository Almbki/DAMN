"""Process-wide UserModelRuntime factory.

Loading the real artifacts is cheap but not free; one runtime per process keeps
version/hash metadata stable for every request and worker thread.
"""

from __future__ import annotations

from functools import lru_cache

from app.user_models.runtime import UserModelRuntime


@lru_cache(maxsize=1)
def get_user_model_runtime() -> UserModelRuntime:
    return UserModelRuntime.from_settings()


def reset_user_model_runtime() -> None:
    """Test/settings helper: force the next call to reload artifacts."""
    get_user_model_runtime.cache_clear()


__all__ = ["get_user_model_runtime", "reset_user_model_runtime"]