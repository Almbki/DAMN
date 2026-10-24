"""Level 1 runtime: load the frozen GRM/CAT artifacts and expose trait snapshots.

The model mathematics live in :mod:`app.user_models.level1.cat` (copied verbatim
from the validated model package). This module only owns artifact loading,
profile validation and the typed hand-off to the rest of the system.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.user_models.artifacts import ArtifactBundle, build_artifact, load_json
from app.user_models.contracts import (
    ModelLevel,
    ModelMetadata,
    ModelStatus,
    TraitDomain,
    TraitSnapshot,
)
from app.user_models.errors import ModelInputError, ModelUnavailableError
from app.user_models.level1 import cat

DOMAIN_ORDER: tuple[str, ...] = ("N", "E", "O", "A", "C")
_DOMAIN_NAMES: dict[str, str] = {
    "N": "Neuroticism",
    "E": "Extraversion",
    "O": "Openness",
    "A": "Agreeableness",
    "C": "Conscientiousness",
}
MODEL_VERSION = "trait_v1"
FEATURE_VERSION = "ipip_neo_grm_v1"

_ARTIFACT_FILES = [
    "artifacts/grm_parameters.json",
    "artifacts/cat_config.json",
    "artifacts/item_mapping.json",
]


class TraitDomainProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theta: float
    se: float = Field(gt=0)
    ci95: tuple[float, float] | None = None
    items_answered: int = Field(default=0, ge=0)


class TraitProfileV1(BaseModel):
    """Validated output of the Level 1 CAT assessment."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    model: str = MODEL_VERSION
    instrument: str = "IPIP-NEO-120"
    method: str = "bayesian_cat"
    calibration: dict[str, Any] = Field(default_factory=dict)
    domains: dict[str, TraitDomainProfile]
    assessment: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _all_domains(self) -> TraitProfileV1:
        missing = [domain for domain in DOMAIN_ORDER if domain not in self.domains]
        if missing:
            raise ValueError(f"trait profile missing domains: {missing}")
        return self


