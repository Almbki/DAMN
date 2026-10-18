"""Unit tests for the weekly-grid XLSX timetable parser."""

from __future__ import annotations

from datetime import date, time
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.application.schedule_import import (
    _parse_week_ranges,
    parse_schedule_file,
)

_COURSE_CELL = (
    "算法设计与分析/(1-2节)1-7周,9-10周/东海岸校区/知行楼326/程老师/"
    "副教授/算法设计与分析-0002/24级计算机科学与技术03班;04班/必修课"
)


def _grid_workbook() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["2026-2027年第1学期"] + [None] * 8)
    sheet.append(
        ["节次", None, "星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    )
    sheet.append(["上午", "一", None, _COURSE_CELL, None, None, None, None, None])
    sheet.cell(
        row=9,
        column=1,
        value=(
            "注--内容顺序为：课程<>周次<>校区<>地点<>教师<>职称<>教学班<>"
            "专业班级<>课程性质 教学周2026-08-31正式开课，2027-01-10结束，共19周"
        ),
    )
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_parse_weekly_grid_xlsx_creates_one_event_per_week_range() -> None:
    outcome = parse_schedule_file(
        _grid_workbook(), filename="grid.xlsx", user_id=7
    )

    assert outcome.skipped == 0
    assert len(outcome.rows) == 2
    events = [row.event for row in outcome.rows]

    first, second = events
    for event in events:
        assert event.title == "算法设计与分析"
        assert event.teacher == "程老师"
        assert event.location == "东海岸校区 知行楼326"
        assert event.weekdays == [1]  # Tuesday column D
        assert event.start_time == time(8, 0)
        assert event.end_time == time(9, 40)
        assert event.source == "xlsx"
        assert event.event_kind == "class"
        assert "1-7周" in (event.notes or "") or "9-10周" in (event.notes or "")

    assert first.start_date == date(2026, 8, 31)
    assert first.end_date == date(2026, 10, 18)
    assert second.start_date == date(2026, 10, 26)
    assert second.end_date == date(2026, 11, 8)
    assert first.external_uid != second.external_uid


def test_grid_week_ranges_support_odd_even_weeks() -> None:
    assert _parse_week_ranges("1-6周单周") == [(1, 1), (3, 3), (5, 5)]
    assert _parse_week_ranges("1-6周双周") == [(2, 2), (4, 4), (6, 6)]
    assert _parse_week_ranges("1-7周,9-10周,第13周") == [
        (1, 7),
        (9, 10),
        (13, 13),
    ]


def test_parse_real_repo_test_xlsx() -> None:
    path = Path(__file__).resolve().parents[2] / "test.xlsx"
    if not path.exists():
        pytest.skip("repo-root test.xlsx is not present")

    outcome = parse_schedule_file(
        path.read_bytes(), filename="test.xlsx", user_id=1
    )

    assert outcome.rows, "expected the real timetable to produce events"
    assert all(row.event.teacher for row in outcome.rows)
    assert any(row.event.location for row in outcome.rows)
    assert any(row.event.teacher == "蔡广基" for row in outcome.rows)
    assert any(
        row.event.location == "新湖校区 知行楼326" for row in outcome.rows
    )
