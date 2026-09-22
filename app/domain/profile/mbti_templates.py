"""MBTI template tables for the user-profile engine.

全部数值为【工程】待校准 (all numeric values are engineering estimates): they
encode MBTI-type stereotypes and must be calibrated against real user feedback
once the feedback loop accumulates data (see ``docs/research/RO-2-模型体系.md``
§4.1.2b for the coefficient provenance of ``TYPE_MULTIPLIER``).

Template schema (exactly 8 keys per type):
    duration_factor        float  0.8-1.6   per-type time multiplier
    completion_prob        float  0-1       prior completion probability
    stress_baseline        float  0-1       resting stress level
    energy_drain_rate      float  0-1       energy consumed per task unit
    proactive_score        float  0-1       how eagerly the user starts work
    procrastination_tendency float 0-1      tendency to delay execution
    preferred_time_slots   dict   {"high","medium","low","restorative"} ->
                                   {"morning","afternoon","evening","night"}
    stress_response        float  0-1       sensitivity of stress to load
"""

from __future__ import annotations

from typing import Any

#: Valid MBTI type codes (uppercase), the 16 real types minus ``_default``.
VALID_MBTI_TYPES: frozenset[str] = frozenset(
    t
    for t in (
        "ISTJ", "ISFJ", "INFJ", "INTJ",
        "ISTP", "ISFP", "INFP", "INTP",
        "ESTP", "ESFP", "ENFP", "ENTP",
        "ESTJ", "ESFJ", "ENFJ", "ENTJ",
    )
)

#: The four MBTI dimension axes, in positional order.
MBTI_DIMENSIONS: tuple[str, ...] = ("ie", "sn", "tf", "jp")

#: Letter pair for each dimension: first letter wins when weight >= 0.5.
DIMENSION_LETTERS: dict[str, tuple[str, str]] = {
    "ie": ("I", "E"),
    "sn": ("S", "N"),
    "tf": ("T", "F"),
    "jp": ("J", "P"),
}

#: Per-task-type theoretical-time multiplier (RO-2 §4.1.2b, 【工程】).
TYPE_MULTIPLIER: dict[str, float] = {
    "concept": 1.2,
    "example": 1.1,
    "practice": 1.3,
    "review": 0.6,
    "project": 1.8,
}

#: Preferred-time-slot labels per load level (values are ``TimeOfDay`` names).
_SLOT_KEYS: tuple[str, ...] = ("high", "medium", "low", "restorative")
_SLOT_VALUES: tuple[str, ...] = ("morning", "afternoon", "evening", "night")


def _slots(high: str, medium: str, low: str, restorative: str) -> dict[str, str]:
    """Build a validated 4-key time-slot dict."""
    return {
        "high": high,
        "medium": medium,
        "low": low,
        "restorative": restorative,
    }


