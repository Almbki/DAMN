from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ddsr.config import DDSRConfig  # noqa: E402
from ddsr.trait_context import TraitContext  # noqa: E402
from helpers import trait_profile  # noqa: E402


@pytest.fixture
def config() -> DDSRConfig:
    return DDSRConfig()


@pytest.fixture
def trait() -> TraitContext:
    return TraitContext.from_profile(trait_profile())


@pytest.fixture
def trait_dict() -> dict:
    return trait_profile()
