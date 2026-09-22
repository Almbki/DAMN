"""Effective scheduling preferences.

One source of truth for the layering:

```
defaults  <  users.profile (legacy keys)  <  users.scheduling_preferences (explicit)
```

The dedicated column was added for the frontend contract
(`GET/PUT /users/me/preferences`) so a wholesale `profile` update can no longer
wipe the scheduling settings. `profile` is still read as a fallback so existing
users keep whatever they had stored there.
"""

from __future__ import annotations

from typing import Any

#: The four caps the contract exposes, with their defaults.
NUMERIC_DEFAULTS: dict[str, int] = {
    "available_minutes_per_day": 480,
    "daily_limit_minutes": 300,
    "buffer_minutes": 15,
    "high_cognitive_max_per_day": 2,
}

#: UI-only sleep window ("HH:MM"); the scheduler does not consume these yet.
SLEEP_KEYS: tuple[str, str] = ("sleep_start", "sleep_end")


def effective_scheduling_preferences(
    profile: dict[str, Any] | None, stored: dict[str, Any] | None
) -> dict[str, Any]:
    """Resolve the preference values actually in effect for a user."""
    profile = profile or {}
    stored = stored or {}

    resolved: dict[str, Any] = {}
    for key, default in NUMERIC_DEFAULTS.items():
        value = stored.get(key)
        if value is None:
            value = profile.get(key)
        resolved[key] = int(value) if value is not None else default

    for key in SLEEP_KEYS:
        value = stored.get(key) or profile.get(key)
        resolved[key] = str(value) if value else None
    return resolved


__all__ = ["NUMERIC_DEFAULTS", "SLEEP_KEYS", "effective_scheduling_preferences"]