#: Stereotyped engineering defaults for all 16 MBTI types plus ``_default``.
#: Heuristics used when picking values:
#:   * J types -> lower ``duration_factor`` and ``procrastination_tendency``;
#:     P types -> higher both.
#:   * E types -> higher ``proactive_score``; I types -> evening/night slots.
#:   * high-N types -> higher ``stress_baseline`` and ``energy_drain_rate``.
#:   * S types -> lower ``stress_baseline``; F types -> higher stress_response.
MBTI_TEMPLATES: dict[str, dict[str, Any]] = {
    "_default": {
        "duration_factor": 1.3,
        "completion_prob": 0.7,
        "stress_baseline": 0.5,
        "energy_drain_rate": 0.5,
        "proactive_score": 0.5,
        "procrastination_tendency": 0.5,
        "preferred_time_slots": _slots("morning", "afternoon", "evening", "night"),
        "stress_response": 0.5,
    },
    "ISTJ": {
        "duration_factor": 1.0,
        "completion_prob": 0.85,
        "stress_baseline": 0.45,
        "energy_drain_rate": 0.45,
        "proactive_score": 0.45,
        "procrastination_tendency": 0.25,
        "preferred_time_slots": _slots("morning", "morning", "afternoon", "evening"),
        "stress_response": 0.5,
    },
    "ISFJ": {
        "duration_factor": 1.05,
        "completion_prob": 0.85,
        "stress_baseline": 0.5,
        "energy_drain_rate": 0.5,
        "proactive_score": 0.45,
        "procrastination_tendency": 0.3,
        "preferred_time_slots": _slots("morning", "afternoon", "evening", "evening"),
        "stress_response": 0.55,
    },
    "INFJ": {
        "duration_factor": 1.15,
        "completion_prob": 0.8,
        "stress_baseline": 0.65,
        "energy_drain_rate": 0.6,
        "proactive_score": 0.45,
        "procrastination_tendency": 0.35,
        "preferred_time_slots": _slots("morning", "morning", "evening", "night"),
        "stress_response": 0.6,
    },
    "INTJ": {
        "duration_factor": 1.1,
        "completion_prob": 0.85,
        "stress_baseline": 0.6,
        "energy_drain_rate": 0.55,
        "proactive_score": 0.5,
        "procrastination_tendency": 0.3,
        "preferred_time_slots": _slots("morning", "morning", "evening", "night"),
        "stress_response": 0.5,
    },
    "ISTP": {
        "duration_factor": 1.3,
        "completion_prob": 0.75,
        "stress_baseline": 0.45,
        "energy_drain_rate": 0.45,
        "proactive_score": 0.45,
        "procrastination_tendency": 0.55,
        "preferred_time_slots": _slots("afternoon", "afternoon", "evening", "night"),
        "stress_response": 0.45,
    },
    "ISFP": {
        "duration_factor": 1.35,
        "completion_prob": 0.7,
        "stress_baseline": 0.5,
        "energy_drain_rate": 0.5,
        "proactive_score": 0.4,
        "procrastination_tendency": 0.6,
        "preferred_time_slots": _slots("afternoon", "afternoon", "evening", "evening"),
        "stress_response": 0.55,
    },
    "INFP": {
        "duration_factor": 1.4,
        "completion_prob": 0.65,
        "stress_baseline": 0.65,
        "energy_drain_rate": 0.6,
        "proactive_score": 0.4,
        "procrastination_tendency": 0.7,
        "preferred_time_slots": _slots("evening", "evening", "afternoon", "night"),
        "stress_response": 0.65,
    },
    "INTP": {
        "duration_factor": 1.4,
        "completion_prob": 0.65,
        "stress_baseline": 0.6,
        "energy_drain_rate": 0.55,
        "proactive_score": 0.4,
        "procrastination_tendency": 0.7,
        "preferred_time_slots": _slots("evening", "evening", "afternoon", "night"),
        "stress_response": 0.55,
    },
    "ESTP": {
        "duration_factor": 1.2,
        "completion_prob": 0.75,
        "stress_baseline": 0.4,
        "energy_drain_rate": 0.5,
        "proactive_score": 0.65,
        "procrastination_tendency": 0.5,
        "preferred_time_slots": _slots("morning", "afternoon", "afternoon", "evening"),
        "stress_response": 0.4,
    },
    "ESFP": {
        "duration_factor": 1.3,
        "completion_prob": 0.7,
        "stress_baseline": 0.45,
        "energy_drain_rate": 0.55,
        "proactive_score": 0.65,
        "procrastination_tendency": 0.6,
        "preferred_time_slots": _slots("afternoon", "afternoon", "evening", "evening"),
        "stress_response": 0.5,
    },
    "ENFP": {
        "duration_factor": 1.35,
        "completion_prob": 0.65,
        "stress_baseline": 0.6,
        "energy_drain_rate": 0.65,
        "proactive_score": 0.7,
        "procrastination_tendency": 0.7,
        "preferred_time_slots": _slots("afternoon", "morning", "evening", "night"),
        "stress_response": 0.6,
    },
    "ENTP": {
        "duration_factor": 1.35,
        "completion_prob": 0.65,
        "stress_baseline": 0.55,
        "energy_drain_rate": 0.6,
        "proactive_score": 0.7,
        "procrastination_tendency": 0.7,
        "preferred_time_slots": _slots("afternoon", "morning", "evening", "night"),
        "stress_response": 0.5,
    },
    "ESTJ": {
        "duration_factor": 0.95,
        "completion_prob": 0.9,
        "stress_baseline": 0.4,
        "energy_drain_rate": 0.45,
        "proactive_score": 0.7,
        "procrastination_tendency": 0.2,
        "preferred_time_slots": _slots("morning", "morning", "afternoon", "evening"),
        "stress_response": 0.4,
    },
    "ESFJ": {
        "duration_factor": 1.0,
        "completion_prob": 0.85,
        "stress_baseline": 0.45,
        "energy_drain_rate": 0.5,
        "proactive_score": 0.65,
        "procrastination_tendency": 0.25,
        "preferred_time_slots": _slots("morning", "morning", "afternoon", "evening"),
        "stress_response": 0.55,
    },
    "ENFJ": {
        "duration_factor": 1.1,
        "completion_prob": 0.8,
        "stress_baseline": 0.55,
        "energy_drain_rate": 0.6,
        "proactive_score": 0.75,
        "procrastination_tendency": 0.3,
        "preferred_time_slots": _slots("morning", "morning", "afternoon", "evening"),
        "stress_response": 0.6,
    },
    "ENTJ": {
        "duration_factor": 1.05,
        "completion_prob": 0.85,
        "stress_baseline": 0.5,
        "energy_drain_rate": 0.55,
        "proactive_score": 0.8,
        "procrastination_tendency": 0.2,
        "preferred_time_slots": _slots("morning", "morning", "afternoon", "evening"),
        "stress_response": 0.45,
    },
}
