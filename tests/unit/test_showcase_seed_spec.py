"""Pure specification checks for the showcase seed (no DB writes)."""

from __future__ import annotations

from collections import Counter, defaultdict
from types import SimpleNamespace

from scripts.seed_showcase_account import (
    FUTURE_DAYS,
    HISTORY_DAYS,
    HISTORY_END,
    HISTORY_START,
    PLAN_END,
    PREFERENCES,
    _task_specs,
)


def _goals() -> dict[str, SimpleNamespace]:
    return {
        "english": SimpleNamespace(id=1),
        "math": SimpleNamespace(id=2),
        "algorithm": SimpleNamespace(id=3),
        "os": SimpleNamespace(id=4),
        "damn": SimpleNamespace(id=5),
        "review": SimpleNamespace(id=6),
    }


def test_showcase_spec_has_expected_task_shape() -> None:
    specs = _task_specs(_goals())

    assert len(specs) == 74
    assert sum(1 for spec in specs if spec.day <= HISTORY_END) == 48
    assert sum(1 for spec in specs if spec.day > HISTORY_END) == 26
    assert {spec.day for spec in specs} <= set(HISTORY_DAYS) | set(FUTURE_DAYS)

    by_goal = Counter(spec.goal_id for spec in specs)
    assert by_goal == {1: 22, 2: 18, 3: 2, 4: 2, 5: 8, 6: 22}

    recurring = [spec for spec in specs if spec.series_id is not None]
    assert len(recurring) == 44
    assert all(spec.occurrence_date == spec.day for spec in recurring)
    assert all(spec.work_unit_key is None for spec in recurring)

    work_units = [spec for spec in specs if spec.work_unit_key is not None]
    assert len(work_units) == 30
    assert len({spec.work_unit_key for spec in work_units}) == 12
    assert Counter(spec.work_unit_key for spec in work_units if spec.goal_id == 2) == {
        f"wg-2-project-{index}": 3 for index in range(6)
    }
    assert Counter(spec.work_unit_key for spec in work_units if spec.goal_id == 5) == {
        f"wg-5-project-{index}": 2 for index in range(4)
    }

    assert PREFERENCES["available_minutes_per_day"] == 720
    assert PREFERENCES["daily_limit_minutes"] == 300
    assert PREFERENCES["max_daily_minutes_per_goal"] == 120


def test_showcase_spec_respects_daily_goal_and_subject_budget() -> None:
    specs = _task_specs(_goals())
    per_goal_day: dict[tuple[int, object], int] = defaultdict(int)
    per_day: dict[object, int] = defaultdict(int)
    high_per_day: dict[object, int] = defaultdict(int)
    subjects_by_day: dict[object, set[str]] = defaultdict(set)

    for spec in specs:
        per_goal_day[(spec.goal_id, spec.day)] += spec.minutes
        per_day[spec.day] += spec.minutes
        subjects_by_day[spec.day].add(spec.subject)
        if spec.load.value == "high":
            high_per_day[spec.day] += 1

    assert max(per_goal_day.values()) <= 120
    assert max(per_day.values()) <= 300
    assert max(high_per_day.values()) <= 2
    for day, subjects in subjects_by_day.items():
        if "algorithm" in subjects:
            assert "math" not in subjects, day

    assert min(spec.day for spec in specs) == HISTORY_START
    assert max(spec.day for spec in specs) == PLAN_END
