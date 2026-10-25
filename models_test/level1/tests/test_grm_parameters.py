from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
PARAMETERS = json.loads((ARTIFACTS / "grm_parameters.json").read_text(encoding="utf-8"))
DIAGNOSTICS = json.loads((ARTIFACTS / "grm_diagnostics.json").read_text(encoding="utf-8"))
MAPPING = json.loads((ARTIFACTS / "item_mapping.json").read_text(encoding="utf-8"))
ITEM_META = {item["item_id"]: item for item in MAPPING["items"]}


def test_grm_parameter_counts() -> None:
    assert PARAMETERS["model"] == "GRM"
    assert PARAMETERS["version"] == "grm_v1"
    assert PARAMETERS["parameter_count"] == 600
    assert set(PARAMETERS["domains"]) == {"N", "E", "O", "A", "C"}
    all_ids = []
    for domain, block in PARAMETERS["domains"].items():
        assert block["n_items"] == 24
        assert len(block["items"]) == 24
        for item_id, item in block["items"].items():
            all_ids.append(item_id)
            assert item["domain"] == domain
            assert item_id in ITEM_META
            assert item["facet"] == ITEM_META[item_id]["facet_name"]
    assert len(all_ids) == 120
    assert len(set(all_ids)) == 120


def test_grm_parameters_are_valid_and_ordered() -> None:
    for block in PARAMETERS["domains"].values():
        for item in block["items"].values():
            assert item["a"] > 0
            thresholds = item["thresholds"]
            assert len(thresholds) == 4
            assert thresholds[0] < thresholds[1] < thresholds[2] < thresholds[3]


def test_grm_diagnostics_core_counts() -> None:
    assert DIAGNOSTICS["converged"] is True
    assert DIAGNOSTICS["respondents"] == 619_150
    assert DIAGNOSTICS["items"] == 120
    assert DIAGNOSTICS["parameter_count"] == 600
    assert DIAGNOSTICS["invalid_parameters"] == 0
    assert DIAGNOSTICS["flagged_item_count"] == len(DIAGNOSTICS["flagged_items"])
    assert set(DIAGNOSTICS["domain_dimensionality"]) == {"N", "E", "O", "A", "C"}


def test_grm_qc_and_item_distribution() -> None:
    qc = DIAGNOSTICS["qc"]
    assert qc["missing_total"] == 367_593
    assert qc["response_min"] == 1
    assert qc["response_max"] == 5
    assert qc["reverse_scoring_applied"] is False
    assert len(qc["item_distribution"]) == 120
    for row in qc["item_distribution"].values():
        total = row["p1"] + row["p2"] + row["p3"] + row["p4"] + row["p5"]
        assert abs(total - 1.0) < 1e-5


def test_flags_do_not_remove_items() -> None:
    flagged_ids = {row["item_id"] for row in DIAGNOSTICS["flagged_items"]}
    parameter_ids = {
        item_id
        for block in PARAMETERS["domains"].values()
        for item_id in block["items"]
    }
    assert flagged_ids <= parameter_ids
    assert len(parameter_ids) == 120
