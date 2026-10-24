from __future__ import annotations

from datetime import date

import pytest
from ddsr.engine import DDSREngine
from ddsr.schemas import PassiveContext, ReflectionInput
from ddsr.state_model import predict_next
from ddsr.store import JsonHistoryStore
from helpers import day, execution, next_day, plan, trait_profile


def replay_days() -> list:
    base = date(2026, 10, 20)
    days = []
    for index in range(10):
        current = next_day(base, index)
        high_completion = index % 2 == 0
        reflection = (
            ReflectionInput(state_review="今天很累，压力很大。")
            if high_completion
            else ReflectionInput(state_review="今天精力充沛，心情放松。")
        )
        days.append(
            day(
                current,
                plans=[plan("t1", day=current)],
                executions=[
                    execution(
                        "t1",
                        day=current,
                        completion=0.3 if high_completion else 0.9,
                        completed=not high_completion,
                    )
                ],
                reflection=reflection,
            )
        )
    return days


def test_multi_day_replay_bounded_and_not_locked(config):
    profiles = DDSREngine(config).replay(replay_days(), trait_profile())
    assert len(profiles) == 10
    assert profiles[0].cold_start is True
    assert all(not profile.cold_start for profile in profiles[1:])
    for profile in profiles:
        for state in (profile.fatigue, profile.stress, profile.self_efficacy):
            assert 0.0 <= state.value <= 1.0
            assert config.uncertainty_floor <= state.uncertainty <= config.uncertainty_ceiling
            assert 0.0 <= state.prior <= 1.0
        for value in profile.next_day_prior.value.as_dict().values():
            assert 0.0 <= value <= 1.0
    fatigue_values = [profile.fatigue.value for profile in profiles]
    assert max(fatigue_values) - min(fatigue_values) > 1e-6
    assert len({round(value, 6) for value in fatigue_values}) > 1


def test_replay_is_deterministic(config):
    first = DDSREngine(config).replay(replay_days(), trait_profile())
    second = DDSREngine(config).replay(replay_days(), trait_profile())
    assert [p.model_dump(mode="json") for p in first] == [
        p.model_dump(mode="json") for p in second
    ]


def test_out_of_order_dates_are_rejected(config):
    engine = DDSREngine(config)
    later = day(next_day(date(2026, 10, 20), 2))
    earlier = day(date(2026, 10, 20))
    engine.process_day(later, trait_profile())
    with pytest.raises(ValueError, match="strictly increasing"):
        engine.process_day(earlier, trait_profile())


def test_gap_days_repeat_transition_and_record_gap(config):
    engine = DDSREngine(config)
    first_day = day(date(2026, 10, 20), reflection=ReflectionInput(state_review="今天很累。"))
    first = engine.process_day(first_day, trait_profile())
    fourth = engine.process_day(day(date(2026, 10, 23)), trait_profile())
    assert fourth.gap_days == 3
    expected = predict_next(
        first.current_posterior.as_dict(),
        {
            "fatigue": first.fatigue.uncertainty,
            "stress": first.stress.uncertainty,
            "self_efficacy": first.self_efficacy.uncertainty,
        },
        config,
        steps=3,
    )
    for state in ("fatigue", "stress", "self_efficacy"):
        assert fourth.prior.as_dict()[state] == pytest.approx(expected.value[state])
        assert fourth.next_day_prior.uncertainty.as_dict()[state] > 0


def test_next_day_prior_is_the_next_day_prior(config):
    engine = DDSREngine(config)
    first = engine.process_day(
        day(date(2026, 10, 20), reflection=ReflectionInput(state_review="今天很累。")),
        trait_profile(),
    )
    second = engine.process_day(day(date(2026, 10, 21)), trait_profile())
    assert second.prior.as_dict() == first.next_day_prior.value.as_dict()
    assert second.fatigue.prior == pytest.approx(first.next_day_prior.value.fatigue)
    assert second.fatigue.prior_uncertainty == pytest.approx(
        first.next_day_prior.uncertainty.fatigue
    )
    expected = predict_next(
        first.current_posterior.as_dict(),
        {
            "fatigue": first.fatigue.uncertainty,
            "stress": first.stress.uncertainty,
            "self_efficacy": first.self_efficacy.uncertainty,
        },
        config,
        steps=1,
    )
    assert first.next_day_prior.value.as_dict() == pytest.approx(expected.value)


def test_json_history_store_roundtrip(config, tmp_path):
    profiles = DDSREngine(config).replay(replay_days()[:3], trait_profile())
    store = JsonHistoryStore(tmp_path / "history.json")
    for profile in profiles:
        store.append(profile)
    loaded = store.load()
    assert [p.model_dump(mode="json") for p in loaded] == [
        p.model_dump(mode="json") for p in profiles
    ]
    assert store.latest().date == profiles[-1].date


def test_no_reflection_with_only_task_log_updates_self_efficacy_only(config):
    current = date(2026, 10, 20)
    profile = DDSREngine(config).process_day(
        day(
            current,
            plans=[plan("t1", day=current)],
            executions=[execution("t1", day=current, completion=1.0, completed=True)],
            reflection=None,
        ),
        trait_profile(),
    )
    assert profile.evidence.extraction_status == "no_reflection"
    assert profile.fatigue.evidence_availability.value == "none"
    assert profile.stress.evidence_availability.value == "none"
    assert profile.self_efficacy.evidence_availability.value == "task_log_only"
    assert profile.fatigue.value == pytest.approx(profile.fatigue.prior)
    assert profile.stress.value == pytest.approx(profile.stress.prior)
    assert profile.self_efficacy.value > profile.self_efficacy.prior


def test_passive_context_is_recorded_but_not_used(config):
    current = date(2026, 10, 20)
    passive = PassiveContext(
        screen_time_minutes=420,
        unlock_count=120,
        late_night_usage_minutes=60,
        app_switching_count=80,
        sleep_duration_minutes=300,
        sleep_quality=0.3,
    )
    plain = DDSREngine(config).process_day(day(current), trait_profile())
    with_context = DDSREngine(config).process_day(
        day(current, passive_context=passive), trait_profile()
    )
    assert with_context.passive_context_used is False
    assert with_context.passive_context is not None
    assert plain.passive_context is None
    assert plain.current_posterior.model_dump() == with_context.current_posterior.model_dump()
    assert any("not used" in note for note in with_context.limitations)
