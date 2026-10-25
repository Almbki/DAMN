from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
MAPPING = json.loads((ARTIFACTS / "item_mapping.json").read_text(encoding="utf-8"))
ISSUES = json.loads((ARTIFACTS / "mapping_issues.json").read_text(encoding="utf-8"))
ITEMS = MAPPING["items"]
LOCAL = json.loads((ROOT / "tests" / "fixtures" / "legacy_questions.json").read_text(encoding="utf-8"))


def test_120_items_with_stable_unique_identity() -> None:
    assert len(ITEMS) == 120
    assert MAPPING["counts"]["official_items"] == 120
    assert MAPPING["counts"]["local_items"] == 120
    assert MAPPING["counts"]["mapped"] == 120
    assert MAPPING["counts"]["missing"] == 0
    assert MAPPING["counts"]["duplicate_local"] == 0
    assert MAPPING["counts"]["duplicate_official"] == 0
    assert MAPPING["counts"]["ambiguous_identity"] == 0

    assert [i["official_order"] for i in ITEMS] == list(range(1, 121))
    assert [i["item_id"] for i in ITEMS] == [f"IPIP_{i:03d}" for i in range(1, 121)]
    assert len({i["item_id"] for i in ITEMS}) == 120
    assert [i["dataset_column"] for i in ITEMS] == [f"I{i}" for i in range(1, 121)]
    assert [i["local_question_id"] for i in ITEMS] == list(range(1, 121))
    assert len({i["local_question_id"] for i in ITEMS}) == 120


def test_local_and_official_sets_are_one_to_one() -> None:
    local_ids = {i["local_question_id"] for i in ITEMS}
    official_ids = {i["official_short_id"] for i in ITEMS}
    assert local_ids == set(range(1, 121))
    assert official_ids == set(range(1, 121))
    assert len(ITEMS) == len(local_ids) == len(official_ids)


def test_domain_and_facet_counts() -> None:
    assert Counter(i["domain"] for i in ITEMS) == {
        "N": 24,
        "E": 24,
        "O": 24,
        "A": 24,
        "C": 24,
    }
    facet_counts = Counter(i["facet_code"] for i in ITEMS)
    assert len(facet_counts) == 30
    assert set(facet_counts.values()) == {4}
    assert "Self-Consciousness" in {i["facet_name"] for i in ITEMS}
    assert len({i["facet"] for i in ITEMS}) == 30


def test_official_metadata_matches_the_item_key_row_for_row() -> None:
    xlrd = pytest.importorskip("xlrd")
    book = xlrd.open_workbook(str(ROOT / "dataset" / "IPIP-NEO-ItemKey.xls"))
    sheet = book.sheet_by_index(0)
    xls_rows = []
    for r in range(1, sheet.nrows):
        full, short, sign, key, facet, item = [sheet.cell_value(r, c) for c in range(6)]
        if short != "":
            xls_rows.append((int(full), int(short), str(sign).strip(), str(key).strip(), str(facet).strip(), str(item).strip()))
    assert len(xls_rows) == 120
    for item, row in zip(ITEMS, xls_rows):
        full, short, sign, key, facet, text_en = row
        assert item["official_short_id"] == short
        assert item["official_full_id"] == full
        assert item["dataset_column"] == f"I{short}"
        assert item["text_en"] == text_en
        assert item["facet_code"] == key
        assert item["facet_name"] == facet
        assert item["keyed_direction"] == ("positive" if sign.startswith("+") else "negative")
        assert item["official_sign"] == sign
        assert item["reverse_scored"] is sign.startswith("-")


def test_reverse_scored_count_matches_official_key() -> None:
    assert sum(1 for i in ITEMS if i["reverse_scored"]) == 55
    assert sum(1 for i in ITEMS if not i["reverse_scored"]) == 65
    for item in ITEMS:
        expected = ("+" if item["keyed_direction"] == "positive" else "-") + item["facet_code"]
        assert item["official_sign"] == expected
        assert item["official_sign"].endswith(item["facet_code"])


