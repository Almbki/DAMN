"""Tolerant CSV/XLSX timetable import.

Supported inputs
----------------
* CSV (``utf-8-sig``, then ``gb18030``) and XLSX (``openpyxl``, read-only).
* Chinese and English headers (see :data:`HEADER_ALIASES`), with spaces /
  underscores / case ignored.
* Weekdays as ``周一..周日``, ``星期一..星期日``, ``Mon..Sun`` or ``1..7``.
* Times as ``HH:MM``, ``H:MM``, ``HH:MM:SS`` or Excel time/datetime cells.
* Dates as ISO, ``YYYY/MM/DD`` or Excel date/datetime cells.

Invalid rows never abort the import: they are skipped and reported as warnings.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.utils.datetime import from_excel

from app.application.exceptions import DomainValidationError
from app.domain.models.schedule_event import ScheduleEvent

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ROWS = 1000

#: Period number -> ``(start_time, end_time)``. Edit here when the school
#: changes its bell schedule; the grid importer reads this mapping.
PERIOD_TIMES: dict[tuple[int, int], tuple[time, time]] = {
    (1, 2): (time(8, 0), time(9, 40)),
    (3, 4): (time(10, 0), time(11, 40)),
    (5, 6): (time(14, 0), time(15, 40)),
    (7, 8): (time(16, 0), time(17, 40)),
    (9, 10): (time(19, 0), time(20, 40)),
    (11, 12): (time(20, 50), time(22, 30)),
}

# Canonical columns.
TITLE = "title"
DATE = "date"
WEEKDAY = "weekday"
START = "start"
END = "end"
LOCATION = "location"
RECURRENCE = "recurrence"
KIND = "kind"
UID = "uid"
NOTES = "notes"


def _clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return unicodedata.normalize("NFKC", value).strip()
    return str(value).strip()


def _normalize_header(value: object) -> str:
    return (
        _clean(value)
        .lower()
        .replace("_", "")
        .replace(" ", "")
        .replace("\u3000", "")
    )


def _aliases(*values: str) -> set[str]:
    return {_normalize_header(value) for value in values}


#: Canonical column -> accepted header spellings. Normalised with
#: :func:`_normalize_header`, so ``start_time``, ``Start Time`` and
#: ``starttime`` all match ``START``.
HEADER_ALIASES: dict[str, set[str]] = {
    TITLE: _aliases("title", "course", "课程", "名称", "事项"),
    DATE: _aliases("date", "日期", "start_date"),
    WEEKDAY: _aliases("weekday", "星期", "周几", "星期几"),
    START: _aliases("start", "start_time", "开始", "开始时间"),
    END: _aliases("end", "end_time", "结束", "结束时间"),
    LOCATION: _aliases("location", "地点", "教室"),
    RECURRENCE: _aliases("recurrence", "重复", "周期"),
    KIND: _aliases("kind", "type", "类型"),
    UID: _aliases("uid", "external_uid", "编号"),
    NOTES: _aliases("notes", "备注", "说明"),
}
_HEADER_LOOKUP = {
    alias: canonical
    for canonical, aliases in HEADER_ALIASES.items()
    for alias in aliases
}

_WEEKDAY_MAP: dict[str, int] = {
    "mon": 0,
    "monday": 0,
    "周一": 0,
    "星期一": 0,
    "礼拜一": 0,
    "tue": 1,
    "tues": 1,
    "tuesday": 1,
    "周二": 1,
    "星期二": 1,
    "礼拜二": 1,
    "wed": 2,
    "weds": 2,
    "wednesday": 2,
    "周三": 2,
    "星期三": 2,
    "礼拜三": 2,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "thursday": 3,
    "周四": 3,
    "星期四": 3,
    "礼拜四": 3,
    "fri": 4,
    "friday": 4,
    "周五": 4,
    "星期五": 4,
    "礼拜五": 4,
    "sat": 5,
    "saturday": 5,
    "周六": 5,
    "星期六": 5,
    "礼拜六": 5,
    "sun": 6,
    "sunday": 6,
    "周日": 6,
    "周天": 6,
    "星期日": 6,
    "星期天": 6,
    "礼拜日": 6,
    "礼拜天": 6,
}
_WEEKDAY_SPLIT = re.compile(r"[,，;；/、|]+|\s+")

_KIND_MAP = {
    "class": "class",
    "course": "class",
    "课程": "class",
    "上课": "class",
    "课": "class",
    "exam": "exam",
    "考试": "exam",
    "busy": "busy",
    "忙碌": "busy",
    "忙": "busy",
    "other": "other",
    "其他": "other",
    "其它": "other",
}


@dataclass
class ParsedRow:
    row_number: int
    event: ScheduleEvent


@dataclass
class ParseOutcome:
    rows: list[ParsedRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    #: Number of rows rejected by validation (also explained in ``warnings``).
    skipped: int = 0


# -- weekly-grid timetable -------------------------------------------------

_GRID_WEEKDAY_NAMES: dict[str, int] = {
    "星期一": 0,
    "星期二": 1,
    "星期三": 2,
    "星期四": 3,
    "星期五": 4,
    "星期六": 5,
    "星期日": 6,
    "星期天": 6,
}

_PERIOD_RE = re.compile(r"\((\d+)\s*-\s*(\d+)\s*节\)")
_WEEK_TOKEN_RE = re.compile(r"(\d+)\s*-\s*(\d+)\s*周|(\d+)\s*周")

_TERM_START_PATTERNS = (
    re.compile(r"教学周\s*[：:]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"),
    re.compile(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*正式\s*(?:开课|上课)"),
    re.compile(r"本学期\s*[：:]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"),
)

_ROOM_HINTS = ("楼", "室", "馆", "栋", "场", "中心")


def _grid_text(value: object) -> str:
    """Normalise a grid cell while preserving its newline separators."""
    if not isinstance(value, str):
        return ""
    text = value.replace("_x000D_", "\n")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\xa0", " ").replace("\u3000", " ")
    return text


def _grid_field(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _find_grid_header(
    matrix: list[list[object]],
) -> tuple[int, dict[int, int]] | None:
    """Return ``(header_row_index, {column_index: weekday})`` or ``None``."""
    for row_index, row in enumerate(matrix):
        columns = {
            column_index: _GRID_WEEKDAY_NAMES[text]
            for column_index, value in enumerate(row)
            if (text := _clean(value)) in _GRID_WEEKDAY_NAMES
        }
        if len(columns) >= 3:
            return row_index, columns
    return None


def _find_term_start(matrix: list[list[object]]) -> date | None:
    for row in matrix:
        for value in row:
            text = _grid_text(value)
            if not text:
                continue
            for pattern in _TERM_START_PATTERNS:
                match = pattern.search(text)
                if match is None:
                    continue
                try:
                    return parse_date(match.group(1))
                except ValueError:
                    continue
    return None


def _parse_period(value: str) -> tuple[int, int] | None:
    match = _PERIOD_RE.search(value)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def _parse_week_ranges(value: str) -> list[tuple[int, int]]:
    """Turn ``1-7周,9-10周,第13周`` into contiguous ``(start, end)`` ranges."""
    weeks: set[int] = set()
    for match in _WEEK_TOKEN_RE.finditer(value):
        if match.group(1) is not None:
            start, end = int(match.group(1)), int(match.group(2))
        else:
            start = end = int(match.group(3))
        if start < 1 or end < start:
            continue
        weeks.update(range(start, end + 1))
    if not weeks:
        return []
    if "单周" in value:
        weeks = {week for week in weeks if week % 2 == 1}
    elif "双周" in value:
        weeks = {week for week in weeks if week % 2 == 0}
    if not weeks:
        return []

    ordered = sorted(weeks)
    ranges: list[tuple[int, int]] = []
    start = previous = ordered[0]
    for week in ordered[1:]:
        if week == previous + 1:
            previous = week
            continue
        ranges.append((start, previous))
        start = previous = week
    ranges.append((start, previous))
    return ranges


def _looks_like_room(text: str) -> bool:
    return bool(text) and (
        any(hint in text for hint in _ROOM_HINTS) or any(ch.isdigit() for ch in text)
    )


def _campus_room_teacher(fields: list[str]) -> tuple[str, str, str]:
    """Resolve campus / room / teacher for both supported cell layouts.

    * ``校区 / 教室 / 教师`` (the simplified form in the spec).
    * ``"校区 教室" / 教师 / 职称`` (what the real ``test.xlsx`` exports).
    """
    campus_field = fields[2] if len(fields) > 2 else ""
    if " " in campus_field:
        campus, _, room = campus_field.rpartition(" ")
        if _looks_like_room(room):
            teacher = fields[3] if len(fields) > 3 else ""
            return campus.strip(), room.strip(), teacher.strip()
    room = fields[3] if len(fields) > 3 else ""
    teacher = fields[4] if len(fields) > 4 else ""
    return campus_field.strip(), room.strip(), teacher.strip()


def _parse_grid_entry(
    entry: str,
    *,
    weekday: int,
    prefix: str,
    user_id: int,
    source: str,
    term_start: date,
    warnings: list[str],
) -> list[ScheduleEvent]:
    """Parse one ``/``-delimited course block into one event per week range."""
    fields = [_grid_field(part) for part in entry.split("/")]
    if len(fields) < 5:
        warnings.append(
            f"{prefix}: skipped - expected at least 5 '/'-separated fields "
            f"(got {len(fields)})"
        )
        return []

    title = _truncate(fields[0], 255, "title", prefix, warnings)
    if not title:
        warnings.append(f"{prefix}: skipped - course name is required")
        return []

    period_weeks = fields[1]
    period = _parse_period(period_weeks)
    if period is None:
        warnings.append(f"{prefix}: skipped - could not parse period from {period_weeks!r}")
        return []
    times = PERIOD_TIMES.get(period)
    if times is None:
        warnings.append(f"{prefix}: skipped - unsupported period {period[0]}-{period[1]}")
        return []

    ranges = _parse_week_ranges(period_weeks)
    if not ranges:
        warnings.append(f"{prefix}: skipped - could not parse weeks from {period_weeks!r}")
        return []

    campus, room, teacher = _campus_room_teacher(fields)
    location_text = " ".join(part for part in (campus, room) if part)
    location = _truncate(location_text, 255, "location", prefix, warnings) or None
    teacher = _truncate(teacher, 128, "teacher", prefix, warnings) or None

    notes_parts = [period_weeks]
    if len(fields) > 5 and fields[5]:
        notes_parts.append(fields[5])
    if len(fields) > 6 and fields[6]:
        notes_parts.append(fields[6])
    notes = _truncate(" | ".join(notes_parts), 1000, "notes", prefix, warnings) or None

    events: list[ScheduleEvent] = []
    for start_week, end_week in ranges:
        event = ScheduleEvent(
            user_id=user_id,
            title=title,
            event_kind="class",
            start_date=term_start + timedelta(weeks=start_week - 1),
            end_date=term_start + timedelta(weeks=end_week - 1, days=6),
            start_time=times[0],
            end_time=times[1],
            weekdays=[weekday],
            source=source,
            location=location,
            teacher=teacher,
            notes=notes,
        )
        event.external_uid = _stable_uid(event)
        events.append(event)
    return events


def _parse_grid_matrix(
    matrix: list[list[object]],
    *,
    header_index: int,
    columns: dict[int, int],
    user_id: int,
    source: str,
    term_start: date | None,
) -> ParseOutcome:
    outcome = ParseOutcome()
    resolved_start = term_start or _find_term_start(matrix)
    if resolved_start is None:
        outcome.warnings.append(
            "no term start date found (expected e.g. '教学周2026-08-31' or "
            "'本学期2026-08-31正式上课'); supply term_start to import week ranges"
        )

    for row_index, row in enumerate(matrix[header_index + 1 :], start=header_index + 2):
        for column_index, weekday in columns.items():
            if column_index >= len(row):
                continue
            text = _grid_text(row[column_index])
            if not text.strip():
                continue
            prefix = f"cell {get_column_letter(column_index + 1)}{row_index}"
            for entry in text.splitlines():
                entry = entry.strip()
                if not entry:
                    continue
                if resolved_start is None:
                    outcome.skipped += 1
                    continue
                try:
                    events = _parse_grid_entry(
                        entry,
                        weekday=weekday,
                        prefix=prefix,
                        user_id=user_id,
                        source=source,
                        term_start=resolved_start,
                        warnings=outcome.warnings,
                    )
                except Exception as exc:  # noqa: BLE001 - one bad cell must not abort
                    outcome.warnings.append(f"{prefix}: skipped - {exc}")
                    outcome.skipped += 1
                    continue
                if not events:
                    outcome.skipped += 1
                    continue
                outcome.rows.extend(
                    ParsedRow(row_number=row_index, event=event) for event in events
                )
    return outcome


# -- primitive parsers -----------------------------------------------------


def parse_weekdays(value: object) -> list[int]:
    """Parse one or more weekdays into ``0..6`` (Monday=0)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return []
    if isinstance(value, bool):
        raise ValueError("invalid weekday")
    if isinstance(value, (int, float)):
        number = int(value)
        if 0 <= number <= 6:
            return [number]
        if 1 <= number <= 7:
            return [number - 1]
        raise ValueError(f"weekday out of range: {number}")

    text = _clean(value).lower().replace("每", "")
    tokens = [token for token in _WEEKDAY_SPLIT.split(text) if token]
    if not tokens:
        raise ValueError(f"invalid weekday: {value!r}")

    days: list[int] = []
    bad: list[str] = []
    for token in tokens:
        token = token.strip()
        if token.isdigit():
            number = int(token)
            if 1 <= number <= 7:
                days.append(number - 1)
            elif number == 0:
                days.append(0)
            else:
                bad.append(token)
            continue
        if token in _WEEKDAY_MAP:
            days.append(_WEEKDAY_MAP[token])
        else:
            bad.append(token)

    if bad:
        raise ValueError(f"invalid weekday: {', '.join(bad)}")
    return sorted(set(days))


