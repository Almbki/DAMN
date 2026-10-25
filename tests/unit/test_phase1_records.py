"""Phase 1 record layer: schema registration, migration chain, repositories.

Incremental coverage for the data-and-records phase: new tables/columns, the
linear migration chain, and the new repositories writing/reading their rows.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, delete, event
from sqlalchemy.orm import Session

from app.domain.models import (
    DailyState,
    EvidenceItem,
    Feedback,
    PredictionOutcome,
    PredictionSnapshot,
    Task,
    TaskDependency,
    TaskEvent,
    TaskExecution,
)
from app.infrastructure.database import Base
from app.infrastructure.database import models as _models  # noqa: F401
from app.infrastructure.database import models as orm
from app.infrastructure.database.repositories import (
    DailyStateRepository,
    EvidenceItemRepository,
    FeedbackRepository,
    PredictionOutcomeRepository,
    PredictionSnapshotRepository,
    SyntheticDataRepository,
    TaskDependencyRepository,
    TaskEventRepository,
    TaskExecutionRepository,
    TaskRepository,
)

NEW_TABLES = {
    "task_dependencies",
    "task_events",
    "evidence_items",
    "daily_states",
    "prediction_snapshots",
    "prediction_outcomes",
}
#: Externally applied on the shared PostgreSQL database before Phase 1; the
#: revision file was reconstructed so the local chain can resolve the DB head.
EXTERNAL_REVISION = "persist_generation_jobs_20261025"
PHASE1_REVISIONS = [
    "b1f4a7c2d9e3",
    "c2a5b8d3e4f1",
    "d3b6c9e4f5a2",
    "e4c7d0f5a6b3",
    "f5d8e1a6b7c4",
    "a6e9f2b7c8d5",
    "b7f0a3c8d9e6",
    "c8a1b4d9e0f7",
]
NEW_HEAD = PHASE1_REVISIONS[-1]
OLD_HEAD = "adde00b2004f"


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


@pytest.fixture()
def fk_session():
    """SQLite session with foreign keys enforced (cascade/constraint tests)."""
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


def test_new_tables_registered() -> None:
    assert NEW_TABLES <= set(Base.metadata.tables)


def test_existing_tables_got_new_nullable_columns() -> None:
    tasks = Base.metadata.tables["tasks"]
    for name in (
        "deadline",
        "earliest_start_date",
        "difficulty",
        "task_type",
        "value_score",
        "completion_criterion",
    ):
        assert name in tasks.columns, name
        assert tasks.columns[name].nullable, name
    executions = Base.metadata.tables["task_executions"]
    for name in ("execution_status", "failure_category", "estimate_feedback"):
        assert name in executions.columns, name
        assert executions.columns[name].nullable, name
    feedbacks = Base.metadata.tables["feedbacks"]
    for name in (
        "day_review",
        "stuck_points",
        "state_review",
        "tomorrow_outlook",
        "day_closed_at",
    ):
        assert name in feedbacks.columns, name
        assert feedbacks.columns[name].nullable, name


def test_unique_constraints_and_cascades() -> None:
    daily = Base.metadata.tables["daily_states"]
    assert {c.name for c in daily.constraints} >= {"uq_daily_states_user_date"}
    outcomes = Base.metadata.tables["prediction_outcomes"]
    snapshot_fk = next(iter(outcomes.columns["snapshot_id"].foreign_keys))
    assert snapshot_fk.ondelete == "CASCADE"
    deps = Base.metadata.tables["task_dependencies"]
    assert {c.name for c in deps.constraints} >= {"uq_task_dependencies_pair"}


def test_migration_chain_contains_phase1_revisions() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(Config("alembic.ini"))
    # Walk the whole chain from the resolved head (robust to later phases).
    chain: list[str] = []
    revision = script.get_current_head()
    while revision is not None:
        chain.append(revision)
        revision = script.get_revision(revision).down_revision
    assert len(chain) == len(set(chain))
    assert set(PHASE1_REVISIONS) <= set(chain)
    # The eight Phase-1 revisions form one contiguous block directly on top of
    # the externally applied revision (which sits on the pre-Phase-1 head).
    assert chain.index(OLD_HEAD) - chain.index(NEW_HEAD) >= len(PHASE1_REVISIONS) + 1
    parents = {
        revision_id: script.get_revision(revision_id).down_revision
        for revision_id in PHASE1_REVISIONS
    }
    assert parents[PHASE1_REVISIONS[0]] == EXTERNAL_REVISION
    for revision_id in PHASE1_REVISIONS[1:]:
        assert parents[revision_id] in PHASE1_REVISIONS, revision_id
    for revision_id in PHASE1_REVISIONS:
        path = Path(script.get_revision(revision_id).path)
        text = path.read_text(encoding="utf-8")
        assert "def upgrade()" in text, revision_id
        assert "def downgrade()" in text, revision_id


def test_task_repository_persists_record_fields(session: Session) -> None:
    (task,) = TaskRepository(session).create_many(
        [
            Task(
                plan_id=1,
                title="read chapter 3",
                deadline=date(2030, 1, 2),
                earliest_start_date=date(2030, 1, 1),
                difficulty=4,
                task_type="reading",
                value_score=5,
                completion_criterion="finish chapter 3 and write 3 notes",
            )
        ]
    )
    assert task.deadline == date(2030, 1, 2)
    assert task.earliest_start_date == date(2030, 1, 1)
    assert task.difficulty == 4
    assert task.task_type == "reading"
    assert task.value_score == 5
    assert task.completion_criterion == "finish chapter 3 and write 3 notes"


def test_execution_repository_persists_outcome_fields(session: Session) -> None:
    execution = TaskExecutionRepository(session).create(
        TaskExecution(
            task_id=1,
            user_id=1,
            planned_duration=60,
            actual_duration=30,
            completion_rate=0.5,
            completed=False,
            execution_status="partial",
            failure_category="scheduling",
            estimate_feedback="over",
        )
    )
    assert execution.execution_status == "partial"
    assert execution.failure_category == "scheduling"
    assert execution.estimate_feedback == "over"


def test_feedback_repository_persists_four_section(session: Session) -> None:
    closed_at = datetime(2030, 1, 1, 22, 0, tzinfo=UTC)
    feedback = FeedbackRepository(session).create(
        Feedback(
            user_id=1,
            plan_id=1,
            date=date(2030, 1, 1),
            completion_rate=0.5,
            day_review="today was okay",
            stuck_points="math proofs",
            state_review="a bit tired",
            tomorrow_outlook="plan less",
            day_closed_at=closed_at,
        )
    )
    assert feedback.day_review == "today was okay"
    assert feedback.stuck_points == "math proofs"
    assert feedback.state_review == "a bit tired"
    assert feedback.tomorrow_outlook == "plan less"
    # SQLite stores DateTime(timezone=True) without the offset.
    assert feedback.day_closed_at is not None
    assert feedback.day_closed_at.replace(tzinfo=UTC) == closed_at


def test_dependency_and_event_repositories(session: Session) -> None:
    deps = TaskDependencyRepository(session)
    (dep,) = deps.create_many([TaskDependency(task_id=2, depends_on_task_id=1)])
    assert dep.dependency_type == "hard"
    assert [item.task_id for item in deps.list_by_task(1)] == [2]
    assert deps.list_by_plan(1) == []

    events = TaskEventRepository(session)
    events.create(
        TaskEvent(
            user_id=1,
            task_id=2,
            event_type="edited",
            before={"title": "a"},
            after={"title": "b"},
        )
    )
    (stored,) = events.list_by_task(2)
    assert stored.after == {"title": "b"}
    assert stored.before == {"title": "a"}


def test_evidence_item_repository(session: Session) -> None:
    items = EvidenceItemRepository(session)
    items.create_many(
        [
            EvidenceItem(
                user_id=1,
                feedback_id=1,
                reflection_field="state_review",
                evidence_type="fatigue",
                direction="increase",
                strength="moderate",
                period="evening",
                evidence_text="a bit tired",
                extractor="rule",
                extractor_version="1",
                status="accepted",
            )
        ]
    )
    (stored,) = items.list_by_feedback(1)
    assert stored.evidence_text == "a bit tired"
    assert stored.voluntary is None


def test_daily_state_upsert_and_prune(session: Session) -> None:
    repo = DailyStateRepository(session)
    day = date(2030, 1, 1)

    def state(fatigue: float) -> DailyState:
        return DailyState(
            user_id=1,
            date=day,
            fatigue=fatigue,
            stress=0.2,
            self_efficacy=0.6,
            fatigue_uncertainty=0.1,
            stress_uncertainty=0.1,
            self_efficacy_uncertainty=0.1,
            evidence_availability="partial",
            evidence_count=1,
            cold_start=False,
            gap_days=0,
        )

    repo.upsert(state(0.4))
    repo.upsert(state(0.8))
    rows = repo.list_by_user(1)
    assert len(rows) == 1
    assert rows[0].fatigue == 0.8

    old = state(0.3).model_copy(update={"date": date(2029, 1, 1)})
    repo.upsert(old)
    assert len(repo.list_by_user(1)) == 2
    assert repo.prune_before(1, day) == 1
    assert [row.date for row in repo.list_by_user(1)] == [day]


def test_prediction_snapshot_and_outcome_repositories(session: Session) -> None:
    snapshots = PredictionSnapshotRepository(session)
    snapshot = snapshots.create(
        PredictionSnapshot(
            user_id=1,
            task_id=7,
            plan_id=1,
            prediction_timestamp=datetime(2030, 1, 1, 8, 0, tzinfo=UTC),
            feature_snapshot={"estimated_duration_minutes": 60},
            input_hash="abc",
            model_version="level3_v1",
            mode="shadow",
        )
    )
    assert snapshots.get_latest_for_task(7).id == snapshot.id
    assert snapshots.list_by_task(7)[0].id == snapshot.id

    outcomes = PredictionOutcomeRepository(session)
    outcome = outcomes.create(
        PredictionOutcome(
            snapshot_id=snapshot.id,
            task_id=7,
            completed=True,
            completion_ratio=1.0,
            actual_duration_minutes=55.0,
            outcome_timestamp=datetime(2030, 1, 1, 9, 0, tzinfo=UTC),
        )
    )
    assert outcomes.get_by_snapshot(snapshot.id).id == outcome.id
    assert outcomes.list_by_task(7)[0].id == outcome.id


def test_domain_bounds_reject_invalid_values() -> None:
    with pytest.raises(ValueError):
        Task(plan_id=1, title="t", difficulty=6)
    with pytest.raises(ValueError):
        DailyState(
            user_id=1,
            date=date(2030, 1, 1),
            fatigue=1.5,
            stress=0.2,
            self_efficacy=0.5,
            fatigue_uncertainty=0.1,
            stress_uncertainty=0.1,
            self_efficacy_uncertainty=0.1,
        )
    with pytest.raises(ValueError):
        PredictionOutcome(snapshot_id=1, task_id=1, completion_ratio=1.5)

def _seed_chain(session: Session, *, data_origin: str = "real") -> tuple[int, int, int]:
    """Minimal user/plan/task rows so the new foreign keys can be exercised."""
    user = orm.User(email=f"{data_origin}@example.com", password_hash="x")
    session.add(user)
    session.flush()
    plan = orm.Plan(
        user_id=user.id,
        version=1,
        title="phase1",
        start_date=date(2030, 1, 1),
        end_date=date(2030, 1, 7),
        data_origin=data_origin,
    )
    session.add(plan)
    session.flush()
    task = orm.Task(plan_id=plan.id, title="seeded", data_origin=data_origin)
    session.add(task)
    session.flush()
    return user.id, plan.id, task.id


def _daily_state(user_id: int, day: date, *, data_origin: str = "real") -> DailyState:
    return DailyState(
        user_id=user_id,
        date=day,
        fatigue=0.2,
        stress=0.2,
        self_efficacy=0.6,
        fatigue_uncertainty=0.1,
        stress_uncertainty=0.1,
        self_efficacy_uncertainty=0.1,
        data_origin=data_origin,
    )


def test_foreign_key_cascade_removes_task_audit_rows(fk_session: Session) -> None:
    session = fk_session
    user_id, plan_id, task_id = _seed_chain(session)
    session.add(orm.TaskEvent(user_id=user_id, task_id=task_id, event_type="edited"))
    session.add(orm.TaskDependency(task_id=task_id, depends_on_task_id=task_id))
    snapshot = PredictionSnapshotRepository(session).create(
        PredictionSnapshot(
            user_id=user_id,
            task_id=task_id,
            prediction_timestamp=datetime(2030, 1, 1, 8, 0, tzinfo=UTC),
            input_hash="h",
        )
    )
    PredictionOutcomeRepository(session).create(
        PredictionOutcome(snapshot_id=snapshot.id, task_id=task_id, completed=True)
    )
    session.flush()

    session.execute(delete(orm.Task).where(orm.Task.id == task_id))
    session.flush()

    assert TaskEventRepository(session).list_by_task(task_id) == []
    assert TaskDependencyRepository(session).list_by_task(task_id) == []
    assert PredictionSnapshotRepository(session).list_by_task(task_id) == []
    assert PredictionOutcomeRepository(session).list_by_task(task_id) == []


def test_synthetic_reset_cleans_phase1_records(fk_session: Session) -> None:
    session = fk_session
    user_id, plan_id, task_id = _seed_chain(session, data_origin="synthetic")
    feedback = FeedbackRepository(session).create(
        Feedback(
            user_id=user_id,
            plan_id=plan_id,
            date=date(2030, 1, 1),
            completion_rate=0.0,
            data_origin="synthetic",
        )
    )
    session.add(orm.TaskEvent(user_id=user_id, task_id=task_id, event_type="edited"))
    session.add(orm.TaskDependency(task_id=task_id, depends_on_task_id=task_id))
    EvidenceItemRepository(session).create_many(
        [
            EvidenceItem(
                user_id=user_id,
                feedback_id=feedback.id,
                reflection_field="state_review",
                evidence_type="fatigue",
                direction="increase",
                strength="moderate",
                period="evening",
                evidence_text="tired",
                extractor="rule",
                extractor_version="1",
                status="accepted",
            )
        ]
    )
    DailyStateRepository(session).upsert(
        _daily_state(user_id, date(2030, 1, 1), data_origin="synthetic")
    )
    snapshot = PredictionSnapshotRepository(session).create(
        PredictionSnapshot(
            user_id=user_id,
            task_id=task_id,
            prediction_timestamp=datetime(2030, 1, 1, 8, 0, tzinfo=UTC),
            input_hash="h",
            data_origin="synthetic",
        )
    )
    PredictionOutcomeRepository(session).create(
        PredictionOutcome(snapshot_id=snapshot.id, task_id=task_id, completed=True)
    )
    session.flush()

    repo = SyntheticDataRepository(session)
    before = repo.counts(user_id)
    for key in (
        "task_events",
        "task_dependencies",
        "evidence_items",
        "daily_states",
        "prediction_snapshots",
        "prediction_outcomes",
    ):
        assert before.get(key, 0) >= 1, (key, before)

    repo.delete_for_user(user_id)
    session.flush()
    after = repo.counts(user_id)
    for key in NEW_TABLES:
        assert after.get(key, 0) == 0, (key, after)
