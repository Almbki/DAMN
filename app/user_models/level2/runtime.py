"""Level 2 runtime: replay DDSR-V1 and expose a typed state snapshot.

The state model is pure (``ddsr/engine.py``) and receives already-assembled
``DayInput`` records. The application layer owns the DB -> ``DayInput`` mapping,
so this module never sees SQLAlchemy.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from app.user_models.artifacts import ArtifactBundle, build_artifact
from app.user_models.contracts import (
    DynamicStateSnapshot,
    ModelLevel,
    ModelMetadata,
    ModelStatus,
    StateEstimate,
)
from app.user_models.errors import ModelInputError, ModelUnavailableError
from app.user_models.level2.ddsr.config import DDSRConfig
from app.user_models.level2.ddsr.engine import DDSREngine
from app.user_models.level2.ddsr.schemas import DayInput, DynamicStateProfile
from app.user_models.level2.ddsr.trait_context import TraitContext

MODEL_VERSION = "ddsr_v1"
FEATURE_VERSION = "ddsr_state_v1"

_ARTIFACT_FILES = [
    "config.json",
    "engine.py",
    "state_model.py",
    "schemas.py",
    "task_metrics.py",
]


class Level2Runtime:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parent / "ddsr"
        self._config: DDSRConfig | None = None
        self._bundle: ArtifactBundle | None = None
        self._error: str | None = None
        self._load()

    def _load(self) -> None:
        try:
            self._config = DDSRConfig.from_json(self.root / "config.json")
            self._bundle = build_artifact(
                ModelLevel.LEVEL2,
                self.root,
                _ARTIFACT_FILES,
                version=self._config.config_version,
            )
        except Exception as exc:  # noqa: BLE001 - captured, exposed as unavailable
            self._error = f"{type(exc).__name__}: {exc}"

    @property
    def available(self) -> bool:
        return self._error is None and self._bundle is not None and self._config is not None

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def artifact_files(self) -> list[str]:
        return list(_ARTIFACT_FILES)

    @property
    def config(self) -> DDSRConfig:
        if not self.available:
            raise ModelUnavailableError(self._error or "level2 unavailable")
        assert self._config is not None
        return self._config

    @property
    def metadata(self) -> ModelMetadata:
        if not self.available:
            return ModelMetadata(
                level=ModelLevel.LEVEL2,
                model_version=MODEL_VERSION,
                artifact_version="unknown",
                artifact_hash="",
                feature_version=FEATURE_VERSION,
                status=ModelStatus.UNAVAILABLE,
                degraded_reason=self._error,
            )
        assert self._bundle is not None and self._config is not None
        return ModelMetadata(
            level=ModelLevel.LEVEL2,
            model_version=MODEL_VERSION,
            artifact_version=self._config.config_version,
            artifact_hash=self._bundle.info.sha256,
            feature_version=FEATURE_VERSION,
        )

    # -- replay ------------------------------------------------------------
    def replay(
        self,
        days: list[DayInput],
        trait_profile: dict[str, Any],
    ) -> DynamicStateProfile:
        """Replay days (strictly increasing) and return the latest profile."""
        if not self.available:
            raise ModelUnavailableError(self._error or "level2 unavailable")
        if not days:
            raise ModelInputError("level2 replay requires at least one day")
        try:
            trait = TraitContext.from_profile(trait_profile)
        except Exception as exc:  # noqa: BLE001
            raise ModelInputError(f"invalid trait context: {exc}") from exc
        engine = DDSREngine(self.config)
        profiles = engine.replay(days, trait)
        return profiles[-1]

    def snapshot(self, profile: DynamicStateProfile | dict[str, Any]) -> DynamicStateSnapshot:
        if not self.available:
            raise ModelUnavailableError(self._error or "level2 unavailable")
        raw = (
            profile.model_dump(mode="json")
            if isinstance(profile, DynamicStateProfile)
            else dict(profile)
        )

        def estimate(key: str) -> StateEstimate:
            entry = raw[key]
            return StateEstimate(
                value=float(entry["value"]),
                uncertainty=float(entry["uncertainty"]),
                evidence_availability=str(entry.get("evidence_availability", "none")),
                evidence_count=int(entry.get("evidence_count", 0)),
                conflict=bool(entry.get("conflict", False)),
            )

        observed = raw.get("date")
        try:
            observed_date = date.fromisoformat(str(observed)) if observed else date.today()
        except ValueError as exc:
            raise ModelInputError(f"invalid level2 date: {observed!r}") from exc

        return DynamicStateSnapshot(
            date=observed_date,
            fatigue=estimate("fatigue"),
            stress=estimate("stress"),
            self_efficacy=estimate("self_efficacy"),
            next_day_prior=dict(raw.get("next_day_prior", {}).get("value", {})),
            next_day_uncertainty=dict(raw.get("next_day_prior", {}).get("uncertainty", {})),
            model_version=str(raw.get("model_version", MODEL_VERSION)),
            config_version=str(raw.get("config_version", self.config.config_version)),
            cold_start=bool(raw.get("cold_start", False)),
            gap_days=int(raw.get("gap_days", 0)),
            profile_json=raw,
            metadata=self.metadata,
        )


__all__ = ["Level2Runtime"]