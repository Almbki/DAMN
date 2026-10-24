from __future__ import annotations

import json
import math
from pathlib import Path

import cat
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"

PARAMS = cat.load_grm_parameters()
ITEM_DOMAIN = {
    item_id: domain
    for domain, block in PARAMS["domains"].items()
    for item_id in block["items"]
}


def deterministic_response(item_id: str, theta: float) -> int:
    block = PARAMS["domains"][ITEM_DOMAIN[item_id]]["items"][item_id]
    probs = cat.category_probabilities(
        np.array([theta]), block["a"], block["thresholds"]
    )[0]
    u = ((sum(ord(c) for c in item_id) % 1000) + 0.5) / 1000.0
    return int(np.searchsorted(np.cumsum(probs), u) + 1)


def run_to_completion(session: cat.CATSession, theta: float = 0.0) -> dict:
    while True:
        item_id = cat.get_next_item(session)
        if item_id is None:
            break
        cat.submit_response(session, item_id, deterministic_response(item_id, theta))
    return cat.get_trait_profile(session)


def test_category_probabilities_sum_to_one_and_are_valid() -> None:
    for block in PARAMS["domains"].values():
        for item in block["items"].values():
            probs = cat.category_probabilities(np.array([-4.0, -1.0, 0.0, 1.0, 4.0]), item["a"], item["thresholds"])
            assert probs.shape == (5, 5)
            assert np.all(np.isfinite(probs))
            assert np.all(probs >= 0.0)
            assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-10)


def test_eap_and_se_are_finite_after_a_response() -> None:
    session = cat.start_assessment(cat.CATConfig(min_items=4, max_items=12, target_se=0.35))
    item_id = cat.get_next_item(session)
    assert item_id is not None
    cat.submit_response(session, item_id, 3)
    state = cat._find_state(session, item_id)
    assert math.isfinite(state.theta)
    assert math.isfinite(state.se)
    assert state.se > 0.0
    assert len(state.ci95) == 2
    assert state.ci95[0] <= state.ci95[1]


def test_answered_items_cannot_be_selected_again() -> None:
    session = cat.start_assessment(cat.CATConfig(min_items=2, max_items=8, target_se=10.0))
    seen = []
    while True:
        item_id = cat.get_next_item(session)
        if item_id is None:
            break
        assert item_id not in seen
        seen.append(item_id)
        cat.submit_response(session, item_id, 3)
        if len(seen) >= 8:
            break
    assert len(seen) == len(set(seen))


def test_item_selection_stays_inside_the_current_domain() -> None:
    session = cat.start_assessment(cat.CATConfig(min_items=2, max_items=8, target_se=10.0))
    while True:
        item_id = cat.get_next_item(session)
        if item_id is None:
            break
        assert ITEM_DOMAIN[item_id] == session.last_domain
        cat.submit_response(session, item_id, 3)
        if session.completed:
            break


def test_target_se_stopping_rule() -> None:
    session = cat.start_assessment(cat.CATConfig(min_items=4, max_items=12, target_se=10.0))
    state = session.states["N"]
    for item_id in state.items[:4]:
        cat.submit_response(session, item_id, 3)
    assert state.items_answered == 4
    assert state.stopped is True
    assert state.stop_reason == "target_se"


def test_max_items_stopping_rule() -> None:
    session = cat.start_assessment(cat.CATConfig(min_items=4, max_items=4, target_se=0.001))
    state = session.states["N"]
    for item_id in state.items[:4]:
        cat.submit_response(session, item_id, 3)
    assert state.items_answered == 4
    assert state.stopped is True
    assert state.stop_reason == "max_items"


def test_all_five_domains_complete() -> None:
    session = cat.start_assessment(cat.CATConfig(min_items=2, max_items=3, target_se=10.0))
    profile = run_to_completion(session, theta=0.0)
    assert profile["assessment"]["completed"] is True
    for domain in cat.DOMAIN_ORDER:
        assert profile["domains"][domain]["items_answered"] >= 2


