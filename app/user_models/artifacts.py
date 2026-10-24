"""Artifact loading, hashing and version extraction.

Artifacts are bundled with the package (``app/user_models/**/artifacts``).
Hashing the *code + config* that defines a layer gives every prediction a
reproducible ``artifact_hash`` even when the model has no serialized weights.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.user_models.contracts import ArtifactInfo, ModelLevel
from app.user_models.errors import ArtifactLoadError


def sha256_file(path: Path) -> str:
    if not path.exists():
        raise ArtifactLoadError(f"artifact not found: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ArtifactLoadError(f"artifact not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactLoadError(f"unreadable artifact {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ArtifactLoadError(f"artifact {path} must contain a JSON object")
    return data


@dataclass(frozen=True)
class ArtifactBundle:
    """One layer's artifact identity."""

    info: ArtifactInfo
    files: dict[str, str]


def build_artifact(
    level: ModelLevel,
    root: Path,
    file_names: list[str],
    *,
    version: str,
) -> ArtifactBundle:
    """Hash ``file_names`` (relative to ``root``) into one stable identity."""
    hashes: dict[str, str] = {}
    for name in file_names:
        path = root / name
        hashes[name] = sha256_file(path)
    combined = hashlib.sha256(
        "\n".join(f"{name}:{hashes[name]}" for name in sorted(hashes)).encode("utf-8")
    ).hexdigest()
    return ArtifactBundle(
        info=ArtifactInfo(
            path=f"{level.value}:{root.as_posix()}",
            sha256=combined,
            version=version,
        ),
        files=hashes,
    )


__all__ = [
    "ArtifactBundle",
    "build_artifact",
    "load_json",
    "sha256_file",
    "sha256_json",
]