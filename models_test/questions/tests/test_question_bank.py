from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
LEGACY = json.loads((ROOT / "tests" / "fixtures" / "legacy_questions.json").read_text(encoding="utf-8"))
CANONICAL = json.loads((ROOT / "questions.json").read_text(encoding="utf-8"))
MAPPING = json.loads((ARTIFACTS / "item_mapping.json").read_text(encoding="utf-8"))


def test_legacy_bank_is_untouched_and_still_has_120_items() -> None:
    digest = hashlib.sha256((ROOT / "tests" / "fixtures" / "legacy_questions.json").read_bytes()).hexdigest()
    assert digest == MAPPING["source_hashes"]["legacy_questions_sha256"]
    assert len(LEGACY) == 120
    assert [q["id"] for q in LEGACY] == list(range(1, 121))
    assert len({q["id"] for q in LEGACY}) == 120


def test_canonical_bank_hash_matches_mapping() -> None:
    digest = hashlib.sha256((ROOT / "questions.json").read_bytes()).hexdigest()
    assert digest == MAPPING["source_hashes"]["canonical_questions_sha256"]


def test_legacy_bank_exposes_the_known_29_facet_problem() -> None:
    facets = Counter(q["facet"] for q in LEGACY)
    assert len(facets) == 29
    assert facets["Friendliness"] == 8
    assert "Self-Consciousness" not in facets
    assert Counter(q["domain"] for q in LEGACY) == {
        "Neuroticism": 20,
        "Extraversion": 28,
        "Openness": 24,
        "Agreeableness": 24,
        "Conscientiousness": 24,
    }
    for qid in (16, 46, 76, 106):
        item = LEGACY[qid - 1]
        assert item["domain"] == "Extraversion"
        assert item["facet"] == "Friendliness"


def test_canonical_bank_is_in_official_order_with_stable_item_ids() -> None:
    assert len(CANONICAL) == 120
    assert [q["item_id"] for q in CANONICAL] == [
        f"IPIP_{i:03d}" for i in range(1, 121)
    ]
    assert [q["official_order"] for q in CANONICAL] == list(range(1, 121))
    assert [q["dataset_column"] for q in CANONICAL] == [
        f"I{i}" for i in range(1, 121)
    ]
    assert len({q["item_id"] for q in CANONICAL}) == 120


def test_canonical_bank_preserves_local_text_and_legacy_identity() -> None:
    for canonical, legacy in zip(CANONICAL, LEGACY):
        assert canonical["local_question_id"] == legacy["id"]
        assert canonical["local_order"] == legacy["id"]
        assert canonical["text"] == legacy["text"]
        assert canonical["legacy"]["id"] == legacy["id"]
        assert canonical["legacy"]["order"] == legacy["id"]
        assert canonical["legacy"]["domain_name"] == legacy["domain"]
        assert canonical["legacy"]["facet_name"] == legacy["facet"]
        assert canonical["legacy"]["reverse"] is legacy["reverse"]


def test_canonical_bank_has_official_domain_and_facet_counts() -> None:
    assert Counter(q["domain"] for q in CANONICAL) == {
        "N": 24,
        "E": 24,
        "O": 24,
        "A": 24,
        "C": 24,
    }
    facet_counts = Counter(q["facet_code"] for q in CANONICAL)
    assert len(facet_counts) == 30
    assert set(facet_counts.values()) == {4}
    assert len({q["facet"] for q in CANONICAL}) == 30
    assert sum(1 for q in CANONICAL if q["reverse_scored"]) == 55
    for q in CANONICAL:
        expected = ("+" if q["keyed_direction"] == "positive" else "-") + q["facet_code"]
        assert q["official_sign"] == expected


def test_canonical_bank_marks_the_four_metadata_corrections() -> None:
    corrected = [q for q in CANONICAL if q["metadata_correction"]]
    assert [q["item_id"] for q in corrected] == [
        "IPIP_016",
        "IPIP_046",
        "IPIP_076",
        "IPIP_106",
    ]
    for q in corrected:
        assert q["domain"] == "N"
        assert q["facet"] == "self_consciousness"
        assert q["legacy"]["domain_name"] == "Extraversion"
        assert q["legacy"]["facet_name"] == "Friendliness"


def test_grm_artifacts_exist_and_no_cat_artifacts_were_created() -> None:
    assert (ARTIFACTS / "grm_parameters.json").exists()
    assert (ARTIFACTS / "grm_diagnostics.json").exists()
    assert (ARTIFACTS / "grm_report.md").exists()
    assert not (ARTIFACTS / "item_parameters.json").exists()
    assert not (ARTIFACTS / "cat_parameters.json").exists()
    assert not (ROOT / "item_parameters.json").exists()
