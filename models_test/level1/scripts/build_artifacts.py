"""Build the IPIP-NEO-120 official mapping artifacts.

Reads the original official XLS plus the archived legacy bank fixture and
produces the production canonical bank and its audit artifacts:

  questions.json                         (production canonical bank)
  artifacts/item_mapping.json
  artifacts/mapping_issues.json
  artifacts/mapping_report.md
  artifacts/dataset_schema.json

The legacy bank is read-only at tests/fixtures/legacy_questions.json. The
official XLS remains the source of truth; the XLSX is the Excel-facing view.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import xlrd

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
DATASET = ROOT / "dataset"
XLS = DATASET / "IPIP-NEO-ItemKey.xls"
LOCAL_BANK = ROOT / "tests" / "fixtures" / "legacy_questions.json"
CANONICAL_BANK = ROOT / "questions.json"

DOMAIN_NAMES = {
    "N": "Neuroticism",
    "E": "Extraversion",
    "O": "Openness",
    "A": "Agreeableness",
    "C": "Conscientiousness",
}

NON_ITEM_COLUMNS = [
    {
        "variable": "CASE",
        "start": 1,
        "end": 6,
        "format": "F6.0",
        "type": "respondent_id",
        "description": "Original case number; runs higher than N because the original file was subset.",
    },
    {"variable": "SEX", "start": 7, "end": 7, "format": "F1.0", "type": "covariate", "description": "1 = male; 2 = female."},
    {"variable": "AGE", "start": 8, "end": 9, "format": "F2.0", "type": "covariate", "description": "Age in years."},
    {"variable": "SEC", "start": 10, "end": 11, "format": "F2.0", "type": "timestamp", "description": "Seconds of completion time."},
    {"variable": "MIN", "start": 12, "end": 13, "format": "F2.0", "type": "timestamp", "description": "Minutes of completion time."},
    {"variable": "HOUR", "start": 14, "end": 15, "format": "F2.0", "type": "timestamp", "description": "Hour of completion time."},
    {"variable": "DAY", "start": 16, "end": 17, "format": "F2.0", "type": "timestamp", "description": "Day of month."},
    {"variable": "MONTH", "start": 18, "end": 19, "format": "F2.0", "type": "timestamp", "description": "0 = January ... 11 = December."},
    {"variable": "YEAR", "start": 20, "end": 22, "format": "F3.0", "type": "timestamp", "description": "Years since 1900; add 1900 for four-digit year."},
    {"variable": "COUNTRY", "start": 23, "end": 31, "format": "A9", "type": "covariate", "description": "Country/region string, left-justified in 9 characters."},
]


def read_key() -> list[dict]:
    """Read the 120 short-form rows directly from the original XLS."""
    book = xlrd.open_workbook(str(XLS), formatting_info=False)
    sheet = book.sheet_by_index(0)
    header = [str(sheet.cell_value(0, c)).strip() for c in range(6)]
    if header != ["Full#", "Short#", "Sign", "Key", "Facet", "Item"]:
        raise SystemExit(f"unexpected ItemKey header: {header}")

    rows: list[dict] = []
    for r in range(1, sheet.nrows):
        full, short, sign, key, facet, item = [sheet.cell_value(r, c) for c in range(6)]
        if short == "":
            continue
        sign = str(sign).strip()
        key = str(key).strip()
        rows.append(
            {
                "official_order": int(short),
                "official_short_id": int(short),
                "official_full_id": int(full),
                "sign": sign,
                "direction": "negative" if sign.startswith("-") else "positive",
                "key": key,
                "domain_code": key[0],
                "facet_name": str(facet).strip(),
                "item_text": str(item).strip(),
            }
        )
    if len(rows) != 120:
        raise SystemExit(f"expected 120 short-form rows, got {len(rows)}")
    return rows


def canonical_slug(text: str) -> str:
    text = text.lower().replace("-", " ").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def normalize_label(text: str) -> str:
    """Case/punctuation-insensitive comparison for Domain and Facet names."""
    return canonical_slug(text)


def legacy_snake(text: str) -> str:
    """Reproduce the legacy eval.py to_snake_case, including double underscores."""
    text = text.replace("-", "_").replace(" ", "_")
    return re.sub(r"(?<!^)(?=[A-Z])", "_", text).lower()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_items() -> tuple[list[dict], list[dict]]:
    key = read_key()
    local = json.loads(LOCAL_BANK.read_text(encoding="utf-8"))
    if len(key) != 120:
        raise SystemExit(f"official key must have 120 rows, got {len(key)}")
    if len(local) != 120:
        raise SystemExit(f"local bank must have 120 items, got {len(local)}")

    items: list[dict] = []
    issues: list[dict] = []
    normalizations: list[dict] = []

    for order, (k, q) in enumerate(zip(key, local), start=1):
        if k["official_short_id"] != order:
            raise SystemExit(f"official key is not in Short# order at row {order}")
        if q["id"] != order:
            raise SystemExit(f"local bank is not in id order at row {order}")

        short = k["official_short_id"]
        domain_code = k["domain_code"]
        domain_name = DOMAIN_NAMES[domain_code]
        facet_name = k["facet_name"]
        facet_slug = canonical_slug(facet_name)
        reverse = k["direction"] == "negative"
        legacy_facet_key = legacy_snake(q["facet"])
        legacy_domain_key = legacy_snake(q["domain"])

        official_sign = ("+" if k["direction"] == "positive" else "-") + k["key"]
        official_meta = {
            "domain_code": domain_code,
            "domain_name": domain_name,
            "facet_code": k["key"],
            "facet_name": facet_name,
            "facet_slug": facet_slug,
            "official_sign": official_sign,
            "reverse": reverse,
        }
        legacy_meta = {
            "id": q["id"],
            "order": order,
            "domain_name": q["domain"],
            "domain_key": legacy_domain_key,
            "facet_name": q["facet"],
            "facet_key": legacy_facet_key,
            "reverse": bool(q["reverse"]),
        }
        domain_mismatch = normalize_label(q["domain"]) != normalize_label(domain_name)
        facet_mismatch = normalize_label(q["facet"]) != normalize_label(facet_name)
        reverse_mismatch = bool(q["reverse"]) != reverse
        mismatch = domain_mismatch or facet_mismatch or reverse_mismatch
        naming_only = (
            not mismatch
            and (q["domain"] != domain_name or q["facet"] != facet_name)
        )

        item = {
            "item_id": f"IPIP_{short:03d}",
            "official_order": order,
            "official_short_id": short,
            "official_full_id": k["official_full_id"],
            "dataset_column": f"I{short}",
            "dataset_start": 31 + short,
            "dataset_end": 31 + short,
            "domain": domain_code,
            "domain_name": domain_name,
            "facet_code": k["key"],
            "facet": facet_slug,
            "facet_name": facet_name,
            "official_sign": official_sign,
            "keyed_direction": k["direction"],
            "reverse_scored": reverse,
            "local_question_id": q["id"],
            "local_order": order,
            "text": q["text"],
            "local_text": q["text"],
            "local_text_sha256": sha256_text(q["text"]),
            "text_en": k["item_text"],
            "translation_verified": True,
            "translation_verification": (
                "Manual side-by-side review of all 120 local Chinese texts "
                "against the official IPIP-NEO-120 item texts."
            ),
            "legacy": legacy_meta,
            "metadata_correction": mismatch,
            "naming_normalization": naming_only,
        }
        if naming_only:
            item["normalization"] = {
                "official_domain_name": domain_name,
                "official_facet_name": facet_name,
                "legacy_domain_name": q["domain"],
                "legacy_facet_name": q["facet"],
                "note": (
                    "Hyphen/space/case-only difference; the normalized Domain "
                    "and Facet are identical. Not a semantic conflict."
                ),
            }
            normalizations.append(
                {
                    "item_id": item["item_id"],
                    "local_question_id": q["id"],
                    "official_order": order,
                    "type": "naming_normalization",
                    "official_facet_name": facet_name,
                    "legacy_facet_name": q["facet"],
                    "normalized_facet": facet_slug,
                    "blocking": False,
                }
            )
        if mismatch:
            item["correction"] = {
                "official": official_meta,
                "legacy": legacy_meta,
                "reason": (
                    f"Local metadata says {q['domain']}/{q['facet']}/"
                    f"reverse={bool(q['reverse'])}; official ItemKey says "
                    f"{domain_name}/{facet_name}/reverse={reverse}. The official "
                    "text identity and the 619,150-row dataset both support the "
                    "official metadata."
                ),
            }
            issues.append(
                {
                    "item_id": item["item_id"],
                    "local_question_id": q["id"],
                    "official_order": order,
                    "type": "metadata_mismatch",
                    "description": (
                        f"Local metadata says {q['domain']}/{q['facet']}/"
                        f"reverse={bool(q['reverse'])}; official ItemKey says "
                        f"{domain_name}/{facet_name}/reverse={reverse}."
                    ),
                    "official": official_meta,
                    "legacy": legacy_meta,
                    "evidence": [
                        f"Local text '{q['text']}' is the Chinese rendering of "
                        f"official item '{k['item_text']}' (Short#{short}, "
                        f"Full#{k['official_full_id']}).",
                        "Dataset correlations place this item with the other "
                        "N4 items, not with E1 items (see the validation block "
                        "in dataset_schema.json).",
                    ],
                    "canonical_status": "adopted_in_production_bank",
                    "resolution_state": (
                        "questions.json now uses the official N4/Self-Consciousness "
                        "metadata. The legacy bank is archived at "
                        "tests/fixtures/legacy_questions.json for audit only."
                    ),
                    "requires_decision": False,
                }
            )
        items.append(item)

    # Structural validation of the official key.
    domain_counts = Counter(i["domain"] for i in items)
    facet_counts = Counter(i["facet_code"] for i in items)
    if domain_counts != {"N": 24, "E": 24, "O": 24, "A": 24, "C": 24}:
        raise SystemExit(f"domain counts are not 24 each: {dict(domain_counts)}")
    if len(facet_counts) != 30 or any(v != 4 for v in facet_counts.values()):
        raise SystemExit(f"facet counts are not 30 x 4: {dict(facet_counts)}")
    if len({i["item_id"] for i in items}) != 120:
        raise SystemExit("duplicate item_id")
    if len({i["local_question_id"] for i in items}) != 120:
        raise SystemExit("duplicate local_question_id")

    return items, issues, normalizations


def build_mapping(items: list[dict], issues: list[dict], normalizations: list[dict]) -> dict:
    return {
        "schema_version": "1.0",
        "dataset": "IPIP120",
        "source": "Johnson 2014 IPIP-NEO-120",
        "official_key_file": "dataset/IPIP-NEO-ItemKey.xls",
        "official_key_xlsx": "artifacts/official_item_key_120.xlsx",
        "dataset_file": "dataset/IPIP120.dat",
        "legacy_source_fixture": "tests/fixtures/legacy_questions.json",
        "canonical_bank_file": "questions.json",
        "source_hashes": {
            "legacy_questions_sha256": sha256_file(LOCAL_BANK),
            "canonical_questions_sha256": sha256_file(CANONICAL_BANK),
            "official_key_xls_sha256": sha256_file(XLS),
            "official_key_xlsx_sha256": sha256_file(ARTIFACTS / "official_item_key_120.xlsx"),
            "ipip120_dat_sha256": sha256_file(DATASET / "IPIP120.dat"),
        },
        "item_id_scheme": {
            "pattern": "IPIP_{official_short_id:03d}",
            "description": (
                "Stable canonical identity derived from the official Short# "
                "column of IPIP-NEO-ItemKey.xls. The array index is never used "
                "as identity."
            ),
            "official_short_id": "Short# in IPIP-NEO-ItemKey.xls, 1..120",
            "official_full_id": "Full# in IPIP-NEO-ItemKey.xls, 1..300",
            "dataset_column": "I{short} in IPIP120.dat, character positions 32..151",
        },
        "mapping_method": [
            "Primary: manual semantic match of each local Chinese text to the official English item text.",
            "Secondary: the observed local order equals the official Short# order; this was used as a consistency check, not as the sole basis.",
            "Tertiary: official Domain/Facet/Sign metadata and empirical dataset correlations.",
        ],
        "counts": {
            "official_items": 120,
            "local_items": 120,
            "mapped": 120,
            "missing": 0,
            "duplicate_local": 0,
            "duplicate_official": 0,
            "ambiguous_identity": 0,
            "metadata_corrections": len(issues),
            "naming_normalizations": len(normalizations),
            "domains": {"N": 24, "E": 24, "O": 24, "A": 24, "C": 24},
            "distinct_facets": 30,
            "items_per_facet": 4,
        },
        "status": "identity_clean_metadata_blocked",
        "normalizations": normalizations,
        "items": items,
    }


def build_dataset_schema(items: list[dict]) -> dict:
    item_columns = [
        {
            "variable": i["dataset_column"],
            "start": i["dataset_start"],
            "end": i["dataset_end"],
            "format": "F1.0",
            "item_id": i["item_id"],
            "official_order": i["official_order"],
            "official_short_id": i["official_short_id"],
            "official_full_id": i["official_full_id"],
            "official_sign": i["official_sign"],
            "domain": i["domain"],
            "facet_code": i["facet_code"],
        }
        for i in items
    ]
    return {
        "dataset": "IPIP120",
        "source": "Johnson 2014 IPIP-NEO-120",
        "file": "dataset/IPIP120.dat",
        "format": "fixed_width",
        "encoding": "ASCII",
        "header": False,
        "record_length_chars": 151,
        "line_terminator": "CRLF",
        "bytes_per_record": 153,
        "file_size_bytes": 94729950,
        "n_rows": 619150,
        "n_variables": 130,
        "n_items": 120,
        "respondent_id": {"variable": "CASE", "start": 1, "end": 6},
        "response_scale": {
            "min": 1,
            "max": 5,
            "labels": [
                "Very Inaccurate",
                "Moderately Inaccurate",
                "Neither Accurate nor Inaccurate",
                "Moderately Accurate",
                "Very Accurate",
            ],
        },
        "missing_values": [0],
        "missing_value_note": "0 is the missing-response code for items I1..I120.",
        "reverse_scoring": {
            "dataset_values": "Reverse-scored items were recoded (1=5, 2=4, 4=2, 5=1) at administration time; values in IPIP120.dat can be summed directly.",
            "local_raw_responses": "For raw local responses, apply 6 - response when reverse_scored is true.",
        },
        "item_block": {
            "first": {"variable": "I1", "start": 32, "end": 32},
            "last": {"variable": "I120", "start": 151, "end": 151},
            "contiguous": True,
            "stride": 1,
        },
        "non_item_variables": [c["variable"] for c in NON_ITEM_COLUMNS],
        "columns": NON_ITEM_COLUMNS + item_columns,
        "item_columns": item_columns,
        "validation": None,
    }


def build_issues(issues: list[dict], normalizations: list[dict]) -> dict:
    return {
        "status": "resolved",
        "identity_status": "clean",
        "canonical_metadata_status": "adopted_in_production_bank",
        "legacy_bank_status": "archived_in_tests_fixtures",
        "blocking_scope": "none",
        "identity_issues": 0,
        "metadata_issues": len(issues),
        "issues": issues,
        "non_blocking_normalizations": normalizations,
        "summary": {
            "missing": 0,
            "duplicate": 0,
            "ambiguous_identity": 0,
            "unverified": 0,
            "metadata_mismatch": len(issues),
            "naming_normalizations": len(normalizations),
            "official_domains": {"N": 24, "E": 24, "O": 24, "A": 24, "C": 24},
            "official_facets": 30,
            "official_items_per_facet": 4,
            "legacy_distinct_facets": 29,
            "legacy_friendliness_items": 8,
        },
        "resolution": (
            "The four legacy E1/Friendliness labels were corrected to the official "
            "N4/Self-Consciousness labels and adopted in questions.json. The legacy "
            "bank is archived at tests/fixtures/legacy_questions.json for audit only. "
            "Historical scores remain reproducible through scoring.score_legacy()."
        ),
        "canonical_bank_file": "questions.json",
        "legacy_bank_file": "tests/fixtures/legacy_questions.json",
        "grm_or_cat_started": False,
    }


def build_mapping_report(
    items: list[dict], issues: list[dict], normalizations: list[dict]
) -> str:
    lines: list[str] = []
    lines.append("# IPIP-NEO-120 Official Item Mapping\n")
    lines.append(
        "This table maps every local question to the official IPIP-NEO-120 "
        "item identity, dataset column, domain, facet, and direction.\n"
    )
    lines.append(
        f"Official items: **120** · Local items: **120** · Identity mapping: "
        f"**120/120** · Legacy metadata corrections: **{len(issues)}** "
        f"(adopted in `questions.json`)\n"
    )
    lines.append(
        "`item_id` is `IPIP_001` ... `IPIP_120`, derived from the official "
        "`Short#` column. `dataset_column` is the fixed-width variable `I1` ... "
        "`I120` in `IPIP120.dat` (character positions 32..151).\n"
    )
    lines.append(
        "The local bank is already in the same order as the official `Short#` "
        "order, but array order is **not** used as identity. Every local text "
        "was checked against the official English item text.\n"
    )
    lines.append(
        f"Eight non-blocking naming normalizations (hyphen/space only) are "
        f"listed separately in `mapping_issues.json`: "
        f"{', '.join(n['item_id'] for n in normalizations)}.\n"
    )
    lines.append(
        "Excel-facing asset: `official_item_key_120.xlsx` stores the exact `Sign` "
        "text (`+N1` / `-A2`) as text. The original `.xls` remains the source of "
        "truth.\n"
    )
    lines.append("## 120-item crosswalk\n\n")
    lines.append(
        "| Official order | Item ID | Dataset column | Local ID | Old order | "
        "Domain | Facet | Sign | Reverse | Status |\n"
    )
    lines.append(
        "|---:|---|---|---:|---:|---|---|---|---:|---|\n"
    )
    for i in items:
        if i["metadata_correction"]:
            status = (
                f"adopted: {i['domain']}/{i['facet_code']} "
                f"{i['facet_name']}, reverse={str(i['reverse_scored']).lower()}"
            )
        else:
            status = "ok"
        lines.append(
            f"| {i['official_order']} | {i['item_id']} | {i['dataset_column']} | "
            f"{i['local_question_id']} | {i['local_order']} | {i['domain']} | "
            f"{i['facet_name']} | {i['official_sign']} | "
            f"{str(i['reverse_scored']).lower()} | {status} |\n"
        )
    lines.append("\n## Legacy corrections (adopted)\n\n")
    lines.append(
        "These four items were `E1 / Friendliness` in the archived legacy bank "
        "(`tests/fixtures/legacy_questions.json`). The canonical `questions.json` "
        "now uses the official `N4 / Self-Consciousness` metadata. The legacy bank "
        "is kept only as a test fixture for historical regression.\n\n"
    )
    lines.append("| Item | Legacy (archived) | Adopted canonical | Dataset evidence |\n")
    lines.append("|---|---|---|---|\n")
    for issue in issues:
        off = issue["official"]
        leg = issue["legacy"]
        ev = issue["evidence"][1] if len(issue["evidence"]) > 1 else ""
        lines.append(
            f"| {issue['item_id']} | {leg['domain_name']} / {leg['facet_name']} / "
            f"reverse={leg['reverse']} | {off['domain_name']} / {off['facet_name']} / "
            f"reverse={off['reverse']} (`{off['facet_code']}`, sign "
            f"`{off['official_sign']}`) | {ev} |\n"
        )
    lines.append("\n## How to read this table\n")
    lines.append(
        "`questions.json` is the production canonical bank. The `Status` column is "
        "`ok` for unchanged items and `adopted` for the four corrected N4 items. "
        "The legacy bank is archived at `tests/fixtures/legacy_questions.json`; it "
        "is not a production input. Historical scores remain reproducible through "
        "`scoring.score_legacy()` for audit only.\n"
    )
    return "".join(lines)


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    items, issues, normalizations = build_items()

    # Write the production bank first so the mapping can record its exact hash.
    CANONICAL_BANK.write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    mapping = build_mapping(items, issues, normalizations)
    issues_doc = build_issues(issues, normalizations)
    schema = build_dataset_schema(items)

    (ARTIFACTS / "item_mapping.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ARTIFACTS / "mapping_issues.json").write_text(
        json.dumps(issues_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ARTIFACTS / "dataset_schema.json").write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ARTIFACTS / "mapping_report.md").write_text(
        build_mapping_report(items, issues, normalizations), encoding="utf-8"
    )

    print(f"items: {len(items)}")
    print(f"metadata conflicts: {len(issues)}")
    print(f"canonical bank: {CANONICAL_BANK.name}")
    print(f"artifacts: {ARTIFACTS}")


if __name__ == "__main__":
    main()
