"""Phase 2: reflection-evidence extraction wiring.

Coverage:
* LLM extraction through DDSREngine/Level2Runtime with a StaticLLMClient;
* malformed LLM output falls back to the deterministic rules;
* the application factory picks rules for mock/unconfigured providers;
* refresh_dynamic_state writes evidence_items and is idempotent;
* a failed extraction degrades instead of raising/destroying evidence;
* build_history keeps state failures out of the duration-ratio estimate.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application.services.model_runtime import (
    FallbackEvidenceExtractor,
    build_evidence_extractor,
)
from app.application.services.user_model_service import UserModelService
from app.core.config import Settings
from app.domain.models import EvidenceItem, TaskExecution
from app.infrastructure.database import Base
from app.infrastructure.database import models as orm
from app.infrastructure.database.repositories import (
    EvidenceItemRepository,
    TaskExecutionRepository,
)
from app.user_models.level2.ddsr.evidence import (
    LLMEvidenceExtractor,
    RuleBasedEvidenceExtractor,
    StaticLLMClient,
)
from app.user_models.level2.ddsr.schemas import DayInput, ReflectionInput
from app.user_models.level2.ddsr.schemas import TaskExecution as Level2TaskExecution
from app.user_models.level2.ddsr.schemas import TaskPlan as Level2TaskPlan
from app.user_models.level2.runtime import Level2Runtime
from app.user_models.runtime import UserModelRuntime

LLM_FATIGUE_PAYLOAD = {
    "evidence": [
        {
            "evidence_type": "fatigue",
            "direction": "increase",
            "evidence_text": "今天很累",
            "source_field": "day_review",
        }
    ]
}


def _trait_profile() -> dict:
    return {
        "schema_version": "1.0",
        "model": "trait_v1",
        "instrument": "IPIP-NEO-120",
        "method": "bayesian_cat",
        "calibration": {"model": "samejima_grm", "version": "grm_v1"},
        "domains": {
            domain: {"theta": 0.2, "se": 0.3}
            for domain in ("N", "E", "O", "A", "C")
        },
    }


def _day(day: date, reflection: str | None) -> DayInput:
    return DayInput(
        date=day,
        task_plans=[
            Level2TaskPlan(
                task_id="1",
                title="task",
                planned_start=datetime.combine(day, time(8, 0)),
                estimated_duration_minutes=60,
            )
        ],
        task_executions=[
            Level2TaskExecution(
                task_id="1",
                completed=True,
                actual_duration_minutes=60,
                completion_ratio=1.0,
            )
        ],
        reflection=ReflectionInput(day_review=reflection) if reflection else None,
    )


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


def _seed_feedback_day(
    session: Session,
    *,
    suffix: str = "main",
    day_review: str = "今天很累，压力很大",
    state_review: str | None = None,
) -> tuple[int, int]:
    today = date.today()
    user = orm.User(
        email=f"phase2-{suffix}@example.com",
        password_hash="x",
        trait_profile=_trait_profile(),
    )
    session.add(user)
    session.flush()
    plan = orm.Plan(
        user_id=user.id,
        version=1,
        title="phase2",
        start_date=today,
        end_date=today,
    )
    session.add(plan)
    session.flush()
    task = orm.Task(
        plan_id=plan.id,
        title="task",
        scheduled_date=today,
        estimated_duration=60,
    )
    session.add(task)
    session.flush()
    session.add(
        orm.TaskExecution(
            task_id=task.id,
            user_id=user.id,
            planned_duration=60,
            actual_duration=30,
            completion_rate=0.5,
            completed=False,
        )
    )
    feedback = orm.Feedback(
        user_id=user.id,
        plan_id=plan.id,
        date=today,
        completion_rate=0.5,
        day_review=day_review,
        state_review=state_review,
    )
    session.add(feedback)
    session.flush()
    session.commit()
    return user.id, feedback.id


class _FailingExtractor:
    name = "failing_evidence"
    version = "9.9"

    def extract(self, reflection, context):
        raise RuntimeError("boom")


# ---------------------------------------------------------------------------
# Engine / runtime extraction
# ---------------------------------------------------------------------------


def test_llm_extractor_returns_per_day_auditable_evidence() -> None:
    client = StaticLLMClient(json.dumps(LLM_FATIGUE_PAYLOAD, ensure_ascii=False))
    runtime = Level2Runtime(extractor=LLMEvidenceExtractor(client))
    profiles, extractions = runtime.replay_with_evidence(
        [
            _day(date(2030, 1, 1), "今天很累"),
            _day(date(2030, 1, 2), None),
        ],
        _trait_profile(),
    )

    assert [profile.date for profile in profiles] == [
        date(2030, 1, 1),
        date(2030, 1, 2),
    ]
    assert len(extractions) == 2
    first, second = extractions
    assert first.ok is True
    assert first.extractor == "llm_evidence_extractor"
    assert first.extractor_version == "1.0"
    assert len(first.items) == 1
    assert first.items[0].evidence_type.value == "fatigue"
    assert first.items[0].evidence_text == "今天很累"
    assert profiles[0].evidence.extraction_status == "ok"
    assert profiles[0].evidence.extractor == "llm_evidence_extractor"
    # No reflection -> no LLM call and no evidence, not a failure.
    assert second.ok is False
    assert second.status == "no_reflection"
    assert second.items == []
    assert len(client.prompts) == 1


def test_malformed_llm_output_falls_back_to_rules() -> None:
    primary = LLMEvidenceExtractor(StaticLLMClient("not JSON"))
    extractor = FallbackEvidenceExtractor(primary, RuleBasedEvidenceExtractor())
    runtime = Level2Runtime(extractor=extractor)
    profiles, extractions = runtime.replay_with_evidence(
        [_day(date(2030, 1, 1), "今天很累")], _trait_profile()
    )

    (extraction,) = extractions
    assert extraction.ok is True
    assert extraction.extractor == "rule_based_evidence"
    assert extraction.extractor_version == "1.0"
    assert extraction.items
    # The profile reports the extractor that actually produced the evidence.
    assert profiles[0].evidence.extractor == "rule_based_evidence"


def test_build_evidence_extractor_uses_rules_when_unconfigured() -> None:
    mock = Settings(evidence_extractor="auto", llm_provider="mock")
    assert isinstance(build_evidence_extractor(mock), RuleBasedEvidenceExtractor)

    unconfigured = Settings(
        evidence_extractor="llm",
        llm_provider="deepseek",
        llm_api_key="",
        llm_api_base="",
    )
    assert isinstance(build_evidence_extractor(unconfigured), RuleBasedEvidenceExtractor)

    explicit_rule = Settings(
        evidence_extractor="rule",
        llm_provider="deepseek",
        llm_api_key="test-key",
    )
    assert isinstance(build_evidence_extractor(explicit_rule), RuleBasedEvidenceExtractor)


def test_build_evidence_extractor_wraps_configured_llm() -> None:
    settings = Settings(
        evidence_extractor="auto",
        llm_provider="deepseek",
        llm_api_key="test-key",
        llm_api_base="",
    )
    extractor = build_evidence_extractor(settings)

    assert isinstance(extractor, FallbackEvidenceExtractor)
    # Before any extraction the wrapper reports its primary (LLM) identity.
    assert extractor.name == "llm_evidence_extractor"


# ---------------------------------------------------------------------------
# Persistence via UserModelService.refresh_dynamic_state
# ---------------------------------------------------------------------------


def test_refresh_persists_rule_evidence_and_is_idempotent(session: Session) -> None:
    user_id, feedback_id = _seed_feedback_day(session)
    service = UserModelService(
        session, runtime=UserModelRuntime(level2=Level2Runtime())
    )

    snapshot = service.refresh_dynamic_state(user_id)
    assert snapshot is not None

    repo = EvidenceItemRepository(session)
    rows = repo.list_by_feedback(feedback_id)
    assert rows
    assert {row.evidence_type for row in rows} >= {"fatigue", "stress"}
    assert all(row.reflection_field == "day_review" for row in rows)
    assert all(row.extractor == "rule_based_evidence" for row in rows)
    assert all(row.extractor_version == "1.0" for row in rows)
    assert all(row.status == "accepted" for row in rows)

    # Replaying the same history replaces, never duplicates, the rows.
    service.refresh_dynamic_state(user_id)
    again = repo.list_by_feedback(feedback_id)
    assert len(again) == len(rows)
    assert {(row.evidence_type, row.evidence_text) for row in again} == {
        (row.evidence_type, row.evidence_text) for row in rows
    }


def test_failed_extraction_degrades_without_writing(session: Session) -> None:
    user_id, feedback_id = _seed_feedback_day(session, suffix="failure")
    repo = EvidenceItemRepository(session)
    repo.create_many(
        [
            EvidenceItem(
                user_id=user_id,
                feedback_id=feedback_id,
                reflection_field="day_review",
                evidence_type="fatigue",
                direction="increase",
                strength="moderate",
                period="unspecified",
                evidence_text="今天很累",
                extractor="rule_based_evidence",
                extractor_version="1.0",
                status="accepted",
            )
        ]
    )
    session.commit()

    runtime = UserModelRuntime(
        level2=Level2Runtime(extractor=_FailingExtractor())
    )
    service = UserModelService(session, runtime=runtime)
    snapshot = service.refresh_dynamic_state(user_id)

    assert snapshot is not None
    rows = repo.list_by_feedback(feedback_id)
    assert len(rows) == 1
    assert rows[0].extractor == "rule_based_evidence"


# ---------------------------------------------------------------------------
# Duration history (phase 5 hook that lives in this service)
# ---------------------------------------------------------------------------


def _seed_execution_history(session: Session) -> int:
    user = orm.User(
        email="phase2-history@example.com",
        password_hash="x",
        trait_profile=_trait_profile(),
    )
    session.add(user)
    session.flush()
    plan = orm.Plan(
        user_id=user.id,
        version=1,
        title="history",
        start_date=date(2030, 1, 1),
        end_date=date(2030, 1, 2),
    )
    session.add(plan)
    session.flush()
    task = orm.Task(plan_id=plan.id, title="task")
    session.add(task)
    session.flush()

    repo = TaskExecutionRepository(session)
    repo.create(
        TaskExecution(
            user_id=user.id,
            task_id=task.id,
            planned_duration=60,
            actual_duration=90,
            completion_rate=1.0,
            completed=True,
            created_at=datetime(2030, 1, 1, 9, tzinfo=UTC),
        )
    )
    repo.create(
        TaskExecution(
            user_id=user.id,
            task_id=task.id,
            planned_duration=60,
            actual_duration=30,
            completion_rate=0.0,
            completed=False,
            failure_category="state",
            created_at=datetime(2030, 1, 1, 10, tzinfo=UTC),
        )
    )
    repo.create(
        TaskExecution(
            user_id=user.id,
            task_id=task.id,
            planned_duration=60,
            actual_duration=30,
            completion_rate=1.0,
            completed=True,
            failure_category="scheduling",
            created_at=datetime(2030, 1, 1, 11, tzinfo=UTC),
        )
    )
    session.commit()
    return user.id


def test_build_history_excludes_state_failures_from_duration_ratio(
    session: Session,
) -> None:
    user_id = _seed_execution_history(session)
    service = UserModelService(
        session, runtime=UserModelRuntime(level2=Level2Runtime())
    )
    history = service.build_history(user_id)

    assert history.completion_history == [True, False, True]
    assert history.duration_ratio_history == [1.5, 0.5]
    assert history.usable_duration_samples == 2
    assert history.total_historical_tasks == 3
