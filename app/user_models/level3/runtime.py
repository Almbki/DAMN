"""Level 3 runtime: Progressive Execution Predictor V1.

Prediction only. In this version the predictor is only ever called by
:class:`app.user_models.shadow.Level3ShadowRunner`; it is not a control input.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

from app.user_models.artifacts import ArtifactBundle, build_artifact
from app.user_models.contracts import Level3Prediction, ModelLevel, ModelMetadata, ModelStatus
from app.user_models.errors import ModelUnavailableError
from app.user_models.level3 import config as level3_config
from app.user_models.level3 import predictor as level3_predictor
from app.user_models.level3 import schemas as level3_schemas

FEATURE_VERSION = "level3_features_v1"

_ARTIFACT_FILES = [
    "config.py",
    "features.py",
    "predictor.py",
    "schemas.py",
    "validation.py",
]


class Level3Runtime:
    def __init__(self, root: Path | None = None, *, predictor: Any | None = None) -> None:
        self.root = root or Path(__file__).resolve().parent
        self._config: level3_config.Level3Config | None = None
        self._predictor: Any | None = predictor
        self._bundle: ArtifactBundle | None = None
        self._error: str | None = None
        self._load()

    def _load(self) -> None:
        try:
            self._config = level3_config.Level3Config()
            self._bundle = build_artifact(
                ModelLevel.LEVEL3,
                self.root,
                _ARTIFACT_FILES,
                version=self._config.model_version,
            )
            if self._predictor is None:
                self._predictor = level3_predictor.Level3Predictor(self._config)
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
    def config(self) -> level3_config.Level3Config:
        if not self.available:
            raise ModelUnavailableError(self._error or "level3 unavailable")
        assert self._config is not None
        return self._config

    @property
    def metadata(self) -> ModelMetadata:
        if not self.available:
            return ModelMetadata(
                level=ModelLevel.LEVEL3,
                model_version="level3_v1",
                artifact_version="unknown",
                artifact_hash="",
                feature_version=FEATURE_VERSION,
                status=ModelStatus.UNAVAILABLE,
                degraded_reason=self._error,
            )
        assert self._bundle is not None and self._config is not None
        return ModelMetadata(
            level=ModelLevel.LEVEL3,
            model_version=self._config.model_version,
            artifact_version=self._config.config_version,
            artifact_hash=self._bundle.info.sha256,
            feature_version=FEATURE_VERSION,
            status=ModelStatus.NOT_FITTED,
            degraded_reason="learned_model_not_fitted",
        )

    def predict(self, inp: level3_schemas.Level3PredictionInput) -> Level3Prediction:
        if not self.available:
            raise ModelUnavailableError(self._error or "level3 unavailable")
        assert self._predictor is not None
        result = self._predictor.predict(inp)
        support = result.data_support
        data_support = dataclasses.asdict(support) if support is not None else {}
        return Level3Prediction(
            completion_probability=result.completion_probability,
            completion_uncertainty=result.completion_uncertainty,
            completion_interval=result.completion_interval,
            predicted_duration_minutes=result.predicted_duration_minutes,
            duration_uncertainty=result.duration_uncertainty,
            duration_interval=result.duration_interval,
            prediction_mode=str(result.prediction_mode),
            prediction_status=str(result.prediction_status),
            model_version=result.model_version,
            feature_snapshot_id=result.feature_snapshot_id,
            data_support=data_support,
            source_level1_version=result.source_level1_version,
            source_level2_version=result.source_level2_version,
            reasons=tuple(result.reasons),
            degraded=result.prediction_status != "ok",
        )


__all__ = ["Level3Runtime"]