def parse_recurrence(value: object) -> list[int] | None:
    """Best-effort weekday extraction from a free-form recurrence column."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    text = _clean(value).lower().replace(" ", "")
    if text in {"daily", "everyday", "每天", "每日", "天天"}:
        return list(range(7))
    if text in {"weekday", "weekdays", "工作日"}:
        return [0, 1, 2, 3, 4]
    if text in {"weekend", "weekends", "周末"}:
        return [5, 6]
    try:
        return parse_weekdays(value)
    except ValueError:
        # "weekly" / "每周" only say that the weekday column applies.
        return None


def _time_from_fraction(value: float) -> time:
    seconds = round(float(value) * 24 * 60 * 60) % (24 * 60 * 60)
    return time(seconds // 3600, (seconds % 3600) // 60, seconds % 60)


def parse_time(value: object) -> time | None:
    """Parse a time cell/string; ``None`` means "not provided"."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.time().replace(microsecond=0)
    if isinstance(value, time):
        return value.replace(microsecond=0)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if 0 <= number < 1:
            return _time_from_fraction(number)
        if 0 <= number <= 23 and number == int(number):
            return time(int(number), 0)
        return _time_from_fraction(number)

    text = _clean(value).replace("：", ":")
    if not text:
        return None
    parts = text.split(":")
    if len(parts) not in (2, 3) or not all(part.isdigit() for part in parts):
        raise ValueError(f"invalid time: {value!r}")
    hour, minute = int(parts[0]), int(parts[1])
    second = int(parts[2]) if len(parts) == 3 else 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        raise ValueError(f"invalid time: {value!r}")
    return time(hour, minute, second)