def test_trait_profile_schema_is_valid() -> None:
    session = cat.start_assessment(cat.CATConfig(min_items=2, max_items=3, target_se=10.0))
    profile = run_to_completion(session, theta=0.0)
    assert profile["schema_version"] == "1.0"
    assert profile["model"] == "trait_v1"
    assert profile["instrument"] == "IPIP-NEO-120"
    assert profile["method"] == "bayesian_cat"
    assert profile["calibration"]["model"] == "samejima_grm"
    assert profile["calibration"]["version"] == "grm_v1"
    assert set(profile["domains"]) == set(cat.DOMAIN_ORDER)
    for row in profile["domains"].values():
        assert set(row) == {"theta", "se", "ci95", "items_answered"}
        assert math.isfinite(row["theta"])
        assert row["se"] > 0
        assert len(row["ci95"]) == 2
        assert row["ci95"][0] <= row["ci95"][1]
    assert profile["assessment"]["total_items_answered"] == sum(
        row["items_answered"] for row in profile["domains"].values()
    )
    assert "mbti" not in profile
    assert "labels" not in profile
    assert "facets" not in profile


def test_unavailable_item_is_skipped() -> None:
    session = cat.start_assessment(cat.CATConfig(min_items=2, max_items=8, target_se=10.0))
    n_items = list(session.states["N"].items)
    blocked = n_items[0]
    cat.mark_item_unavailable(session, blocked)
    selected = []
    while True:
        item_id = cat.get_next_item(session)
        if item_id is None:
            break
        selected.append(item_id)
        cat.submit_response(session, item_id, 3)
        if len(selected) >= 10:
            break
    assert blocked not in selected


def test_first_item_has_max_information_in_first_domain() -> None:
    session = cat.start_assessment(cat.CATConfig(min_items=2, max_items=3, target_se=10.0))
    first = cat.get_next_item(session)
    assert first is not None
    assert session.last_domain == "N"
    n_items = session.states["N"].params
    infos = {
        item_id: cat.item_information(0.0, block["a"], block["thresholds"])
        for item_id, block in n_items.items()
    }
    assert infos[first] == pytest.approx(max(infos.values()), abs=1e-12)


def test_cat_config_artifact_is_valid() -> None:
    config = json.loads((ARTIFACTS / "cat_config.json").read_text(encoding="utf-8"))
    assert config["model"] == "trait_v1"
    assert config["estimator"] == "EAP"
    assert config["prior"] == {"distribution": "normal", "mean": 0.0, "sd": 1.0}
    assert config["item_selection"] == "max_fisher_information_at_eap"
    assert config["min_items"] == 4
    assert config["max_items"] == 12
    assert config["target_se"] == 0.35
    assert config["ci_method"] == "posterior_quantile"
    assert config["calibration"] == {
        "model": "samejima_grm",
        "version": "grm_v1",
        "reference_population": "Johnson_IPIP_NEO_120",
    }
    assert config["domain_order"] == ["N", "E", "O", "A", "C"]
    assert config["scheduling"] == "round_robin"


def test_cat_validation_artifact_is_valid() -> None:
    validation = json.loads((ARTIFACTS / "cat_validation.json").read_text(encoding="utf-8"))
    assert validation["simulation"]["tested_respondents"] == 619_150
    assert validation["selected_config"]["target_se"] == 0.35
    assert {row["target_se"] for row in validation["compared_target_se"]} == {0.30, 0.35, 0.40}
    assert set(validation["domains"]) == set(cat.DOMAIN_ORDER)
    for domain in cat.DOMAIN_ORDER:
        row = validation["domains"][domain]
        assert row["n"] == 619_150
        assert row["pearson"] > 0.9
        assert row["mae"] > 0
        assert row["rmse"] >= row["mae"]
        assert row["mean_items"] >= 4
        assert row["mean_items"] <= 12
        assert len(row["regions"]) == 5
    assert validation["extreme_theta_warning"] is None or isinstance(
        validation["extreme_theta_warning"], str
    )
