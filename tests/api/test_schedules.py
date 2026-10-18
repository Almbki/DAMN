"""API tests for timetable import (CSV/XLSX), listing and deletion."""

from __future__ import annotations

from datetime import time
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

_CN_CSV = """课程,星期,开始时间,结束时间,地点
高等数学,周一,09:00,11:00,教学楼A101
大学英语,周三,14:00,15:30,教学楼B202
"""


def _import_csv(
    client: TestClient, headers: dict, text: str, *, dry_run: bool = False
) -> dict:
    response = client.post(
        "/api/v1/schedules/import",
        params={"dry_run": str(dry_run).lower()},
        files={"file": ("timetable.csv", text.encode("utf-8"), "text/csv")},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_import_csv_with_chinese_headers_preserves_weekly_recurrence(
    client: TestClient, auth_headers: dict
) -> None:
    result = _import_csv(client, auth_headers, _CN_CSV)
    assert result["imported"] == 2
    assert result["skipped"] == 0

    events = client.get("/api/v1/schedules", headers=auth_headers)
    assert events.status_code == 200, events.text
    rows = events.json()
    assert len(rows) == 2

    math = next(row for row in rows if row["title"] == "高等数学")
    assert math["weekdays"] == [0]  # Monday
    assert math["start_time"] == "09:00:00"
    assert math["end_time"] == "11:00:00"
    assert math["location"] == "教学楼A101"
    assert math["event_kind"] == "class"
    assert math["source"] == "csv"

    # Dedup: importing the same file again updates instead of inserting.
    again = _import_csv(client, auth_headers, _CN_CSV)
    assert again["imported"] == 0
    assert again["updated"] == 2
    assert len(client.get("/api/v1/schedules", headers=auth_headers).json()) == 2


def test_import_xlsx_with_excel_time_cells(
    client: TestClient, auth_headers: dict
) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["title", "weekday", "start", "end", "location"])
    sheet.append(["Algorithms", "Tue", time(10, 0), time(12, 0), "Lab 3"])
    sheet.append(["Physics", "星期五", time(13, 30), time(15, 0), "Room 7"])
    buffer = BytesIO()
    workbook.save(buffer)

    response = client.post(
        "/api/v1/schedules/import",
        files={
            "file": (
                "timetable.xlsx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["imported"] == 2

    rows = client.get("/api/v1/schedules", headers=auth_headers).json()
    algo = next(row for row in rows if row["title"] == "Algorithms")
    assert algo["weekdays"] == [1]  # Tuesday
    assert algo["start_time"] == "10:00:00"
    assert algo["source"] == "xlsx"


def test_invalid_rows_produce_warnings_not_a_500(
    client: TestClient, auth_headers: dict
) -> None:
    csv_text = """title,weekday,start,end
Valid Course,Mon,09:00,10:00
,Mon,11:00,12:00
Bad Times,Tue,12:00,11:00
Unknown Weekday,Notaday,09:00,10:00
"""
    result = _import_csv(client, auth_headers, csv_text)
    assert result["imported"] == 1
    assert result["skipped"] == 3
    assert any("title is required" in warning for warning in result["warnings"])
    assert any("end time must be after start time" in warning for warning in result["warnings"])
    assert any("invalid weekday" in warning for warning in result["warnings"])


def test_import_rejects_legacy_xls_clearly(
    client: TestClient, auth_headers: dict
) -> None:
    response = client.post(
        "/api/v1/schedules/import",
        files={"file": ("timetable.xls", b"not-an-xls", "application/vnd.ms-excel")},
        headers=auth_headers,
    )
    assert response.status_code == 422, response.text
    assert ".xlsx" in response.json()["message"]


def test_dry_run_does_not_store(
    client: TestClient, auth_headers: dict
) -> None:
    result = _import_csv(client, auth_headers, _CN_CSV, dry_run=True)
    assert result["imported"] == 2
    assert client.get("/api/v1/schedules", headers=auth_headers).json() == []


def test_list_range_and_delete_event(
    client: TestClient, auth_headers: dict
) -> None:
    csv_text = """课程,日期,星期,开始时间,结束时间
单次讲座,2026-11-02,,09:00,10:00
每周例会,,周一,11:00,12:00
"""
    assert _import_csv(client, auth_headers, csv_text)["imported"] == 2

    # The weekly recurrence is returned for any week it occurs in.
    ranged = client.get(
        "/api/v1/schedules",
        params={"from": "2026-11-02", "to": "2026-11-08"},
        headers=auth_headers,
    )
    assert ranged.status_code == 200, ranged.text
    titles = {row["title"] for row in ranged.json()}
    assert titles == {"单次讲座", "每周例会"}

    event_id = ranged.json()[0]["id"]
    deleted = client.delete(f"/api/v1/schedules/{event_id}", headers=auth_headers)
    assert deleted.status_code == 204, deleted.text

    remaining = client.get("/api/v1/schedules", headers=auth_headers).json()
    assert all(row["id"] != event_id for row in remaining)

    missing = client.delete(f"/api/v1/schedules/{event_id}", headers=auth_headers)
    assert missing.status_code == 404, missing.text


def test_import_reports_overlap_within_file(
    client: TestClient, auth_headers: dict
) -> None:
    csv_text = """课程,星期,开始时间,结束时间
数学,周一,09:00,11:00
物理,周一,10:00,12:00
"""
    result = _import_csv(client, auth_headers, csv_text)
    assert result["imported"] == 2
    assert result["conflicts"], "overlapping imported events should be reported"


def test_import_weekly_grid_xlsx_persists_teacher_and_term_start(
    client: TestClient, auth_headers: dict
) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        ["节次", None, "星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    )
    sheet.append(
        [
            "上午",
            "一",
            "算法设计与分析/(1-2节)1-2周/东海岸校区/知行楼326/程老师/副教授/"
            "算法设计与分析-0002/24级计算机03班/必修课",
            None,
            None,
            None,
            None,
            None,
            None,
        ]
    )
    buffer = BytesIO()
    workbook.save(buffer)

    response = client.post(
        "/api/v1/schedules/import",
        params={"term_start": "2026-09-07"},
        files={
            "file": (
                "grid.xlsx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["imported"] == 1

    rows = client.get("/api/v1/schedules", headers=auth_headers).json()
    event = next(row for row in rows if row["title"] == "算法设计与分析")
    assert event["teacher"] == "程老师"
    assert event["location"] == "东海岸校区 知行楼326"
    assert event["weekdays"] == [0]  # Monday column C
    assert event["start_date"] == "2026-09-07"
    assert event["end_date"] == "2026-09-20"
    assert event["start_time"] == "08:00:00"
    assert event["end_time"] == "09:40:00"