class Level1Runtime:
    """Read-only wrapper around the frozen trait model."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parent
        self._params_path = self.root / "artifacts" / "grm_parameters.json"
        self._config_path = self.root / "artifacts" / "cat_config.json"
        self._params: dict[str, Any] = {}
        self._config: cat.CATConfig | None = None
        self._bundle: ArtifactBundle | None = None
        self._error: str | None = None
        self._item_map: dict[str, dict[str, Any]] | None = None
        self._load()

    def _load(self) -> None:
        try:
            params = load_json(self._params_path)
            if params.get("model") != "GRM":
                raise ModelInputError("expected GRM parameters")
            if sorted(params.get("domains", {})) != sorted(DOMAIN_ORDER):
                raise ModelInputError("GRM artifacts must contain N/E/O/A/C")
            self._params = params
            self._config = cat.CATConfig.from_json(self._config_path)
            version = str(params.get("version") or self._config.calibration_version)
            self._bundle = build_artifact(
                ModelLevel.LEVEL1, self.root, _ARTIFACT_FILES, version=version
            )
        except Exception as exc:  # noqa: BLE001 - captured, exposed as unavailable
            self._error = f"{type(exc).__name__}: {exc}"

    @property
    def available(self) -> bool:
        return self._error is None and self._bundle is not None

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def artifact_files(self) -> list[str]:
        return list(_ARTIFACT_FILES)

    @property
    def metadata(self) -> ModelMetadata:
        if not self.available:
            return ModelMetadata(
                level=ModelLevel.LEVEL1,
                model_version=MODEL_VERSION,
                artifact_version="unknown",
                artifact_hash="",
                feature_version=FEATURE_VERSION,
                status=ModelStatus.UNAVAILABLE,
                degraded_reason=self._error,
            )
        assert self._bundle is not None
        return ModelMetadata(
            level=ModelLevel.LEVEL1,
            model_version=MODEL_VERSION,
            artifact_version=self._bundle.info.version,
            artifact_hash=self._bundle.info.sha256,
            feature_version=FEATURE_VERSION,
        )

    # -- assessment --------------------------------------------------------
    def score_responses(self, responses: dict[str, int]) -> TraitProfileV1:
        """Score a completed item -> response map through the frozen CAT."""
        if not self.available:
            raise ModelUnavailableError(self._error or "level1 unavailable")
        session = cat.start_assessment(self._config, self._params_path)
        for item_id, response in responses.items():
            cat.submit_response(session, item_id, int(response))
        return TraitProfileV1.model_validate(cat.get_trait_profile(session))

    def validate_profile(self, profile: dict[str, Any] | TraitProfileV1) -> TraitProfileV1:
        if isinstance(profile, TraitProfileV1):
            return profile
        try:
            return TraitProfileV1.model_validate(profile)
        except Exception as exc:  # noqa: BLE001 - malformed input is a typed error
            raise ModelInputError(f"invalid trait profile: {exc}") from exc

    # -- assessment --------------------------------------------------------
    def new_session(self) -> cat.CATSession:
        """Create a fresh CAT session using the frozen configuration/artifacts."""
        if not self.available:
            raise ModelUnavailableError(self._error or "level1 unavailable")
        return cat.start_assessment(self._config, self._params_path)

    def next_item(self, session: cat.CATSession) -> str | None:
        """Delegate adaptive item selection to the frozen CAT implementation."""
        return cat.get_next_item(session)

    def record_response(
        self, session: cat.CATSession, item_id: str, response: int
    ) -> dict[str, Any]:
        if isinstance(response, bool) or not isinstance(response, int):
            raise ModelInputError("response must be an integer 1..5")
        try:
            return cat.submit_response(session, item_id, response)
        except (KeyError, ValueError) as exc:
            raise ModelInputError(str(exc)) from exc

    def profile_from_session(self, session: cat.CATSession) -> TraitProfileV1:
        try:
            return TraitProfileV1.model_validate(cat.get_trait_profile(session))
        except Exception as exc:  # noqa: BLE001 - malformed model output
            raise ModelInputError(f"invalid CAT profile: {exc}") from exc

    def session_from_state(
        self,
        responses: list[dict[str, Any]],
        rr_index: int,
        unavailable: list[str] | None = None,
    ) -> cat.CATSession:
        """Rebuild a CAT session from the minimal persisted state.

        ``cat.submit_response`` is replayed in administered order so the
        per-domain stop rules reproduce exactly; ``rr_index`` is the only cursor
        that submit_response never touches, so it is restored afterwards.
        """
        if not self.available:
            raise ModelUnavailableError(self._error or "level1 unavailable")
        session = self.new_session()
        for entry in responses:
            try:
                item_id = str(entry["item_id"])
                response = int(entry["response"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ModelInputError("malformed assessment response history") from exc
            self.record_response(session, item_id, response)
        session.rr_index = int(rr_index) % len(cat.DOMAIN_ORDER)
        for item_id in unavailable or []:
            try:
                cat.mark_item_unavailable(session, item_id)
            except KeyError as exc:
                raise ModelInputError(f"unknown unavailable item: {item_id}") from exc
        return session

    def progress(self, session: cat.CATSession) -> dict[str, Any]:
        """User-facing progress counts; never exposes theta/SE/Fisher values."""
        domains: dict[str, dict[str, Any]] = {}
        for domain in cat.DOMAIN_ORDER:
            state = session.states[domain]
            domains[domain] = {
                "answered": int(state.items_answered),
                "stopped": bool(state.stopped),
                "domain_name": _DOMAIN_NAMES[domain],
            }
        answered = sum(state.items_answered for state in session.states.values())
        remaining_min = sum(
            max(0, session.config.min_items - state.items_answered)
            for state in session.states.values()
            if not state.stopped
        )
        remaining_max = sum(
            max(0, session.config.max_items - state.items_answered)
            for state in session.states.values()
            if not state.stopped
        )
        current_domain = next(
            (
                cat.DOMAIN_ORDER[(session.rr_index + offset) % len(cat.DOMAIN_ORDER)]
                for offset in range(len(cat.DOMAIN_ORDER))
                if not session.states[
                    cat.DOMAIN_ORDER[
                        (session.rr_index + offset) % len(cat.DOMAIN_ORDER)
                    ]
                ].stopped
            ),
            None,
        )
        return {
            "answered": int(answered),
            "remaining_min": int(remaining_min),
            "remaining_max": int(remaining_max),
            "completed_domains": sum(1 for state in session.states.values() if state.stopped),
            "total_domains": len(cat.DOMAIN_ORDER),
            "current_domain": current_domain,
            "domains": domains,
        }

    def item_info(self, item_id: str) -> dict[str, Any]:
        """Real item label from the frozen mapping (Chinese primary, English secondary)."""
        self._load_item_map()
        assert self._item_map is not None
        entry = self._item_map.get(item_id)
        if entry is None:
            raise ModelInputError(f"unknown item_id: {item_id}")
        return {
            "item_id": item_id,
            "text": str(entry.get("text") or entry.get("local_text") or ""),
            "text_en": str(entry.get("text_en") or ""),
            "domain": str(entry.get("domain") or ""),
            "domain_name": str(entry.get("domain_name") or _DOMAIN_NAMES.get(
                str(entry.get("domain") or ""), ""
            )),
            "facet": str(entry.get("facet") or ""),
            "facet_name": str(entry.get("facet_name") or ""),
        }

    def item_exists(self, item_id: str) -> bool:
        self._load_item_map()
        return bool(self._item_map and item_id in self._item_map)

    def _load_item_map(self) -> None:
        if self._item_map is not None:
            return
        path = self.root / "artifacts" / "item_mapping.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            items = payload.get("items")
            if not isinstance(items, list):
                raise ValueError("item_mapping.items must be a list")
            self._item_map = {
                str(item["item_id"]): item for item in items if item.get("item_id")
            }
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
            raise ModelUnavailableError(f"unreadable item mapping: {exc}") from exc

    def snapshot(self, profile: dict[str, Any] | TraitProfileV1) -> TraitSnapshot:
        if not self.available:
            raise ModelUnavailableError(self._error or "level1 unavailable")
        validated = self.validate_profile(profile)
        return TraitSnapshot(
            model_version=validated.model or MODEL_VERSION,
            schema_version=validated.schema_version,
            domains={
                domain: TraitDomain(
                    theta=entry.theta,
                    se=entry.se,
                    ci95=tuple(entry.ci95) if entry.ci95 else None,
                    items_answered=entry.items_answered,
                )
                for domain, entry in validated.domains.items()
            },
            calibration=dict(validated.calibration),
            metadata=self.metadata,
        )


__all__ = ["DOMAIN_ORDER", "Level1Runtime", "TraitDomainProfile", "TraitProfileV1"]