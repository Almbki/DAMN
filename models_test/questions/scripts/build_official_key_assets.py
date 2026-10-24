"""Build the Excel-facing official ItemKey workbook from the original XLS.

Source of truth:
    dataset/IPIP-NEO-ItemKey.xls
    sheet "IPIP-NEO-ItemKey", header row 1, 300 item rows.
    The 120-item form is the subset with a non-empty Short# (1..120).

Output:
    artifacts/official_item_key_120.xlsx

The `Sign` column is stored as text so Excel displays `+N1` / `-A2` correctly
instead of interpreting them as formulas.  Machine-readable data lives in
`artifacts/item_mapping.json`; this workbook is the human/Excel view.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import openpyxl
import xlrd
from openpyxl.styles import Alignment, Font, PatternFill

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
XLS = ROOT / "dataset" / "IPIP-NEO-ItemKey.xls"
XLSX_OUT = ARTIFACTS / "official_item_key_120.xlsx"

XLSX_COLUMNS = [
    "Official order",
    "Official Short#",
    "Official Full#",
    "Sign",
    "Direction",
    "Key",
    "Domain",
    "Facet",
    "Item",
]

DOMAIN_NAMES = {
    "N": "Neuroticism",
    "E": "Extraversion",
    "O": "Openness",
    "A": "Agreeableness",
    "C": "Conscientiousness",
}


def read_xls() -> tuple[list[dict], int]:
    book = xlrd.open_workbook(str(XLS), formatting_info=False)
    if book.nsheets != 1:
        raise SystemExit(f"expected one sheet, found {book.sheet_names()}")
    sheet = book.sheet_by_index(0)
    header = [str(sheet.cell_value(0, c)).strip() for c in range(sheet.ncols)]
    if header != ["Full#", "Short#", "Sign", "Key", "Facet", "Item"]:
        raise SystemExit(f"unexpected header: {header}")

    rows: list[dict] = []
    pool = 0
    for r in range(1, sheet.nrows):
        full, short, sign, key, facet, item = [sheet.cell_value(r, c) for c in range(6)]
        if short == "":
            pool += 1
            continue
        rows.append(
            {
                "full": int(full),
                "short": int(short),
                "sign": str(sign).strip(),
                "key": str(key).strip(),
                "facet": str(facet).strip(),
                "item": str(item).strip(),
            }
        )
    if len(rows) != 120:
        raise SystemExit(f"expected 120 short-form rows, got {len(rows)}")
    if [r["short"] for r in rows] != list(range(1, 121)):
        raise SystemExit("Short# is not exactly 1..120 in order")
    for row in rows:
        if row["sign"] not in {"+" + row["key"], "-" + row["key"]}:
            raise SystemExit(f"Sign does not match Key: {row}")
    return rows, pool


def write_xlsx(rows: list[dict]) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "IPIP-NEO-120"

    header_fill = PatternFill("solid", fgColor="305496")
    header_font = Font(bold=True, color="FFFFFF")
    for c, name in enumerate(XLSX_COLUMNS, start=1):
        cell = ws.cell(row=1, column=c, value=name)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for r, row in enumerate(rows, start=2):
        values = [
            r - 1,
            row["short"],
            row["full"],
            row["sign"],
            "positive" if row["sign"].startswith("+") else "negative",
            row["key"],
            DOMAIN_NAMES[row["key"][0]],
            row["facet"],
            row["item"],
        ]
        for c, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=c, value=value)
            if c == 4:
                cell.number_format = "@"
                cell.data_type = "s"
            cell.alignment = Alignment(vertical="top", wrap_text=(c == 9))

    widths = {"A": 14, "B": 16, "C": 16, "D": 10, "E": 11, "F": 8, "G": 14, "H": 24, "I": 72}
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:I{len(rows) + 1}"

    notes = wb.create_sheet("README")
    notes["A1"] = "IPIP-NEO-120 official item key"
    notes["A1"].font = Font(bold=True, size=14)
    note_rows = [
        ("Source", "dataset/IPIP-NEO-ItemKey.xls, sheet 'IPIP-NEO-ItemKey'"),
        ("Rows used", "Rows 2-121 (Short# = 1..120). Rows 122-301 are the full 300-item pool and have no Short#."),
        ("Counts", "120 items; 5 domains x 24; 30 facets x 4; 65 positive / 55 negative."),
        ("Sign column", "Stored as text so Excel does not interpret +N1 / -A2 as formulas."),
        ("Machine-readable", "artifacts/item_mapping.json contains the same mapping with item_id and legacy audit fields."),
    ]
    for r, (label, value) in enumerate(note_rows, start=3):
        notes.cell(row=r, column=1, value=label).font = Font(bold=True)
        notes.cell(row=r, column=2, value=value)
    notes.column_dimensions["A"].width = 16
    notes.column_dimensions["B"].width = 110
    for row in notes.iter_rows(min_row=3, max_row=2 + len(note_rows), min_col=2, max_col=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    wb.save(XLSX_OUT)


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    rows, pool = read_xls()
    write_xlsx(rows)
    counts = {
        "items": len(rows),
        "full_pool_rows": pool,
        "domains": dict(Counter(r["key"][0] for r in rows)),
        "facets": len({r["facet"] for r in rows}),
        "positive": sum(1 for r in rows if r["sign"].startswith("+")),
        "negative": sum(1 for r in rows if r["sign"].startswith("-")),
    }
    print("counts:", counts)
    print("wrote:", XLSX_OUT)


if __name__ == "__main__":
    main()
