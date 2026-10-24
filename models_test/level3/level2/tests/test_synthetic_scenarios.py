from __future__ import annotations

from datetime import date

import pytest
from ddsr.config import DDSRConfig
from ddsr.engine import DDSREngine
from ddsr.schemas import EvidenceType, ReflectionInput
from ddsr.trait_context import TraitContext
from helpers import day, execution, plan, trait_profile

CURRENT = date(2026, 10, 20)


def run(days):
    return DDSREngine(DDSRConfig()).replay(days, TraitContext.from_profile(trait_profile()))


def test_high_completion_low_fatigue():
    profile = run(
        [
            day(
                CURRENT,
                plans=[plan("t1", day=CURRENT), plan("t2", day=CURRENT, hour=10, duration=30)],
                executions=[
                    execution("t1", day=CURRENT, completion=1.0, completed=True),
                    execution("t2", day=CURRENT, start_hour=10, completion=1.0, completed=True),
                ],
                reflection=ReflectionInput(
                    state_review="今天精力充沛，不累，心情放松。",
                    tomorrow_outlook="明天我有把握完成。",
                ),
            )
        ]
    )[0]
    assert profile.behavioral_indicators.goal_attainment.value == pytest.approx(1.0)
    assert profile.self_efficacy.value > profile.self_efficacy.prior
    assert profile.fatigue.value < profile.fatigue.prior
    assert profile.stress.value < profile.stress.prior


def test_high_start_delay_due_to_external_event_is_not_procrastination():
    profile = run(
        [
            day(
                CURRENT,
                plans=[plan("t1", day=CURRENT, hour=9)],
                executions=[
                    execution(
                        "t1",
                        day=CURRENT,
                        start_hour=11,
                        duration=30,
                        completion=0.5,
                        completed=False,
                        interruptions=2,
                    )
                ],
                reflection=ReflectionInput(
                    stuck_points="本来九点要开始，但临时开会，后来又被电话打断，不是拖延。"
                ),
            )
        ]
    )[0]
    indicator = profile.behavioral_indicators.procrastination_evidence
    assert indicator.confirmed == []
    assert indicator.candidate_task_ids == ["t1"]
    assert indicator.late_start_candidate_count == 1
    assert any(
        item.evidence_type is EvidenceType.INTERRUPTION
        for item in profile.evidence.evidence_items
    )
    assert not any(
        item.evidence_type is EvidenceType.PROCRASTINATION
        for item in profile.evidence.evidence_items
    )
    # Interruption and late start are not state evidence.
    assert profile.fatigue.value == pytest.approx(profile.fatigue.prior)
    assert profile.stress.value == pytest.approx(profile.stress.prior)
    assert profile.self_efficacy.value == pytest.approx(profile.self_efficacy.prior)


def test_high_start_delay_with_explicit_avoidance_is_procrastination():
    profile = run(
        [
            day(
                CURRENT,
                plans=[plan("t1", day=CURRENT, hour=9)],
                executions=[
                    execution(
                        "t1",
                        day=CURRENT,
                        start_hour=11,
                        duration=30,
                        completion=0.2,
                        completed=False,
                    )
                ],
                reflection=ReflectionInput(
                    stuck_points="我一直在拖延，明知道该做却不想开始，主动逃避了。"
                ),
            )
        ]
    )[0]
    confirmed = profile.behavioral_indicators.procrastination_evidence.confirmed
    assert len(confirmed) == 1
    assert confirmed[0].voluntary is True
    assert confirmed[0].cause_category.value == "avoidance"
    assert profile.behavioral_indicators.procrastination_evidence.candidate_task_ids == ["t1"]


def test_high_fatigue_low_completion():
    profile = run(
        [
            day(
                CURRENT,
                plans=[plan("t1", day=CURRENT)],
                executions=[
                    execution(
                        "t1",
                        day=CURRENT,
                        duration=20,
                        completion=0.2,
                        completed=False,
                    )
                ],
                reflection=ReflectionInput(
                    state_review="今天特别累，精疲力尽，压力很大，完全没精神。"
                ),
            )
        ]
    )[0]
    assert profile.fatigue.value > profile.fatigue.prior
    assert profile.stress.value > profile.stress.prior
    assert profile.self_efficacy.value < profile.self_efficacy.prior


def test_failure_today_but_high_self_efficacy_for_tomorrow():
    profile = run(
        [
            day(
                CURRENT,
                plans=[plan("t1", day=CURRENT)],
                executions=[
                    execution(
                        "t1",
                        day=CURRENT,
                        duration=10,
                        completion=0.1,
                        completed=False,
                    )
                ],
                reflection=ReflectionInput(
                    day_review="今天任务基本没完成。",
                    state_review="今天有点累。",
                    tomorrow_outlook="明天我有把握完成，能搞定。",
                ),
            )
        ]
    )[0]
    assert profile.behavioral_indicators.goal_attainment.value == pytest.approx(0.1)
    assert profile.self_efficacy.value > profile.self_efficacy.prior
    tomorrow = [
        item
        for item in profile.evidence.evidence_items
        if item.source_field.value == "tomorrow_outlook"
    ]
    assert tomorrow
    assert all(item.evidence_type is EvidenceType.SELF_EFFICACY for item in tomorrow)
    assert profile.fatigue.value > profile.fatigue.prior


def test_no_reflection_only_task_log():
    profile = run(
        [
            day(
                CURRENT,
                plans=[plan("t1", day=CURRENT)],
                executions=[execution("t1", day=CURRENT, completion=1.0, completed=True)],
                reflection=None,
            )
        ]
    )[0]
    assert profile.evidence.extraction_status == "no_reflection"
    assert profile.fatigue.value == pytest.approx(profile.fatigue.prior)
    assert profile.stress.value == pytest.approx(profile.stress.prior)
    assert profile.self_efficacy.value > profile.self_efficacy.prior
    assert profile.self_efficacy.evidence_availability.value == "task_log_only"
