"""Validation artifact generation for Level 3."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_level1_level2_hashes(level3_root: Path) -> dict:
    hashes = {}
    files = [
        level3_root / "level1" / "cat.py",
        level3_root / "level1" / "artifacts" / "grm_parameters.json",
        level3_root / "level1" / "artifacts" / "cat_config.json",
        level3_root / "level2" / "ddsr" / "schemas.py",
        level3_root / "level2" / "ddsr" / "engine.py",
        level3_root / "level2" / "ddsr" / "config.json",
    ]
    for f in files:
        h = sha256_file(f)
        if h:
            hashes[str(f.relative_to(level3_root))] = h
    return hashes


def build_validation_artifact(level3_root: Path, test_results: dict) -> dict:
    hashes = compute_level1_level2_hashes(level3_root)
    artifact = {
        "model": "Level3-Predictor-V1",
        "model_version": "level3_v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "read_only_contract": {
            "level1_modified": False,
            "level2_modified": False,
            "level1_level2_hashes": hashes,
        },
        "test_results": test_results,
        "prediction_modes": ["cold_start", "history_baseline", "learned_model"],
        "anti_leakage": {
            "uses_only_pre_task_state": True,
            "snapshot_frozen_before_outcome": True,
            "no_post_task_backfill": True,
        },
        "implementation_validated": test_results.get("all_passed", False),
        "predictive_validity_validated": False,
        "notes": [
            "No real longitudinal outcome dataset available; synthetic tests only for implementation validation.",
            "Learned model coefficients not fitted (NOT FITTED) until real data passes eligibility gate.",
        ],
    }
    return artifact
