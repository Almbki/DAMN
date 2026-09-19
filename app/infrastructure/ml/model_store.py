"""Model store implementations for serialising/deserialising ML artifacts."""

from __future__ import annotations

import os
import pickle
from typing import Protocol


class ModelStore(Protocol):
    """Persistence interface for trained model artifacts."""

    def load(self, name: str) -> object | None:
        """Return the stored model or ``None`` when it does not exist."""
        ...

    def save(self, name: str, model: object) -> None:
        """Persist ``model`` under ``name`` for later ``load``."""
        ...


class InMemoryModelStore:
    """Process-local dict store - volatile, useful for tests and short runs."""

    def __init__(self) -> None:
        self._models: dict[str, object] = {}

    def load(self, name: str) -> object | None:
        return self._models.get(name)

    def save(self, name: str, model: object) -> None:
        self._models[name] = model


class FileModelStore:
    """Pickle-based on-disk store inside ``directory``.

    PLACEHOLDER - no trained models exist yet. Intended for local experiments
    only; swap for a real artifact service once the ML layer starts producing
    trained models.
    """

    def __init__(self, directory: str) -> None:
        self._directory = directory

    def _path(self, name: str) -> str:
        return os.path.join(self._directory, f"{name}.pkl")

    def load(self, name: str) -> object | None:
        path = self._path(name)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as handle:
            return pickle.load(handle)

    def save(self, name: str, model: object) -> None:
        os.makedirs(self._directory, exist_ok=True)
        with open(self._path(name), "wb") as handle:
            pickle.dump(model, handle)