_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d", "%m/%d/%Y")


def parse_date(value: object) -> date | None:
    """Parse ISO / ``YYYY/MM/DD`` / Excel date cells; ``None`` when empty."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        converted = from_excel(float(value))
        if isinstance(converted, datetime):
            return converted.date()
        if isinstance(converted, date):
            return converted
        raise ValueError(f"invalid date: {value!r}")

    text = _clean(value).replace("／", "/")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"invalid date: {value!r}")


# -- file readers ----------------------------------------------------------


def _decode_csv(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DomainValidationError(
        "could not decode the CSV file; save it as UTF-8 or GB18030"
    )


def _csv_rows(content: bytes) -> list[tuple[int, dict[str, object]]]:
    text = _decode_csv(content)
    if not text.strip():
        raise DomainValidationError("the uploaded file is empty")

    try:
        dialect: type[csv.Dialect] | csv.Dialect = csv.Sniffer().sniff(
            text[:4096], delimiters=",;\t"
        )
    except csv.Error:
        dialect = csv.excel

    reader = csv.reader(io.StringIO(text), dialect)
    raw_rows = list(reader)
    if not raw_rows:
        raise DomainValidationError("the uploaded file is empty")
    return _rows_from_matrix(raw_rows)


def _xlsx_matrix(content: bytes) -> list[list[object]]:
    try:
        workbook = load_workbook(
            io.BytesIO(content), read_only=True, data_only=True
        )
    except Exception as exc:  # noqa: BLE001 - corrupt files are user errors
        raise DomainValidationError(f"could not read the XLSX file: {exc}") from exc

    try:
        sheet = workbook.active
        if sheet is None:
            raise DomainValidationError("the workbook has no worksheet")
        return [list(row) for row in sheet.iter_rows(values_only=True)]
    finally:
        workbook.close()


def _xlsx_rows(content: bytes) -> list[tuple[int, dict[str, object]]]:
    matrix = _xlsx_matrix(content)
    if not matrix:
        raise DomainValidationError("the uploaded file is empty")
    return _rows_from_matrix(matrix)


def _rows_from_matrix(
    matrix: list[list[object]],
) -> list[tuple[int, dict[str, object]]]:
    header = matrix[0] if matrix else []
    canonical = [_HEADER_LOOKUP.get(_normalize_header(cell)) for cell in header]

    rows: list[tuple[int, dict[str, object]]] = []
    for row_number, values in enumerate(matrix[1:], start=2):
        row: dict[str, object] = {}
        for index, key in enumerate(canonical):
            if key is None or key in row or index >= len(values):
                continue
            row[key] = values[index]
        if not any(_clean(value) for value in row.values()):
            continue  # blank line
        rows.append((row_number, row))
        if len(rows) > MAX_ROWS:
            raise DomainValidationError(
                f"too many rows: the import limit is {MAX_ROWS} rows"
            )
    return rows


def read_rows(content: bytes, filename: str) -> tuple[list[tuple[int, dict[str, object]]], str]:
    """Return ``(rows, source)`` for a CSV/XLSX upload."""
    if len(content) > MAX_FILE_BYTES:
        raise DomainValidationError(
            f"file is too large: the limit is {MAX_FILE_BYTES // (1024 * 1024)} MB"
        )

    suffix = Path(filename or "").suffix.lower()
    if suffix == ".xls":
        raise DomainValidationError(
            "legacy .xls files are not supported; save the timetable as .xlsx"
        )
    if suffix == ".csv":
        return _csv_rows(content), "csv"
    if suffix == ".xlsx":
        return _xlsx_rows(content), "xlsx"
    raise DomainValidationError(
        "unsupported file type; upload a .csv or .xlsx timetable"
    )


# -- row validation --------------------------------------------------------


def _stable_uid(event: ScheduleEvent) -> str:
    weekdays = ",".join(str(day) for day in sorted(event.weekdays or []))
    parts = [
        event.title.strip().lower(),
        event.event_kind,
        event.start_date.isoformat() if event.start_date else "",
        event.end_date.isoformat() if event.end_date else "",
        event.start_time.strftime("%H:%M:%S"),
        event.end_time.strftime("%H:%M:%S"),
        weekdays,
        (event.location or "").strip().lower(),
    ]
    # Appending the teacher only when present keeps the UID of flat CSV/XLSX
    # rows (which have no teacher) unchanged across upgrades.
    if event.teacher:
        parts.append(event.teacher.strip().lower())
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"auto-{digest[:32]}"


def _parse_kind(value: object) -> tuple[str, str | None]:
    text = _clean(value).lower()
    if not text:
        return "class", None
    if text in _KIND_MAP:
        return _KIND_MAP[text], None
    return "other", f"unknown kind {text!r}; stored as 'other'"


def _truncate(text: str, limit: int, label: str, warning_prefix: str, warnings: list[str]) -> str:
    if len(text) <= limit:
        return text
    warnings.append(
        f"{warning_prefix}: {label} was longer than {limit} characters and was truncated"
    )
    return text[:limit]


def _parse_row(
    values: dict[str, object],
    *,
    row_number: int,
    user_id: int,
    source: str,
) -> tuple[ScheduleEvent | None, list[str]]:
    prefix = f"row {row_number}"
    warnings: list[str] = []

    title = _clean(values.get(TITLE))
    if not title:
        return None, [f"{prefix}: skipped - title is required"]
    title = _truncate(title, 255, "title", prefix, warnings)

    try:
        start_time = parse_time(values.get(START))
        end_time = parse_time(values.get(END))
    except ValueError as exc:
        return None, [f"{prefix}: skipped - {exc}"]
    if start_time is None or end_time is None:
        return None, [f"{prefix}: skipped - start and end times are required"]
    if end_time <= start_time:
        return None, [f"{prefix}: skipped - end time must be after start time"]

    try:
        start_date = parse_date(values.get(DATE))
        end_date = start_date
    except ValueError as exc:
        return None, [f"{prefix}: skipped - {exc}"]

    weekdays: list[int] | None = None
    weekday_value = values.get(WEEKDAY)
    if _clean(weekday_value):
        try:
            weekdays = parse_weekdays(weekday_value) or None
        except ValueError as exc:
            return None, [f"{prefix}: skipped - {exc}"]
    elif _clean(values.get(RECURRENCE)):
        weekdays = parse_recurrence(values.get(RECURRENCE))

    if start_date is not None and end_date is not None and start_date > end_date:
        return None, [f"{prefix}: skipped - start date is after end date"]

    event_kind, kind_warning = _parse_kind(values.get(KIND))
    if kind_warning:
        warnings.append(f"{prefix}: {kind_warning}")

    location = _truncate(
        _clean(values.get(LOCATION)), 255, "location", prefix, warnings
    ) or None
    notes = _truncate(
        _clean(values.get(NOTES)), 1000, "notes", prefix, warnings
    ) or None

    uid = _clean(values.get(UID))
    if uid:
        uid = _truncate(uid, 128, "uid", prefix, warnings)
    if not weekdays and start_date is None:
        warnings.append(
            f"{prefix}: no date or weekday given; the event is stored but will "
            "not block any slots"
        )

    event = ScheduleEvent(
        user_id=user_id,
        title=title,
        event_kind=event_kind,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        weekdays=weekdays,
        source=source,
        external_uid=uid or None,
        location=location,
        notes=notes,
    )
    event.external_uid = event.external_uid or _stable_uid(event)
    return event, warnings


def _parse_flat_rows(
    rows: list[tuple[int, dict[str, object]]], *, source: str, user_id: int
) -> ParseOutcome:
    outcome = ParseOutcome()
    if not rows:
        outcome.warnings.append("the file contains a header but no data rows")
        return outcome

    for row_number, values in rows:
        try:
            event, warnings = _parse_row(
                values, row_number=row_number, user_id=user_id, source=source
            )
        except Exception as exc:  # noqa: BLE001 - one bad row must not abort
            outcome.warnings.append(f"row {row_number}: skipped - {exc}")
            continue
        outcome.warnings.extend(warnings)
        if event is not None:
            outcome.rows.append(ParsedRow(row_number=row_number, event=event))
        else:
            outcome.skipped += 1
    return outcome


def parse_schedule_file(
    content: bytes,
    *,
    filename: str,
    user_id: int,
    term_start: date | None = None,
) -> ParseOutcome:
    """Parse an uploaded CSV/XLSX timetable into validated events.

    Plain CSV and flat XLSX tables use the header-based importer. An XLSX whose
    matrix contains a weekday header row (``星期一..星期日``) is treated as a
    weekly-grid timetable; ``term_start`` overrides the term date found in the
    sheet.
    """
    if len(content) > MAX_FILE_BYTES:
        raise DomainValidationError(
            f"file is too large: the limit is {MAX_FILE_BYTES // (1024 * 1024)} MB"
        )

    suffix = Path(filename or "").suffix.lower()
    if suffix == ".xls":
        raise DomainValidationError(
            "legacy .xls files are not supported; save the timetable as .xlsx"
        )
    if suffix == ".csv":
        return _parse_flat_rows(_csv_rows(content), source="csv", user_id=user_id)
    if suffix == ".xlsx":
        matrix = _xlsx_matrix(content)
        if not matrix:
            raise DomainValidationError("the uploaded file is empty")
        header = _find_grid_header(matrix)
        if header is not None:
            header_index, columns = header
            return _parse_grid_matrix(
                matrix,
                header_index=header_index,
                columns=columns,
                user_id=user_id,
                source="xlsx",
                term_start=term_start,
            )
        return _parse_flat_rows(
            _rows_from_matrix(matrix), source="xlsx", user_id=user_id
        )
    raise DomainValidationError(
        "unsupported file type; upload a .csv or .xlsx timetable"
    )


__all__ = [
    "HEADER_ALIASES",
    "MAX_FILE_BYTES",
    "MAX_ROWS",
    "PERIOD_TIMES",
    "ParseOutcome",
    "ParsedRow",
    "parse_date",
    "parse_recurrence",
    "parse_schedule_file",
    "parse_time",
    "parse_weekdays",
    "read_rows",
]
