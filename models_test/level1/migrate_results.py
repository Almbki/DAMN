"""Recompute the two historical users under canonical item identities.

The old result JSONs are archived in tests/fixtures/legacy_results.json.
This script verifies the legacy scoring path exactly reproduces the archived
domain/facet scores, then writes canonical results to results/result_*.json.

Usage:
    python migrate_results.py
"""

from __future__ import annotations

import json
from pathlib import Path

from scoring import (
    LEGACY_FACET_KEY_TO_CANONICAL,
    load_questions,
    score_canonical,
    score_legacy,
)

ROOT = Path(__file__).resolve().parent
QUESTIONS = ROOT / "questions.json"
LEGACY_FIXTURE = ROOT / "tests" / "fixtures" / "legacy_results.json"
RESULTS_DIR = ROOT / "results"


def _raw_score_diffs(
    old: dict, new: dict, key_map: dict[str, str] | None = None
) -> list[dict]:
    key_map = key_map or {}
    rows: list[dict] = []
    old_mapped = {key_map.get(k, k): v for k, v in old.items()}
    for key in sorted(set(old_mapped) | set(new)):
        old_row = old_mapped.get(key, {})
        new_row = new.get(key, {})
        old_raw = old_row.get("raw_score")
        new_raw = new_row.get("raw_score")
        if old_raw == new_raw and old_row.get("level") == new_row.get("level"):
            continue
        rows.append(
            {
                "key": key,
                "old_raw_score": old_raw,
                "new_raw_score": new_raw,
                "delta": (new_raw - old_raw) if old_raw is not None and new_raw is not None else None,
                "old_level": old_row.get("level"),
                "new_level": new_row.get("level"),
            }
        )
    return rows


def migrate_one(name: str, original: dict, questions: list[dict]) -> dict:
    responses = {int(row["item_id"]): row["response"] for row in original["responses"]}
    if len(responses) != 120:
        raise SystemExit(f"{name}: expected 120 responses, got {len(responses)}")

    legacy = score_legacy(responses, questions)
    canonical = score_canonical(responses, questions)

    legacy_domain_diffs = _raw_score_diffs(original["domains"], legacy["domains"])
    legacy_facet_diffs = _raw_score_diffs(original["facets"], legacy["facets"])
    legacy_ok = not legacy_domain_diffs and not legacy_facet_diffs

    canonical_domain_diffs = _raw_score_diffs(original["domains"], canonical["domains"])
    canonical_facet_diffs = _raw_score_diffs(
        original["facets"], canonical["facets"], LEGACY_FACET_KEY_TO_CANONICAL
    )

    if not legacy_ok:
        raise SystemExit(
            f"{name}: legacy regression failed\n"
            f"  domains: {legacy_domain_diffs}\n  facets: {legacy_facet_diffs}"
        )

    migrated = {
        "schema_version": "2.0",
        "assessment": canonical["assessment"],
        "domains": canonical["domains"],
        "facets": canonical["facets"],
        "responses": canonical["responses"],
        "migration": {
            "source_result_file": f"tests/fixtures/legacy_results.json#{name}",
            "source_item_id_scheme": "legacy integer id 1..120",
            "target_item_id_scheme": "IPIP_001..IPIP_120",
            "raw_responses_preserved": True,
            "legacy_scoring_matches_original": legacy_ok,
            "legacy_domains": legacy["domains"],
            "legacy_facets": legacy["facets"],
            "canonical_vs_legacy_domain_diffs": canonical_domain_diffs,
            "canonical_vs_legacy_facet_diffs": canonical_facet_diffs,
            "note": (
                "The canonical block uses official ItemKey metadata. The legacy "
                "block reproduces the pre-migration eval.py scores. They differ "
                "only at the four corrected N4 items."
            ),
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    target = RESULTS_DIR / f"result_{name}.json"
    target.write_text(
        json.dumps(migrated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "name": name,
        "target": f"results/result_{name}.json",
        "items": len(responses),
        "legacy_scoring_matches_original": legacy_ok,
        "canonical_domain_diffs": canonical_domain_diffs,
        "canonical_facet_diffs": canonical_facet_diffs,
        "legacy_facet_count": len(legacy["facets"]),
        "canonical_facet_count": len(canonical["facets"]),
    }


def main() -> None:
    questions = load_questions(QUESTIONS)
    legacy_results = json.loads(LEGACY_FIXTURE.read_text(encoding="utf-8"))
    if not isinstance(legacy_results, dict) or not legacy_results:
        raise SystemExit("legacy_results.json must be a non-empty object keyed by user")

    users = [
        migrate_one(name, legacy_results[name], questions)
        for name in sorted(legacy_results)
    ]

    print(f"users: {len(users)}")
    for user in users:
        print(
            f"  {user['name']}: items={user['items']} "
            f"legacy={user['legacy_scoring_matches_original']} "
            f"domain_diffs={user['canonical_domain_diffs']} "
            f"facet_diffs={user['canonical_facet_diffs']}"
        )
    print(f"wrote: {', '.join(user['target'] for user in users)}")


if __name__ == "__main__":
    main()
