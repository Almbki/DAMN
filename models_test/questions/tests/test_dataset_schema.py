from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
DAT = ROOT / "dataset" / "IPIP120.dat"


def load_json(name: str) -> dict:
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_dat_file_has_the_documented_fixed_width_shape() -> None:
    assert DAT.stat().st_size == 619_150 * 153
    data = DAT.read_bytes()
    assert data.endswith(b"\r\n")
    assert data.count(b"\r\n") == 619_150
    lines = data.split(b"\r\n")
    assert lines[-1] == b""
    assert len(lines) - 1 == 619_150
    assert all(len(line) == 151 for line in lines[:-1])


def test_item_values_are_1_to_5_and_missing_is_0() -> None:
    np = pytest.importorskip("numpy")
    raw = np.fromfile(DAT, dtype=np.uint8).reshape(-1, 153)
    items = raw[:, 31:151].astype(np.int16) - 48
    assert items.min() == 0
    assert items.max() == 5
    assert int((items == 0).sum()) == 367_593
    # Every non-missing value is one of the five response categories.
    assert set(np.unique(items).tolist()) == {0, 1, 2, 3, 4, 5}


def test_schema_matches_the_variables_documented_in_DAT120_doc() -> None:
    schema = load_json("dataset_schema.json")
    assert schema["dataset"] == "IPIP120"
    assert schema["format"] == "fixed_width"
    assert schema["header"] is False
    assert schema["record_length_chars"] == 151
    assert schema["bytes_per_record"] == 153
    assert schema["file_size_bytes"] == 94_729_950
    assert schema["n_rows"] == 619_150
    assert schema["n_variables"] == 130
    assert schema["n_items"] == 120
    assert schema["missing_values"] == [0]
    assert schema["response_scale"] == {
        "min": 1,
        "max": 5,
        "labels": [
            "Very Inaccurate",
            "Moderately Inaccurate",
            "Neither Accurate nor Inaccurate",
            "Moderately Accurate",
            "Very Accurate",
        ],
    }

    columns = {c["variable"]: c for c in schema["columns"]}
    assert columns["CASE"]["start"] == 1
    assert columns["CASE"]["end"] == 6
    assert columns["SEX"]["start"] == 7
    assert columns["COUNTRY"]["start"] == 23
    assert columns["COUNTRY"]["end"] == 31
    assert columns["I1"]["start"] == 32
    assert columns["I120"]["end"] == 151

    item_columns = schema["item_columns"]
    assert len(item_columns) == 120
    assert item_columns[0]["variable"] == "I1"
    assert item_columns[0]["item_id"] == "IPIP_001"
    assert item_columns[-1]["variable"] == "I120"
    assert item_columns[-1]["item_id"] == "IPIP_120"
    assert [c["start"] for c in item_columns] == list(range(32, 152))


def test_official_item_key_counts_and_directions() -> None:
    mapping = load_json("item_mapping.json")
    rows = mapping["items"]
    assert len(rows) == 120
    assert [r["official_short_id"] for r in rows] == list(range(1, 121))
    assert len({r["official_full_id"] for r in rows}) == 120
    assert Counter(r["domain"] for r in rows) == {
        "N": 24,
        "E": 24,
        "O": 24,
        "A": 24,
        "C": 24,
    }
    facet_counts = Counter(r["facet_name"] for r in rows)
    assert len(facet_counts) == 30
    assert set(facet_counts.values()) == {4}
    assert Counter(r["keyed_direction"] for r in rows) == {
        "positive": 65,
        "negative": 55,
    }
    for item in rows:
        assert item["official_sign"] == (
            ("+" if item["keyed_direction"] == "positive" else "-") + item["facet_code"]
        )


def test_official_key_xlsx_is_excel_safe() -> None:
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.load_workbook(ARTIFACTS / "official_item_key_120.xlsx", data_only=False)
    ws = workbook["IPIP-NEO-120"]
    assert ws.max_row == 121
    assert ws.max_column == 9
    assert ws.cell(2, 4).value == "+N1"
    assert ws.cell(2, 4).data_type != "f"
    assert ws.cell(3, 4).value == "+E1"
    assert ws.cell(3, 4).data_type != "f"
    formulas = [cell.coordinate for row in ws.iter_rows() for cell in row if cell.data_type == "f"]
    assert formulas == []


