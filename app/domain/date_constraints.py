"""Deterministic extraction of explicit earliest-start constraints.

A user's explicit "after / from / not before <date>" is a hard scheduling fact,
not a prompt suggestion. This module turns only the supported expressions into
a structured date; ambiguous partial dates fail closed instead of being silently
ignored.

Semantics
---------
* exclusive (``之后`` / ``以后`` / ``after``): the next calendar day is allowed;
* inclusive (``不早于`` / ``从...开始`` / ``not before`` / ``from``): the named
  day itself is allowed.

The parser never reads or rewrites the source text; callers keep the original
title/description as the evidence.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta


class DateConstraintError(ValueError):
    """An explicit date constraint exists but cannot be parsed safely."""


_FULL_DATE = re.compile(
    r"(?<!\d)(?P<year>\d{4})\s*[-/.年]\s*(?P<month>\d{1,2})\s*"
    r"[-/.月]\s*(?P<day>\d{1,2})\s*[日号]?(?!\d)"
)
_MONTH_DAY = re.compile(
    r"(?<![\d年])(?P<month>\d{1,2})\s*月\s*(?P<day>\d{1,2})\s*[日号]?"
)
#: A partial date (year-month or month only). It is not schedulable by itself,
#: but if a constraint marker is attached it must fail closed.
_PARTIAL_DATE = re.compile(
    r"(?<!\d)(?P<year>\d{4})\s*[-/.]\s*(?P<month>\d{1,2})(?!\s*[-/.]\s*\d)"
    r"|(?<![\d年])(?P<month_only>\d{1,2})\s*月(?!\s*\d)"
)

_EXCLUSIVE_SUFFIX = ("之后", "以后", "过后")
_INCLUSIVE_SUFFIX = ("开始", "起")


def _source_suffix(source: str | None) -> str:
    return f" [source: {source}]" if source else ""


def _fragment(text: str, match: re.Match[str] | None = None) -> str:
    if match is None:
        return text.strip().replace("\n", " ")[:120]
    return (
        text[max(0, match.start() - 20) : match.end() + 20]
        .replace("\n", " ")
        .strip()
    )


def _classify_semantics(
    text: str, start: int, end: int, *, source: str | None = None
) -> str | None:
    """Return ``"exclusive"``, ``"inclusive"`` or ``None`` for one date token."""
    before = text[max(0, start - 24) : start].lower()
    after = text[end : end + 24].lstrip().lower()

    exclusive = False
    inclusive = False
    if after.startswith(_EXCLUSIVE_SUFFIX) or re.match(r"^后(?!\w)", after):
        exclusive = True
    if re.search(r"(?:晚于|迟于|after)\s*$", before):
        exclusive = True
    if re.search(r"(?:不早于|not\s+before|on\s+or\s+after)\s*$", before):
        inclusive = True
    if re.search(r"(?:从|自|from)\s*$", before):
        inclusive = True
    if after.startswith(_INCLUSIVE_SUFFIX):
        inclusive = True

    if exclusive and inclusive:
        raise DateConstraintError(
            "date constraint contains both exclusive and inclusive wording "
            f"near {_fragment(text, _Span(start, end))!r}"
            f"{_source_suffix(source)}"
        )
    if exclusive:
        return "exclusive"
    if inclusive:
        return "inclusive"
    return None


class _Span:
    """Small adapter so ``_fragment`` can accept a start/end pair."""

    def __init__(self, start: int, end: int) -> None:
        self._start = start
        self._end = end

    def start(self) -> int:
        return self._start

    def end(self) -> int:
        return self._end


def _year_for_month_day(
    month: int, day: int, *, deadline: date | None, reference: date
) -> date:
    """Resolve an omitted year from the goal deadline then the plan reference.

    Deterministic rule:
    * with a deadline, use the deadline's year; if that would fall after the
      deadline, use the previous year (e.g. deadline 2027-01-05 + "12月20日");
    * without a deadline, use the reference year; if the date is already past,
      use the next year (the next occurrence).
    """
    if deadline is not None:
        candidate = date(deadline.year, month, day)
        if candidate > deadline:
            candidate = date(deadline.year - 1, month, day)
        return candidate
    candidate = date(reference.year, month, day)
    if candidate < reference:
        candidate = date(reference.year + 1, month, day)
    return candidate


def _date_from_match(
    match: re.Match[str],
    *,
    deadline: date | None,
    reference: date,
    source: str | None = None,
) -> date:
    try:
        month = int(match.group("month"))
        day = int(match.group("day"))
        raw_year = match.groupdict().get("year")
        if raw_year is not None:
            return date(int(raw_year), month, day)
        return _year_for_month_day(
            month, day, deadline=deadline, reference=reference
        )
    except ValueError as exc:  # invalid calendar date (e.g. 2026-02-30)
        raise DateConstraintError(
            f"invalid calendar date: {match.group(0)!r}"
            f"{_source_suffix(source)}"
        ) from exc


def parse_earliest_start(
    text: str | None,
    *,
    deadline: date | None = None,
    reference: date | None = None,
    source: str | None = None,
) -> date | None:
    """Return the first allowed day from explicit constraint text, if any.

    Raises :class:`DateConstraintError` when a constraint marker is attached to
    a date token that cannot be parsed safely (for example a partial
    ``11月之后``). A date mentioned without an adjacent constraint marker is not
    treated as an earliest-start constraint.
    """
    if not text:
        return None
    normalised = unicodedata.normalize("NFKC", text)
    reference = reference or date.today()

    dated: list[tuple[re.Match[str], str]] = []
    spans: list[tuple[int, int]] = []
    for match in _FULL_DATE.finditer(normalised):
        dated.append((match, "full"))
        spans.append(match.span())
    for match in _MONTH_DAY.finditer(normalised):
        if any(start <= match.start() and match.end() <= end for start, end in spans):
            continue
        dated.append((match, "month_day"))
        spans.append(match.span())

    partials: list[re.Match[str]] = []
    for match in _PARTIAL_DATE.finditer(normalised):
        if any(start <= match.start() and match.end() <= end for start, end in spans):
            continue
        partials.append(match)

    earliest: date | None = None
    for match, _kind in dated:
        semantics = _classify_semantics(
            normalised, match.start(), match.end(), source=source
        )
        if semantics is None:
            continue
        candidate = _date_from_match(
            match, deadline=deadline, reference=reference, source=source
        )
        if semantics == "exclusive":
            candidate = candidate + timedelta(days=1)
        earliest = candidate if earliest is None else max(earliest, candidate)

    # A partial date plus an attached constraint is a real but unsafe
    # constraint (e.g. "11月之后"): fail closed with the goal/source context.
    for match in partials:
        semantics = _classify_semantics(
            normalised, match.start(), match.end(), source=source
        )
        if semantics is not None:
            raise DateConstraintError(
                "an explicit date constraint was found but could not be parsed "
                f"reliably; near {_fragment(normalised, match)!r}"
                f"{_source_suffix(source)}"
            )
    return earliest


def resolve_earliest_start(
    explicit: date | None,
    *,
    text: str | None,
    deadline: date | None,
    reference: date | None = None,
    source: str | None = None,
) -> date | None:
    """Combine an explicit structured start with any text constraint.

    The later day wins. Raises when the result would be later than the
    (inclusive) deadline.
    """
    reference = reference or date.today()
    parsed = parse_earliest_start(
        text,
        deadline=deadline,
        reference=reference,
        source=source,
    )
    values = [day for day in (explicit, parsed) if day is not None]
    earliest = max(values) if values else None
    if earliest is not None and deadline is not None and earliest > deadline:
        raise DateConstraintError(
            f"earliest start {earliest.isoformat()} is after deadline "
            f"{deadline.isoformat()}{_source_suffix(source)}"
        )
    return earliest


__all__ = [
    "DateConstraintError",
    "parse_earliest_start",
    "resolve_earliest_start",
]
