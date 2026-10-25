"""IPIP-NEO-120 scoring on stable item identities.

The canonical path is item_id based:

    question bank -> official order -> item_id -> response
                  -> reverse scoring -> facet -> domain

No array index is used as identity.

Two modes are supported:

* ``canonical``: official ItemKey domain/facet/direction metadata.
* ``legacy``: byte-for-byte reproduction of the pre-migration eval.py scoring,
  retained only for migration regression.  Do not use it for new data, GRM
  calibration, or CAT.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

DOMAIN_NAMES = {
    "N": "Neuroticism",
    "E": "Extraversion",
    "O": "Openness",
    "A": "Agreeableness",
    "C": "Conscientiousness",
}
DOMAIN_NAME_TO_CODE = {v: k for k, v in DOMAIN_NAMES.items()}

# Legacy eval.py emitted double underscores for facets whose official names
# contain a hyphen or a space before the second capital.  Keep the mapping
# explicit so canonical keys stay clean and audit-friendly.
LEGACY_FACET_KEY_TO_CANONICAL = {
    "self__efficacy": "self_efficacy",
    "artistic__interests": "artistic_interests",
    "activity__level": "activity_level",
    "achievement__striving": "achievement_striving",
    "excitement__seeking": "excitement_seeking",
    "self__discipline": "self_discipline",
}


def load_questions(path: str | Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "items" in data:
        data = data["items"]
    if not isinstance(data, list):
        raise ValueError("question bank must be a JSON array (or an object with an 'items' array)")
    if not data:
        raise ValueError("question bank is empty")
    return data


def legacy_snake(text: str) -> str:
    """Reproduce the legacy eval.py to_snake_case exactly."""
    text = text.replace("-", "_").replace(" ", "_")
    return re.sub(r"(?<!^)(?=[A-Z])", "_", text).lower()


def canonical_slug(text: str) -> str:
    text = text.lower().replace("-", " ").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _validate_response(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not a valid response")
    try:
        response = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"response must be an integer 1..5, got {value!r}") from exc
    if response < 1 or response > 5:
        raise ValueError(f"response must be in 1..5, got {response}")
    return response


def _reverse(response: int) -> int:
    return 6 - response


def _domain_level(score: int) -> str:
    return "high" if score >= 84 else ("low" if score <= 60 else "average")


def _facet_level(score: int) -> str:
    return "high" if score >= 15 else ("low" if score <= 9 else "average")


def _canonical_lookup(questions: list[dict]) -> tuple[dict[str, dict], dict[int, dict]]:
    by_item_id: dict[str, dict] = {}
    by_legacy_id: dict[int, dict] = {}
    for q in questions:
        item_id = q.get("item_id")
        if not item_id:
            raise ValueError("canonical mode requires every question to have item_id")
        if item_id in by_item_id:
            raise ValueError(f"duplicate item_id in question bank: {item_id}")
        by_item_id[item_id] = q
        legacy = q.get("legacy") or {}
        legacy_id = legacy.get("id", q.get("id"))
        if legacy_id is not None:
            if int(legacy_id) in by_legacy_id:
                raise ValueError(f"duplicate legacy id in question bank: {legacy_id}")
            by_legacy_id[int(legacy_id)] = q
    return by_item_id, by_legacy_id


def _resolve_canonical(
    key: Any, by_item_id: Mapping[str, dict], by_legacy_id: Mapping[int, dict]
) -> dict:
    if isinstance(key, str) and key in by_item_id:
        return by_item_id[key]
    try:
        legacy_id = int(key)
    except (TypeError, ValueError):
        legacy_id = None
    if legacy_id is not None and legacy_id in by_legacy_id:
        return by_legacy_id[legacy_id]
    raise KeyError(f"unknown item identity: {key!r}")


def score_canonical(
    responses: Mapping[Any, Any], questions: list[dict]
) -> dict:
    """Official canonical scoring.  Responses may use item_id or legacy int ids."""
    by_item_id, by_legacy_id = _canonical_lookup(questions)

    answered: dict[str, tuple[dict, int]] = {}
    for key, value in responses.items():
        q = _resolve_canonical(key, by_item_id, by_legacy_id)
        item_id = q["item_id"]
        if item_id in answered:
            raise ValueError(f"duplicate response for item {item_id}")
        answered[item_id] = (q, _validate_response(value))

    facet_scores: dict[str, int] = defaultdict(int)
    domain_scores: dict[str, int] = defaultdict(int)
    response_rows: list[dict] = []

    for item_id, (q, raw) in answered.items():
        score = _reverse(raw) if q.get("reverse_scored") else raw
        domain_code = q["domain"]
        domain_name = q.get("domain_name") or DOMAIN_NAMES[domain_code]
        domain_key = domain_name.lower()
        facet_slug = q.get("facet") or canonical_slug(q["facet_name"])
        facet_scores[facet_slug] += score
        domain_scores[domain_key] += score
        response_rows.append(
            {
                "item_id": item_id,
                "legacy_id": (q.get("legacy") or {}).get("id", q.get("id")),
                "response": raw,
            }
        )

    response_rows.sort(key=lambda row: next(
        i["official_order"] for i in questions if i["item_id"] == row["item_id"]
    ))

    domains: dict[str, dict] = {}
    for q in questions:
        domain_code = q["domain"]
        domain_name = q.get("domain_name") or DOMAIN_NAMES[domain_code]
        domain_key = domain_name.lower()
        if domain_key in domains:
            continue
        score = domain_scores.get(domain_key, 0)
        domains[domain_key] = {
            "domain_code": domain_code,
            "domain_name": domain_name,
            "raw_score": score,
            "standardized_score": None,
            "percentile": None,
            "level": _domain_level(score),
        }

    facets: dict[str, dict] = {}
    facet_meta: dict[str, dict] = {}
    for q in questions:
        slug = q.get("facet") or canonical_slug(q["facet_name"])
        facet_meta.setdefault(
            slug,
            {
                "facet_code": q.get("facet_code"),
                "facet_name": q.get("facet_name"),
                "domain": (q.get("domain_name") or DOMAIN_NAMES[q["domain"]]).lower(),
                "domain_name": (q.get("domain_name") or DOMAIN_NAMES[q["domain"]]),
                "domain_code": q["domain"],
                "legacy_key": legacy_snake(q["facet_name"]) if q.get("facet_name") else None,
            },
        )
    for slug, meta in facet_meta.items():
        score = facet_scores.get(slug, 0)
        facets[slug] = {
            **meta,
            "raw_score": score,
            "standardized_score": None,
            "percentile": None,
            "level": _facet_level(score),
        }

    return {
        "schema_version": "2.0",
        "assessment": {
            "instrument": "IPIP-NEO-120",
            "method": "full_test",
            "items_answered": len(answered),
            "scoring_mode": "canonical",
            "item_id_scheme": "IPIP_001..IPIP_120",
            "item_key_source": "IPIP-NEO-ItemKey.xls (official Johnson 2014 key)",
        },
        "domains": domains,
        "facets": facets,
        "responses": response_rows,
        "scoring_metadata": {
            "reverse_formula": "6 - response",
            "domain_levels": {"high": ">=84", "average": "61..83", "low": "<=60"},
            "facet_levels": {"high": ">=15", "average": "10..14", "low": "<=9"},
            "threshold_note": "Legacy thresholds retained for continuity; not official norms.",
        },
    }


def score_legacy(
    responses: Mapping[Any, Any], questions: list[dict]
) -> dict:
    """Exact reproduction of the pre-migration eval.py scoring.

    This path intentionally keeps the legacy 29-facet key and the double-
    underscore facet keys so historical results can be audited byte-for-byte.
    """
    by_legacy_id: dict[int, dict] = {}
    by_item_id: dict[str, dict] = {}
    for q in questions:
        legacy = q.get("legacy") or {}
        legacy_id = legacy.get("id", q.get("id"))
        if legacy_id is None:
            raise ValueError("legacy mode requires id or legacy.id")
        legacy_id = int(legacy_id)
        if legacy_id in by_legacy_id:
            raise ValueError(f"duplicate legacy id: {legacy_id}")
        record = {
            "id": legacy_id,
            "domain": legacy.get("domain_name", q.get("domain")),
            "facet": legacy.get("facet_name", q.get("facet")),
            "reverse": bool(legacy.get("reverse", q.get("reverse"))),
        }
        by_legacy_id[legacy_id] = record
        if q.get("item_id"):
            by_item_id[q["item_id"]] = record

    def resolve(key: Any) -> dict:
        if isinstance(key, str) and key in by_item_id:
            return by_item_id[key]
        try:
            legacy_id = int(key)
        except (TypeError, ValueError):
            legacy_id = None
        if legacy_id is not None and legacy_id in by_legacy_id:
            return by_legacy_id[legacy_id]
        raise KeyError(f"unknown legacy item identity: {key!r}")

    facet_scores: dict[str, int] = defaultdict(int)
    domain_scores: dict[str, int] = defaultdict(int)
    response_rows: list[dict] = []

    seen_legacy_ids: set[int] = set()
    for key, value in responses.items():
        q = resolve(key)
        if q["id"] in seen_legacy_ids:
            raise ValueError(f"duplicate response for legacy item {q['id']}")
        seen_legacy_ids.add(q["id"])
        raw = _validate_response(value)
        score = _reverse(raw) if q["reverse"] else raw
        facet_scores[legacy_snake(q["facet"])] += score
        domain_scores[legacy_snake(q["domain"])] += score
        response_rows.append({"item_id": q["id"], "response": raw})

    domains: dict[str, dict] = {}
    for domain_key, score in domain_scores.items():
        domains[domain_key] = {
            "raw_score": score,
            "standardized_score": None,
            "percentile": None,
            "level": _domain_level(score),
        }

    facets: dict[str, dict] = {}
    for q in questions:
        legacy = q.get("legacy") or {}
        facet_name = legacy.get("facet_name", q.get("facet"))
        domain_name = legacy.get("domain_name", q.get("domain"))
        facet_key = legacy_snake(facet_name)
        domain_key = legacy_snake(domain_name)
        if facet_key in facets:
            continue
        score = facet_scores.get(facet_key, 0)
        facets[facet_key] = {
            "domain": domain_key,
            "raw_score": score,
            "standardized_score": None,
            "level": _facet_level(score),
        }

    return {
        "schema_version": "1.0",
        "assessment": {
            "instrument": "IPIP-NEO-120",
            "method": "full_test",
            "items_answered": len(response_rows),
        },
        "domains": domains,
        "facets": facets,
        "responses": response_rows,
    }


def score_responses(
    responses: Mapping[Any, Any],
    questions: list[dict],
    *,
    mode: str = "canonical",
) -> dict:
    if mode == "canonical":
        return score_canonical(responses, questions)
    if mode == "legacy":
        return score_legacy(responses, questions)
    raise ValueError(f"unknown scoring mode: {mode!r}")


def compare_scores(old: Mapping[str, Mapping[str, Any]], new: Mapping[str, Mapping[str, Any]]) -> list[dict]:
    """Return per-key differences for raw_score and level."""
    diffs: list[dict] = []
    for key in sorted(set(old) | set(new)):
        old_row = old.get(key, {})
        new_row = new.get(key, {})
        if old_row.get("raw_score") != new_row.get("raw_score") or old_row.get("level") != new_row.get("level"):
            diffs.append(
                {
                    "key": key,
                    "old_raw_score": old_row.get("raw_score"),
                    "new_raw_score": new_row.get("raw_score"),
                    "delta": (
                        new_row.get("raw_score") - old_row.get("raw_score")
                        if old_row.get("raw_score") is not None and new_row.get("raw_score") is not None
                        else None
                    ),
                    "old_level": old_row.get("level"),
                    "new_level": new_row.get("level"),
                }
            )
    return diffs
