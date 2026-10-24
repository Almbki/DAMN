"""Read-only adapter for the frozen Level 1 TraitProfile V1 contract.

Nothing in this module writes to the profile, re-estimates theta, or changes
GRM/CAT parameters.  The five theta/SE pairs are retained only as versioned
context metadata; DDSR-V1 uses no Trait -> State weights.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .schemas import SourceTraitModel

REQUIRED_DOMAINS: tuple[str, ...] = ("N", "E", "O", "A", "C")


@dataclass(frozen=True)
class TraitContext:
    model: str
    schema_version: str
    calibration_model: str | None
    calibration_version: str | None
    reference_population: str | None
    domains: dict[str, dict[str, float]]

    @classmethod
    def from_profile(cls, profile: Mapping[str, Any]) -> TraitContext:
        if not isinstance(profile, Mapping):
            raise TypeError("TraitProfile must be a mapping")
        domains = profile.get("domains")
        if not isinstance(domains, Mapping):
            raise ValueError("TraitProfile.domains must be a mapping")
        missing = [domain for domain in REQUIRED_DOMAINS if domain not in domains]
        if missing:
            raise ValueError(f"TraitProfile missing domains: {missing}")

        copied: dict[str, dict[str, float]] = {}
        for domain in REQUIRED_DOMAINS:
            entry = domains[domain]
            if not isinstance(entry, Mapping):
                raise ValueError(f"TraitProfile.domains[{domain!r}] must be a mapping")
            try:
                theta = float(entry["theta"])
                se = float(entry["se"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"TraitProfile.domains[{domain!r}] requires numeric theta and se"
                ) from exc
            if se <= 0:
                raise ValueError(f"TraitProfile.domains[{domain!r}].se must be > 0")
            copied[domain] = {"theta": theta, "se": se}

        calibration = profile.get("calibration") or {}
        if not isinstance(calibration, Mapping):
            calibration = {}
        return cls(
            model=str(profile.get("model", "trait_v1")),
            schema_version=str(profile.get("schema_version", "1.0")),
            calibration_model=(
                str(calibration.get("model")) if calibration.get("model") else None
            ),
            calibration_version=(
                str(calibration.get("version")) if calibration.get("version") else None
            ),
            reference_population=(
                str(calibration.get("reference_population"))
                if calibration.get("reference_population")
                else None
            ),
            domains=copy.deepcopy(copied),
        )

    def source_model(self) -> SourceTraitModel:
        return SourceTraitModel(
            model=self.model,
            schema_version=self.schema_version,
            calibration_model=self.calibration_model,
            calibration_version=self.calibration_version,
            reference_population=self.reference_population,
            domains_used=list(REQUIRED_DOMAINS),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "schema_version": self.schema_version,
            "calibration_model": self.calibration_model,
            "calibration_version": self.calibration_version,
            "reference_population": self.reference_population,
            "domains": copy.deepcopy(self.domains),
        }