def test_official_key_assets_are_verified_against_the_original_xls() -> None:
    xlrd = pytest.importorskip("xlrd")
    openpyxl = pytest.importorskip("openpyxl")

    book = xlrd.open_workbook(str(ROOT / "dataset" / "IPIP-NEO-ItemKey.xls"))
    sheet = book.sheet_by_index(0)
    assert sheet.nrows == 301
    assert [sheet.cell_value(0, c) for c in range(6)] == [
        "Full#",
        "Short#",
        "Sign",
        "Key",
        "Facet",
        "Item",
    ]

    xls_rows = []
    for r in range(1, sheet.nrows):
        full, short, sign, key, facet, item = [sheet.cell_value(r, c) for c in range(6)]
        if short != "":
            xls_rows.append(
                {
                    "full": int(full),
                    "short": int(short),
                    "sign": str(sign).strip(),
                    "key": str(key).strip(),
                    "facet": str(facet).strip(),
                    "item": str(item).strip(),
                }
            )
    assert len(xls_rows) == 120
    assert [r["short"] for r in xls_rows] == list(range(1, 121))

    mapping = load_json("item_mapping.json")
    by_short = {item["official_short_id"]: item for item in mapping["items"]}
    workbook = openpyxl.load_workbook(ARTIFACTS / "official_item_key_120.xlsx", data_only=False)
    ws = workbook["IPIP-NEO-120"]

    for index, xls in enumerate(xls_rows, start=1):
        item = by_short[index]
        assert item["official_full_id"] == xls["full"]
        assert item["official_sign"] == xls["sign"]
        assert item["keyed_direction"] == (
            "positive" if xls["sign"].startswith("+") else "negative"
        )
        assert item["facet_code"] == xls["key"]
        assert item["facet_name"] == xls["facet"]
        assert item["text_en"] == xls["item"]

        xlsx_row = [ws.cell(index + 1, c).value for c in range(1, 10)]
        assert xlsx_row == [
            index,
            xls["short"],
            xls["full"],
            xls["sign"],
            item["keyed_direction"],
            xls["key"],
            {
                "N": "Neuroticism",
                "E": "Extraversion",
                "O": "Openness",
                "A": "Agreeableness",
                "C": "Conscientiousness",
            }[xls["key"][0]],
            xls["facet"],
            xls["item"],
        ]
        assert ws.cell(index + 1, 4).data_type != "f"
        assert ws.cell(index + 1, 4).value == xls["sign"]


def test_mapping_issues_are_resolved() -> None:
    issues = load_json("mapping_issues.json")
    assert issues["status"] == "resolved"
    assert issues["canonical_metadata_status"] == "adopted_in_production_bank"
    assert issues["legacy_bank_status"] == "archived_in_tests_fixtures"
    assert issues["metadata_issues"] == 4
    assert all(issue["canonical_status"] == "adopted_in_production_bank" for issue in issues["issues"])


def test_empirical_dataset_alignment_artifact() -> None:
    validation = load_json("dataset_schema.json")["validation"]
    assert validation is not None
    assert validation["n_rows"] == 619_150
    assert validation["all_rows_151_chars"] is True
    assert validation["missing_value_code"] == 0
    assert validation["missing_cell_count"] == 367_593
    assert validation["rows_with_any_missing"] == 208_774

    correlation = validation["correlation"]
    assert correlation["lag_30"] > 0.4
    assert correlation["lag_60"] > 0.4
    assert correlation["lag_90"] > 0.4
    assert correlation["lag_30"] > 10 * correlation["mean_all_off_diagonal"]
    top3 = {row["lag"] for row in correlation["lag_profile_top10"][:3]}
    assert top3 == {30, 60, 90}

    assert validation["empirical_order_check"]["status"] == "pass"
    for item_id, evidence in validation["metadata_correction_evidence"].items():
        assert item_id in {"IPIP_016", "IPIP_046", "IPIP_076", "IPIP_106"}
        assert evidence["mean_r_with_N4_mates"] > 0
        assert evidence["mean_r_with_E1_mates"] < 0
