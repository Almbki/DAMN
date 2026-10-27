"""Guarded synthetic scenario import/reset.

The service imports *observations* only. Level 2 and Level 3 are then computed by
the real runtime; no fatigue/stress/completion values can be injected.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.application.dto.synthetic import (
    ScenarioDay,
    ScenarioTask,
    SyntheticImportSummary,
    SyntheticResetSummary,
    SyntheticScenario,
    SyntheticScenarioInfo,
    SyntheticStatus,
)
from app.application.exceptions import ConflictError, DomainValidationError, NotFoundError
from app.application.services.model_runtime import get_user_model_runtime
from app.application.services.user_model_service import UserModelService
from app.core.config import get_settings
from app.domain.models import Feedback, Plan, Task, TaskExecution, TraitAssessment
from app.domain.models.enums import CognitiveLoad, PlanStatus, Priority, TaskKind, TaskStatus
from app.infrastructure.database.repositories import (
    FeedbackRepository,
    PlanRepository,
    SyntheticDataRepository,
    TaskExecutionRepository,
    TaskRepository,
    TraitAssessmentRepository,
    UserRepository,
    UserStateRepository,
)
from app.user_models.runtime import UserModelRuntime

logger = logging.getLogger(__name__)

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "scenarios"
SYNTHETIC = "synthetic"


class SyntheticScenarioService:
    def __init__(
        self, session: Session, *, runtime: UserModelRuntime | None = None
    ) -> None:
        self._session = session
        self._runtime = runtime or get_user_model_runtime()
        self._users = UserRepository(session)
        self._plans = PlanRepository(session)
        self._tasks = TaskRepository(session)
        self._executions = TaskExecutionRepository(session)
        self._feedback = FeedbackRepository(session)
        self._assessments = TraitAssessmentRepository(session)
        self._states = UserStateRepository(session)
        self._synthetic = SyntheticDataRepository(session)
        self._user_models = UserModelService(session, runtime=self._runtime)

    @property
    def enabled(self) -> bool:
        return get_settings().enable_synthetic_import

    def require_enabled(self) -> None:
        if not self.enabled:
            raise NotFoundError("synthetic import is disabled")

    def _reject_showcase(self, user_id: int) -> None:
        """Protect the curated showcase account from synthetic reset/import.

        The showcase dataset is deliberately marked synthetic, so the normal
        developer reset would delete its plans, tasks, feedback and Level 2
        state. Rebuild it only through ``scripts/seed_showcase_account.py``.
        """
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("user not found")
        if (user.profile or {}).get("showcase_seed"):
            raise ConflictError(
                "showcase demo account data is protected; "
                "rebuild it with scripts/seed_showcase_account.py"
            )

    def list_scenarios(self) -> list[SyntheticScenarioInfo]:
        self.require_enabled()
        result: list[SyntheticScenarioInfo] = []
        for path in sorted(FIXTURE_DIR.glob("*.json")):
            try:
                scenario = SyntheticScenario.model_validate(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            except Exception as exc:  # noqa: BLE001 - skip a broken fixture
                logger.warning("invalid synthetic fixture %s: %s", path, exc)
                continue
            result.append(
                SyntheticScenarioInfo(
                    name=scenario.name,
                    description=scenario.description,
                    scenario_version=scenario.scenario_version,
                    days=len(scenario.days),
                    tasks=sum(len(day.tasks) for day in scenario.days),
                )
            )
        return result

    def status(self, user_id: int) -> SyntheticStatus:
        self.require_enabled()
        counts = self._synthetic.counts(user_id)
        return SyntheticStatus(
            enabled=True,
            synthetic_present=sum(counts.values()) > 0,
            counts={key: value for key, value in counts.items() if value},
        )

    def import_scenario(
        self,
        user_id: int,
        *,
        scenario_name: str | None = None,
        scenario: SyntheticScenario | None = None,
    ) -> SyntheticImportSummary:
        self.require_enabled()
        self._reject_showcase(user_id)
        resolved = self._resolve_scenario(scenario_name, scenario)
        days = sorted(resolved.days, key=lambda day: day.date)
        if not days:
            raise DomainValidationError("scenario must contain at least one day")

        shadow_before = self._synthetic.count_shadow(user_id, data_origin=SYNTHETIC)
        warnings: list[str] = []

        try:
            self._apply_level1(user_id, resolved)
            existing_trait = self._user_models.get_trait_profile(user_id)
            if existing_trait is None:
                raise DomainValidationError(
                    "scenario needs level1 data or an existing validated trait profile"
                )

            plan = self._plans.create(
                Plan(
                    user_id=user_id,
                    version=self._plans.next_version(user_id),
                    status=PlanStatus.ACTIVE,
                    title=f"Synthetic: {resolved.name}"[:255],
                    start_date=days[0].date,
                    end_date=days[-1].date,
                    confidence=0.5,
                    data_origin=SYNTHETIC,
                )
            )
            tasks_and_specs: list[tuple[Task, ScenarioDay, ScenarioTask, datetime]] = []
            order_index = 0
            for day in days:
                for spec in day.tasks:
                    planned_start = spec.planned_start or datetime.combine(
                        day.date, time(9, 0)
                    )
                    planned_end = planned_start + timedelta(
                        minutes=spec.estimated_duration_minutes
                    )
                    task = Task(
                        plan_id=plan.id or 0,
                        title=spec.title,
                        estimated_duration=spec.estimated_duration_minutes,
                        predicted_duration=spec.estimated_duration_minutes,
                        cognitive_load=CognitiveLoad.MEDIUM,
                        priority=Priority.MEDIUM,
                        scheduled_date=day.date,
                        start_time=planned_start.time(),
                        end_time=planned_end.time(),
                        status=(
                            TaskStatus.COMPLETED
                            if spec.completed
                            else TaskStatus.SCHEDULED
                        ),
                        completion_probability=None,
                        prediction_source="synthetic:scenario",
                        prediction_mode="synthetic",
                        data_origin=SYNTHETIC,
                        task_kind=TaskKind.ONE_OFF,
                        order_index=order_index,
                    )
                    tasks_and_specs.append((task, day, spec, planned_start))
                    order_index += 1

            created_tasks = self._tasks.create_many([item[0] for item in tasks_and_specs])
            executions = 0
            for created, (_task, _day, spec, planned_start) in zip(
                created_tasks, tasks_and_specs, strict=True
            ):
                completion_rate = spec.completion_rate
                if completion_rate is None:
                    completion_rate = 1.0 if spec.completed else 0.0
                actual_start = spec.actual_start or planned_start
                finished_at = None
                if spec.actual_duration_minutes is not None:
                    finished_at = actual_start + timedelta(
                        minutes=spec.actual_duration_minutes
                    )
                elif spec.completed:
                    finished_at = actual_start + timedelta(
                        minutes=spec.estimated_duration_minutes
                    )
                self._executions.create(
                    TaskExecution(
                        task_id=created.id or 0,
                        user_id=user_id,
                        planned_duration=spec.estimated_duration_minutes,
                        actual_duration=spec.actual_duration_minutes,
                        completion_rate=completion_rate,
                        started_at=actual_start,
                        finished_at=finished_at,
                        difficulty_feedback=spec.difficulty,
                        interruption_count=spec.interruption_count,
                        completed=spec.completed,
                        data_origin=SYNTHETIC,
                    )
                )
                executions += 1

            feedback_count = 0
            for day in days:
                if day.feedback is None:
                    continue
                self._feedback.create(
                    Feedback(
                        user_id=user_id,
                        plan_id=plan.id or 0,
                        date=day.date,
                        completion_rate=day.feedback.completion_rate,
                        stress_level=day.feedback.stress_level,
                        energy_level=day.feedback.energy_level,
                        free_text=day.feedback.free_text,
                        sleep_hours=day.feedback.sleep_hours,
                        task_reasons=[],
                        data_origin=SYNTHETIC,
                    )
                )
                feedback_count += 1

            self._session.flush()
            self._user_models.refresh_dynamic_state(user_id, commit=False)
            context = self._user_models.context(user_id)
            written = self._user_models.run_shadow_for_plan(
                user_id=user_id,
                plan_id=plan.id,
                tasks=created_tasks,
                context=context,
                data_origin=SYNTHETIC,
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        shadow_after = self._synthetic.count_shadow(user_id, data_origin=SYNTHETIC)
        level2_date = context.state.date if context.state is not None else None
        if context.state is None:
            warnings.append(
                "Level 2 is unavailable: "
                + (", ".join(context.degraded_reasons) or "no state")
            )
        if written == 0:
            warnings.append(
                "Level 3 shadow produced no rows (check Level 1/2 availability)."
            )
        return SyntheticImportSummary(
            scenario=resolved.name,
            days_imported=len(days),
            tasks_imported=len(created_tasks),
            executions_imported=executions,
            feedback_imported=feedback_count,
            level1_status="ready" if context.trait is not None else "unavailable",
            level2_status="ready" if context.state is not None else "unavailable",
            level2_observed_on=level2_date,
            shadow_runs_before=shadow_before,
            shadow_runs_after=shadow_after,
            warnings=warnings,
        )

    def reset(self, user_id: int) -> SyntheticResetSummary:
        self.require_enabled()
        self._reject_showcase(user_id)
        try:
            deleted = self._synthetic.delete_for_user(user_id)
            self._session.flush()
            had_synthetic_trait = deleted.get("trait_assessments", 0) > 0
            real_trait = self._synthetic.has_real_trait(user_id)
            if real_trait:
                latest_real = self._assessments.get_latest_completed_for_user(user_id)
                if latest_real is not None and latest_real.trait_profile is not None:
                    self._users.update_fields(
                        user_id,
                        trait_profile=latest_real.trait_profile,
                        trait_model_version=latest_real.model_version or None,
                        trait_artifact_hash=latest_real.artifact_hash or None,
                        trait_feature_version=latest_real.feature_version or None,
                    )
            elif had_synthetic_trait:
                # The current snapshot may have come from the synthetic import.
                self._users.update_fields(
                    user_id,
                    trait_profile=None,
                    trait_model_version=None,
                    trait_artifact_hash=None,
                    trait_feature_version=None,
                )
            self._states.delete_by_user(user_id)
            self._session.flush()
            if real_trait and self._synthetic.has_real_observations(user_id):
                self._user_models.refresh_dynamic_state(user_id, commit=False)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        context = self._user_models.context(user_id)
        return SyntheticResetSummary(
            deleted={key: value for key, value in deleted.items() if value},
            level1_status="ready" if context.trait is not None else "unavailable",
            level2_status="ready" if context.state is not None else "unavailable",
            warnings=(
                ["Level 1 is now unavailable; complete the initial assessment again."]
                if context.trait is None
                else []
            ),
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _require_user(self, user_id: int) -> None:
        if self._users.get_by_id(user_id) is None:
            raise NotFoundError("user not found")

    def _resolve_scenario(
        self, scenario_name: str | None, scenario: SyntheticScenario | None
    ) -> SyntheticScenario:
        if scenario is not None:
            return scenario
        name = (scenario_name or "").strip()
        if not name or "/" in name or "\\" in name or ".." in name:
            raise DomainValidationError("invalid scenario_name")
        path = FIXTURE_DIR / f"{name}.json"
        if not path.exists():
            raise NotFoundError(f"scenario not found: {name}")
        try:
            return SyntheticScenario.model_validate(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except Exception as exc:  # noqa: BLE001
            raise DomainValidationError(f"invalid scenario: {exc}") from exc

    def _preserve_real_trait_snapshot(self, user_id: int) -> None:
        """Keep a pre-existing real trait recoverable across synthetic reset.

        A user can import a validated Level 1 profile without a CAT assessment.
        Before a synthetic scenario overwrites the current snapshot, persist that
        snapshot as a real completed assessment so reset can restore it. Do not
        do this when the current snapshot already came from synthetic data.
        """
        if self._synthetic.has_real_trait(user_id):
            return
        if self._synthetic.counts(user_id).get("trait_assessments", 0) > 0:
            return
        current = self._user_models.get_trait_profile(user_id)
        if current is None:
            return
        meta = self._runtime.level1.metadata
        now = datetime.now(UTC)
        self._assessments.create(
            TraitAssessment(
                id=uuid4().hex,
                user_id=user_id,
                status="completed",
                responses=[],
                rr_index=0,
                trait_profile=current,
                model_version=meta.model_version,
                calibration_version=meta.artifact_version,
                artifact_hash=meta.artifact_hash,
                feature_version=meta.feature_version,
                data_origin="real",
                created_at=now,
                updated_at=now,
                completed_at=now,
            )
        )

    def _apply_level1(self, user_id: int, scenario: SyntheticScenario) -> None:
        level1 = scenario.level1
        if level1 is None:
            return
        self._preserve_real_trait_snapshot(user_id)
        meta = self._runtime.level1.metadata
        now = datetime.now(UTC)
        if level1.responses is not None:
            session = self._runtime.level1.new_session()
            for item in level1.responses:
                self._runtime.level1.record_response(session, item.item_id, item.response)
            profile = self._runtime.level1.profile_from_session(session)
            payload = profile.model_dump(mode="json")
            self._user_models.set_trait_profile(user_id, payload)
            responses = [item.model_dump(mode="json") for item in level1.responses]
            rr_index = session.rr_index
        elif level1.trait_profile is not None:
            self._user_models.set_trait_profile(user_id, level1.trait_profile)
            payload = self._user_models.get_trait_profile(user_id) or {}
            responses = []
            rr_index = 0
        else:  # pragma: no cover - DTO validator prevents this
            raise DomainValidationError("scenario level1 is empty")

        self._assessments.create(
            TraitAssessment(
                id=uuid4().hex,
                user_id=user_id,
                status="completed",
                responses=responses,
                rr_index=rr_index,
                trait_profile=payload,
                model_version=meta.model_version,
                calibration_version=meta.artifact_version,
                artifact_hash=meta.artifact_hash,
                feature_version=meta.feature_version,
                data_origin=SYNTHETIC,
                created_at=now,
                updated_at=now,
                completed_at=now,
            )
        )