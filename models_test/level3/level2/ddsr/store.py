"""Small JSON history store for longitudinal DDSR-V1 replay."""

from __future__ import annotations

import json
from pathlib import Path

from .schemas import DynamicStateProfile


class JsonHistoryStore:
    """Append-only local JSON history.

    This is intentionally not a database.  It exists so the daily profiles (and
    therefore prediction errors) survive across sessions and can be replayed.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> list[DynamicStateProfile]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("history file must contain a JSON list of profiles")
        return [DynamicStateProfile.model_validate(item) for item in raw]

    def save(self, profiles: list[DynamicStateProfile]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [profile.model_dump(mode="json") for profile in profiles]
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def append(self, profile: DynamicStateProfile) -> list[DynamicStateProfile]:
        profiles = self.load()
        profiles.append(profile)
        self.save(profiles)
        return profiles

    def latest(self) -> DynamicStateProfile | None:
        profiles = self.load()
        return profiles[-1] if profiles else None
