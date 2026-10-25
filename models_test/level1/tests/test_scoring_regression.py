from __future__ import annotations

import json
from pathlib import Path

import pytest
from scoring import (
    LEGACY_FACET_KEY_TO_CANONICAL,
    load_questions,
    score_canonical,
    score_legacy,
)

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = load_questions(ROOT / "questions.json")
LEGACY_BANK = load_questions(ROOT / "tests" / "fixtures" / "legacy_questions.json")
LEGACY_RESULTS = json.loads(
    (ROOT / "tests" / "fixtures" / "legacy_results.json").read_text(encoding="utf-8")
)
CANONICAL_RESULTS = {
    path.stem.removeprefix("result_"): json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((ROOT / "results").glob("result_*.json"))
}
USER_IDS = sorted(LEGACY_RESULTS)


def old_responses(result: dict) -> dict[int, int]:
    return {int(row["item_id"]): row["response"] for row in result["responses"]}


@pytest.mark.parametrize("name", USER_IDS)
def test_legacy_scoring_exactly_reproduces_original_from_canonical_bank(name: str) -> None:
    original = LEGACY_RESULTS[name]
    responses = old_responses(original)
    legacy = score_legacy(responses, CANONICAL)
    assert legacy["domains"] == original["domains"]
    assert legacy["facets"] == original["facets"]
    assert legacy["responses"] == original["responses"]


@pytest.mark.parametrize("name", USER_IDS)
def test_legacy_scoring_exactly_reproduces_original_from_legacy_bank(name: str) -> None:
    original = LEGACY_RESULTS[name]
    responses = old_responses(original)
    legacy = score_legacy(responses, LEGACY_BANK)
    assert legacy["domains"] == original["domains"]
    assert legacy["facets"] == original["facets"]
    assert legacy["responses"] == original["responses"]


@pytest.mark.parametrize("name", USER_IDS)
def test_raw_responses_are_preserved_under_canonical_item_ids(name: str) -> None:
    original = LEGACY_RESULTS[name]
    canonical = CANONICAL_RESULTS[name]
    by_item_id = {row["item_id"]: row for row in canonical["responses"]}
    assert len(by_item_id) == 120
    for old_row in original["responses"]:
        old_id = int(old_row["item_id"])
        item_id = f"IPIP_{old_id:03d}"
        assert by_item_id[item_id]["response"] == old_row["response"]
        assert by_item_id[item_id]["legacy_id"] == old_id


@pytest.mark.parametrize("name", USER_IDS)
def test_canonical_scoring_is_order_independent(name: str) -> None:
    responses = old_responses(LEGACY_RESULTS[name])
    forward = score_canonical(responses, CANONICAL)
    backward = score_canonical(dict(reversed(list(responses.items()))), CANONICAL)
    assert forward["domains"] == backward["domains"]
    assert forward["facets"] == backward["facets"]
    assert forward["responses"] == backward["responses"]


@pytest.mark.parametrize("name", USER_IDS)
def test_canonical_difference_is_exactly_the_four_metadata_corrections(name: str) -> None:
    original = LEGACY_RESULTS[name]
    canonical = CANONICAL_RESULTS[name]

    domain_deltas = {
        key: canonical["domains"][key]["raw_score"] - row["raw_score"]
        for key, row in original["domains"].items()
        if canonical["domains"][key]["raw_score"] != row["raw_score"]
    }
    assert domain_deltas == {"neuroticism": 18, "extraversion": -6}

    old_facets = {
        LEGACY_FACET_KEY_TO_CANONICAL.get(key, key): row
        for key, row in original["facets"].items()
    }
    assert set(canonical["facets"]) == set(old_facets) | {"self_consciousness"}
    for key, row in old_facets.items():
        expected = row["raw_score"] - 6 if key == "friendliness" else row["raw_score"]
        assert canonical["facets"][key]["raw_score"] == expected
    assert canonical["facets"]["self_consciousness"]["raw_score"] == 18

    changed = {
        key
        for key, row in old_facets.items()
        if canonical["facets"][key]["raw_score"] != row["raw_score"]
    }
    assert changed == {"friendliness"}


@pytest.mark.parametrize("name", USER_IDS)
def test_canonical_domain_score_equals_sum_of_its_facets(name: str) -> None:
    canonical = CANONICAL_RESULTS[name]
    for domain_key, row in canonical["domains"].items():
        total = sum(
            facet["raw_score"]
            for facet in canonical["facets"].values()
            if facet["domain"] == domain_key
        )
        assert total == row["raw_score"]


def test_reverse_flags_follow_official_key_not_legacy_metadata() -> None:
    canonical = score_canonical({"IPIP_016": 1, "IPIP_106": 5}, CANONICAL)
    # IPIP_016 is forward N4; IPIP_106 is reverse N4. 1 + (6-5) = 2.
    assert canonical["facets"]["self_consciousness"]["raw_score"] == 2
    assert canonical["facets"]["friendliness"]["raw_score"] == 0

    legacy = score_legacy({16: 1, 106: 5}, CANONICAL)
    # Legacy: IPIP_016 reverse E1; IPIP_106 forward E1. (6-1) + 5 = 10.
    assert legacy["facets"]["friendliness"]["raw_score"] == 10
    assert "self__consciousness" not in legacy["facets"]


def test_scoring_rejects_unknown_or_out_of_range_responses() -> None:
    with pytest.raises(KeyError):
        score_canonical({"IPIP_999": 3}, CANONICAL)
    with pytest.raises(ValueError):
        score_canonical({"IPIP_001": 0}, CANONICAL)
    with pytest.raises(ValueError):
        score_canonical({"IPIP_001": 6}, CANONICAL)
    with pytest.raises(ValueError):
        score_legacy({1: 0}, CANONICAL)


@pytest.mark.parametrize("name", USER_IDS)
def test_canonical_result_files_keep_the_migration_audit(name: str) -> None:
    migrated = CANONICAL_RESULTS[name]
    assert migrated["schema_version"] == "2.0"
    assert len(migrated["responses"]) == 120
    assert {row["item_id"] for row in migrated["responses"]} == {
        f"IPIP_{i:03d}" for i in range(1, 121)
    }
    migration = migrated["migration"]
    assert migration["raw_responses_preserved"] is True
    assert migration["legacy_scoring_matches_original"] is True
    assert migration["canonical_vs_legacy_domain_diffs"]
    assert migration["canonical_vs_legacy_facet_diffs"]
    assert len(migration["legacy_facets"]) == 29
    assert len(migrated["facets"]) == 30


def test_only_canonical_results_remain_in_results_dir() -> None:
    files = sorted(path.name for path in (ROOT / "results").glob("*.json"))
    assert files == ["result_dxl.json", "result_zjh.json"]
    assert not (ROOT / "results" / "migrated").exists()