def test_local_text_and_legacy_id_are_preserved() -> None:
    for item, local in zip(ITEMS, LOCAL):
        assert item["local_question_id"] == local["id"]
        assert item["local_order"] == local["id"]
        assert item["local_text"] == local["text"]
        assert item["legacy"]["id"] == local["id"]
        assert item["legacy"]["domain_name"] == local["domain"]
        assert item["legacy"]["facet_name"] == local["facet"]
        assert item["legacy"]["reverse"] is local["reverse"]
        expected = hashlib.sha256(local["text"].encode("utf-8")).hexdigest()
        assert item["local_text_sha256"] == expected


def test_translation_verification_is_recorded_for_all_items() -> None:
    for item in ITEMS:
        assert item["translation_verified"] is True
        assert item["local_text"].strip()
        assert item["text_en"].strip()
        assert "Manual side-by-side review" in item["translation_verification"]


def test_metadata_corrections_are_exactly_the_four_known_items() -> None:
    corrected = [i for i in ITEMS if i["metadata_correction"]]
    assert [i["item_id"] for i in corrected] == [
        "IPIP_016",
        "IPIP_046",
        "IPIP_076",
        "IPIP_106",
    ]
    for item in corrected:
        assert item["domain"] == "N"
        assert item["domain_name"] == "Neuroticism"
        assert item["facet_code"] == "N4"
        assert item["facet_name"] == "Self-Consciousness"
        assert item["legacy"]["domain_name"] == "Extraversion"
        assert item["legacy"]["facet_name"] == "Friendliness"
    by_id = {i["item_id"]: i for i in corrected}
    assert by_id["IPIP_016"]["reverse_scored"] is False
    assert by_id["IPIP_046"]["reverse_scored"] is False
    assert by_id["IPIP_076"]["reverse_scored"] is False
    assert by_id["IPIP_106"]["reverse_scored"] is True
    for item_id in ("IPIP_016", "IPIP_046", "IPIP_076"):
        assert by_id[item_id]["legacy"]["reverse"] is True
    assert by_id["IPIP_106"]["legacy"]["reverse"] is False


def test_mapping_issues_are_resolved() -> None:
    assert ISSUES["status"] == "resolved"
    assert ISSUES["identity_status"] == "clean"
    assert ISSUES["canonical_metadata_status"] == "adopted_in_production_bank"
    assert ISSUES["legacy_bank_status"] == "archived_in_tests_fixtures"
    assert ISSUES["blocking_scope"] == "none"
    assert ISSUES["identity_issues"] == 0
    assert ISSUES["metadata_issues"] == 4
    assert len(ISSUES["issues"]) == 4
    for issue in ISSUES["issues"]:
        assert issue["canonical_status"] == "adopted_in_production_bank"
        assert issue["requires_decision"] is False
    summary = ISSUES["summary"]
    assert summary["missing"] == 0
    assert summary["duplicate"] == 0
    assert summary["ambiguous_identity"] == 0
    assert summary["unverified"] == 0
    assert summary["metadata_mismatch"] == 4
    assert summary["naming_normalizations"] == 8
    assert summary["legacy_distinct_facets"] == 29
    assert summary["legacy_friendliness_items"] == 8
    assert "adopted in questions.json" in ISSUES["resolution"]
    assert ISSUES["grm_or_cat_started"] is False


def test_mapping_report_is_clean_and_shows_adopted_corrections() -> None:
    text = (ARTIFACTS / "mapping_report.md").read_text(encoding="utf-8")
    assert "Legacy corrections (adopted)" in text
    assert "adopted: N/N4" in text
    assert "questions.json" in text
    assert "tests/fixtures/legacy_questions.json" in text
    assert "**YES**" not in text
    assert "unresolved canonical mapping" not in text


def test_naming_normalizations_are_non_blocking() -> None:
    normalizations = ISSUES["non_blocking_normalizations"]
    assert len(normalizations) == 8
    assert {n["item_id"] for n in normalizations} == {
        "IPIP_020",
        "IPIP_022",
        "IPIP_050",
        "IPIP_052",
        "IPIP_080",
        "IPIP_082",
        "IPIP_110",
        "IPIP_112",
    }
    for row in normalizations:
        assert row["type"] == "naming_normalization"
        assert row["blocking"] is False
        assert row["normalized_facet"] in {
            "achievement_striving",
            "excitement_seeking",
        }
