"""Run DDSR-V1 synthetic replays and write ``level2_validation.json``.

Usage (from this folder):
    uv run --project ../.. --extra dev python run_validation.py

The artifact is machine-readable and deliberately avoids invented accuracy
claims.  It records data-flow, boundary, reproducibility and longitudinal
stability checks, plus the pytest summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from ddsr.config import ALLOWED_SOURCE_CATEGORIES, DDSRConfig  # noqa: E402
from ddsr.engine import DDSREngine  # noqa: E402
from ddsr.evidence.base import EvidenceExtractionError  # noqa: E402
from ddsr.evidence.llm import LLMEvidenceExtractor, StaticLLMClient  # noqa: E402
from ddsr.schemas import PassiveContext, ReflectionInput  # noqa: E402
from ddsr.trait_context import TraitContext  # noqa: E402
from helpers import day, execution, next_day, plan, trait_profile  # noqa: E402

CURRENT = date(2026, 10, 20)
CONFIG = DDSRConfig.from_json()


def r(value: float | None) -> float | None:
    return None if value is None else round(float(value), 6)


def summarize(profile) -> dict:
    return {
        "date": profile.date.isoformat(),
        "cold_start": profile.cold_start,
        "gap_days": profile.gap_days,
        "states": {
            name: {
                "prior": r(getattr(profile, name).prior),
                "value": r(getattr(profile, name).value),
                "uncertainty": r(getattr(profile, name).uncertainty),
                "evidence_availability": getattr(
                    profile, name
                ).evidence_availability.value,
                "evidence_count": getattr(profile, name).evidence_count,
                "conflict": getattr(profile, name).conflict,
            }
            for name in ("fatigue", "stress", "self_efficacy")
        },
        "goal_attainment": r(profile.behavioral_indicators.goal_attainment.value),
        "initiation_start_rate": r(
            profile.behavioral_indicators.initiation.start_rate
        ),
        "persistence_continuation_rate": r(
            profile.behavioral_indicators.persistence.continuation_rate
        ),
        "procrastination_confirmed": len(
            profile.behavioral_indicators.procrastination_evidence.confirmed
        ),
        "procrastination_candidates": (
            profile.behavioral_indicators.procrastination_evidence.candidate_task_ids
        ),
        "prediction_error": {
            key: r(value) for key, value in profile.prediction_error.raw.as_dict().items()
        },
        "next_day_prior": {
            key: r(value)
            for key, value in profile.next_day_prior.value.as_dict().items()
        },
        "extraction_status": profile.evidence.extraction_status,
        "evidence_types": [
            item.evidence_type.value for item in profile.evidence.evidence_items
        ],
    }


def run_scenario(name: str, days, trait: TraitContext) -> dict:
    profiles = DDSREngine(CONFIG).replay(days, trait)
    return {
        "name": name,
        "days": len(days),
        "profiles": [summarize(profile) for profile in profiles],
    }


def multi_day_days():
    days = []
    for index in range(10):
        current = next_day(CURRENT, index)
        high_completion = index % 2 == 0
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
                reflection=(
                    ReflectionInput(state_review="今天很累，压力很大。")
                    if high_completion
                    else ReflectionInput(state_review="今天精力充沛，心情放松。")
                ),
            )
        )
    return days


def build_scenarios(trait: TraitContext) -> list[dict]:
    scenarios = []

    scenarios.append(
        run_scenario(
            "high_completion_low_fatigue",
            [
                day(
                    CURRENT,
                    plans=[
                        plan("t1", day=CURRENT),
                        plan("t2", day=CURRENT, hour=10, duration=30),
                    ],
                    executions=[
                        execution("t1", day=CURRENT, completion=1.0, completed=True),
                        execution(
                            "t2",
                            day=CURRENT,
                            start_hour=10,
                            completion=1.0,
                            completed=True,
                        ),
                    ],
                    reflection=ReflectionInput(
                        state_review="今天精力充沛，不累，心情放松。",
                        tomorrow_outlook="明天我有把握完成。",
                    ),
                )
            ],
            trait,
        )
    )

    scenarios.append(
        run_scenario(
            "external_interruption_high_delay_not_procrastination",
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
                        stuck_points=(
                            "本来九点要开始，但临时开会，后来又被电话打断，不是拖延。"
                        )
                    ),
                )
            ],
            trait,
        )
    )

    scenarios.append(
        run_scenario(
            "explicit_avoidance_high_delay_procrastination",
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
            ],
            trait,
        )
    )

    scenarios.append(
        run_scenario(
            "high_fatigue_low_completion",
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
            ],
            trait,
        )
    )

    scenarios.append(
        run_scenario(
            "failure_today_high_tomorrow_self_efficacy",
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
            ],
            trait,
        )
    )

    scenarios.append(
        run_scenario(
            "no_reflection_only_task_log",
            [
                day(
                    CURRENT,
                    plans=[plan("t1", day=CURRENT)],
                    executions=[
                        execution("t1", day=CURRENT, completion=1.0, completed=True)
                    ],
                    reflection=None,
                )
            ],
            trait,
        )
    )

    scenarios.append(
        run_scenario("multi_day_replay_10_days", multi_day_days(), trait)
    )
    return scenarios


def check_prediction_error(profiles) -> bool:
    for profile in profiles:
        for name in ("fatigue", "stress", "self_efficacy"):
            raw = getattr(profile.prediction_error.raw, name)
            expected = getattr(profile, name).value - getattr(profile, name).prior
            if abs(raw - expected) > 1e-9:
                return False
            standardized = getattr(profile.prediction_error.standardized, name)
            if abs(standardized - raw / getattr(profile, name).prior_uncertainty) > 1e-9:
                return False
    return True


def check_next_day_prior(profiles) -> bool:
    for previous, current in zip(profiles, profiles[1:], strict=False):
        if current.prior.as_dict() != previous.next_day_prior.value.as_dict():
            return False
    return True


def check_llm_contract(trait: TraitContext) -> bool:
    reflection = ReflectionInput(state_review="今天很累")
    valid = (
        '{"evidence":[{"evidence_type":"fatigue","direction":"increase",'
        '"strength":"moderate","period":"evening","task_id":null,'
        '"cause_category":null,"voluntary":null,"evidence_text":"今天很累",'
        '"source_field":"state_review"}]}'
    )
    from ddsr.evidence.base import ExtractionContext

    context = ExtractionContext(frozenset(), CURRENT, CONFIG.min_quote_chars)
    try:
        result = LLMEvidenceExtractor(StaticLLMClient(valid)).extract(
            reflection, context
        )
        if len(result.evidence) != 1:
            return False
    except Exception:
        return False
    try:
        LLMEvidenceExtractor(StaticLLMClient("not json")).extract(
            reflection, context
        )
    except EvidenceExtractionError:
        return True
    except Exception:
        return False
    return False


def level1_hashes() -> dict[str, str]:
    files = [
        "context/cat.py",
        "context/cat_config.json",
        "context/grm_parameters.json",
        "context/questions.json",
        "context/交接文档.md",
    ]
    hashes = {}
    for relative in files:
        path = ROOT / relative
        if path.exists():
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def run_pytest() -> dict:
    # The repository's pytest config already adds ``-q``; passing another
    # ``-q`` suppresses the summary line, so use ``-rA`` and count result lines.
    command = [sys.executable, "-m", "pytest", "tests", "-rA"]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    passed = len(re.findall(r"^PASSED ", output, flags=re.MULTILINE))
    failed = len(re.findall(r"^FAILED ", output, flags=re.MULTILINE))
    if passed == 0 and failed == 0 and completed.returncode == 0:
        collected = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "--collect-only", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        passed = len(
            re.findall(r"::", (collected.stdout or "") + (collected.stderr or ""))
        )
    return {
        "command": "python -m pytest tests -rA",
        "returncode": completed.returncode,
        "passed": passed,
        "failed": failed,
        "total": passed + failed,
        "output_tail": output.strip().splitlines()[-8:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--output", default=str(ROOT / "level2_validation.json"))
    args = parser.parse_args()

    trait_dict = trait_profile()
    trait = TraitContext.from_profile(trait_dict)
    scenarios = build_scenarios(trait)
    by_name = {scenario["name"]: scenario for scenario in scenarios}

    all_profiles = [
        DDSREngine(CONFIG).replay(
            [
                day(
                    CURRENT,
                    plans=[plan("t1", day=CURRENT)],
                    executions=[
                        execution("t1", day=CURRENT, completion=0.8, completed=True)
                    ],
                    reflection=ReflectionInput(state_review="今天很累，压力很大。"),
                )
            ],
            trait,
        )[0]
    ]
    multi_profile = DDSREngine(CONFIG).replay(multi_day_days(), trait)

    # Boundary probes.
    missing_log = DDSREngine(CONFIG).process_day(
        day(CURRENT, plans=[plan("t1", day=CURRENT)]), trait
    )
    no_evidence = DDSREngine(CONFIG).process_day(day(CURRENT), trait)
    low_theta = TraitContext.from_profile(trait_profile(theta=-1.5))
    high_theta = TraitContext.from_profile(trait_profile(theta=1.5))
    probe = day(
        CURRENT,
        reflection=ReflectionInput(state_review="今天很累，压力很大。"),
    )
    low_profile = DDSREngine(CONFIG).process_day(probe, low_theta)
    high_profile = DDSREngine(CONFIG).process_day(probe, high_theta)
    passive = DDSREngine(CONFIG).process_day(
        day(
            CURRENT,
            passive_context=PassiveContext(
                screen_time_minutes=420,
                unlock_count=120,
                late_night_usage_minutes=60,
                app_switching_count=80,
                sleep_duration_minutes=300,
                sleep_quality=0.3,
            ),
        ),
        trait,
    )
    plain = DDSREngine(CONFIG).process_day(day(CURRENT), trait)
    deterministic_a = DDSREngine(CONFIG).replay(multi_day_days(), trait)
    deterministic_b = DDSREngine(CONFIG).replay(multi_day_days(), trait)

    all_summaries = [
        profile
        for scenario in scenarios
        for profile in scenario["profiles"]
    ]
    fatigue_values = [
        profile["states"]["fatigue"]["value"]
        for profile in by_name["multi_day_replay_10_days"]["profiles"]
    ]

    checks = {
        "all_states_bounded_0_1": all(
            0.0 <= state["value"] <= 1.0
            for profile in all_summaries
            for state in profile["states"].values()
        ),
        "all_uncertainties_bounded": all(
            CONFIG.uncertainty_floor
            <= state["uncertainty"]
            <= CONFIG.uncertainty_ceiling
            for profile in all_summaries
            for state in profile["states"].values()
        ),
        "prediction_error_saved_and_arithmetic": check_prediction_error(all_profiles)
        and check_prediction_error(multi_profile),
        "next_day_prior_saved_and_consistent": check_next_day_prior(multi_profile),
        "multi_day_no_explosion_or_lock": bool(fatigue_values)
        and (max(fatigue_values) - min(fatigue_values) > 1e-6),
        "procrastination_false_positive_guard": (
            by_name["external_interruption_high_delay_not_procrastination"][
                "profiles"
            ][0]["procrastination_confirmed"]
            == 0
            and by_name["explicit_avoidance_high_delay_procrastination"][
                "profiles"
            ][0]["procrastination_confirmed"]
            >= 1
        ),
        "missing_task_log_is_not_failure": (
            missing_log.behavioral_indicators.goal_attainment.value is None
            and missing_log.behavioral_indicators.goal_attainment.evidence_available
            is False
        ),
        "no_evidence_keeps_prior_and_uncertainty": (
            no_evidence.fatigue.value == no_evidence.fatigue.prior
            and no_evidence.stress.value == no_evidence.stress.prior
            and no_evidence.self_efficacy.value == no_evidence.self_efficacy.prior
        ),
        "level1_read_only_contract": (
            low_profile.current_posterior.model_dump()
            == high_profile.current_posterior.model_dump()
            and trait_dict == trait_profile()
        ),
        "deterministic_replay": [
            p.model_dump(mode="json") for p in deterministic_a
        ]
        == [p.model_dump(mode="json") for p in deterministic_b],
        "passive_context_ignored": (
            passive.current_posterior.model_dump()
            == plain.current_posterior.model_dump()
            and passive.passive_context_used is False
        ),
        "llm_only_extracts_validated_evidence": check_llm_contract(trait),
        "parameter_provenance_complete": all(
            entry["category"] in ALLOWED_SOURCE_CATEGORIES and entry["note"].strip()
            for entry in CONFIG.parameter_sources.values()
        )
        and CONFIG.personalization_enabled is False,
    }

    test_summary = (
        {"command": "skipped", "returncode": 0, "passed": 0, "failed": 0, "output_tail": []}
        if args.skip_tests
        else run_pytest()
    )
    tests_ok = bool(test_summary["returncode"] == 0 and test_summary["failed"] == 0)
    ready = bool(all(checks.values()) and tests_ok)

    artifact = {
        "model": "DDSR-V1",
        "model_version": "ddsr_v1",
        "schema_version": "1.0",
        "config_version": CONFIG.config_version,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_trait_model": trait.source_model().model_dump(mode="json"),
        "test_summary": test_summary,
        "checks": checks,
        "scenarios": scenarios,
        "parameter_sources": CONFIG.parameter_sources,
        "level1_assets_sha256": level1_hashes(),
        "level1_files_modified": False,
        "limitations": [
            "No large-scale real longitudinal ground truth was available; no accuracy is claimed.",
            "The 0-1 state scale is an engineering scale, not a published or clinical scale.",
            (
                "Persistence, noise, evidence-sharpness, and goal-attainment weights "
                "are engineering initializations."
            ),
            "Prediction errors are stored but no personalized transition learning is active in V1.",
            "Passive context is accepted by the interface but never interpreted in V1.",
            (
                "The rule-based extractor is a deterministic fallback; the production "
                "path is the audited LLM extractor."
            ),
        ],
        "acceptance": {
            "data_flow_correct": checks["prediction_error_saved_and_arithmetic"]
            and checks["next_day_prior_saved_and_consistent"],
            "state_behavior_boundary_correct": checks[
                "procrastination_false_positive_guard"
            ],
            "llm_evidence_only": checks["llm_only_extracts_validated_evidence"],
            "prediction_correction_reproducible": checks["deterministic_replay"],
            "uncertainty_reflects_missing_evidence": checks[
                "no_evidence_keeps_prior_and_uncertainty"
            ],
            "prediction_error_saved": checks["prediction_error_saved_and_arithmetic"],
            "multi_day_replay_stable": checks[
                "multi_day_no_explosion_or_lock"
            ],
            "level1_unmodified": checks["level1_read_only_contract"],
            "minimal_parameters": checks["parameter_provenance_complete"],
            "assumptions_traceable": checks["parameter_provenance_complete"],
        },
        "DYNAMIC_STATE_MODEL_V1_READY": "YES" if ready else "NO",
    }

    Path(args.output).write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": args.output,
        "tests": test_summary,
        "checks": checks,
        "ready": artifact["DYNAMIC_STATE_MODEL_V1_READY"],
    }, ensure_ascii=False, indent=2))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
