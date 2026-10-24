"""``UserModelRuntime`` - the single facade over Level 1 / 2 / 3.

The application layer talks to this object only. It owns:

* artifact loading + version/hash metadata (no caller reads files);
* typed snapshots for Level 1 and Level 2;
* Level 3 inference (called by the shadow runner only in this version);
* the configured Level 3 mode.

Failure policy: construction never raises. A layer that fails to load is marked
``UNAVAILABLE`` and its methods raise :class:`ModelUnavailableError`; callers
degrade deterministically instead of crashing the planner.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.user_models.contracts import (
    DynamicStateSnapshot,
    HistoryBundle,
    Level3Mode,
    Level3Prediction,
    ModelMetadata,
    ModelStatus,
    TaskPredictionContext,
    TraitSnapshot,
    UserModelContext,
)
from app.user_models.errors import ModelUnavailableError
from app.user_models.level1.runtime import Level1Runtime
from app.user_models.level2.runtime import Level2Runtime
from app.user_models.level3 import schemas as level3_schemas
from app.user_models.level3.runtime import Level3Runtime
from app.user_models.level3.validation import sha256_file

logger = logging.getLogger(__name__)


def resolve_level3_mode(raw: str | None) -> tuple[Level3Mode, str | None]:
    """Parse the configured mode. ``active`` is intentionally not open yet."""
    try:
        requested = Level3Mode(str(raw or Level3Mode.SHADOW.value).strip().lower())
    except ValueError:
        logger.warning("invalid LEVEL3_MODE %r; falling back to shadow", raw)
        return Level3Mode.SHADOW, "invalid_mode"
    if requested is Level3Mode.ACTIVE:
        logger.warning(
            "LEVEL3_MODE=active is not opened for production control in v1; "
            "running Level 3 in shadow mode"
        )
        return Level3Mode.SHADOW, "active_not_open"
    return requested, None


class UserModelRuntime:
    """Facade injected into the application layer (and therefore into the agent)."""

    def __init__(
        self,
        *,
        level1: Level1Runtime | None = None,
        level2: Level2Runtime | None = None,
        level3: Level3Runtime | None = None,
        requested_mode: str | Level3Mode | None = None,
    ) -> None:
        self.level1 = level1 or Level1Runtime()
        self.level2 = level2 or Level2Runtime()
        self.level3 = level3 or Level3Runtime()
        if isinstance(requested_mode, Level3Mode):
            raw_mode = requested_mode.value
        else:
            raw_mode = requested_mode
        try:
            self.requested_mode = Level3Mode(
                str(raw_mode or Level3Mode.SHADOW.value).strip().lower()
            )
        except ValueError:
            self.requested_mode = Level3Mode.SHADOW
        self.mode, self.mode_reason = resolve_level3_mode(raw_mode)
        if self.mode_reason in {"invalid_mode", "active_not_open"}:
            self.mode = Level3Mode.SHADOW

    @classmethod
    def from_settings(cls) -> UserModelRuntime:
        from app.core.config import get_settings

        settings = get_settings()
        return cls(requested_mode=getattr(settings, "level3_mode", "shadow"))

    # -- metadata ----------------------------------------------------------
    def metadata(self) -> tuple[ModelMetadata, ...]:
        items: list[ModelMetadata] = [self.level1.metadata, self.level2.metadata]
        level3_meta = self.level3.metadata
        if self.mode is Level3Mode.OFF:
            level3_meta = level3_meta.model_copy(update={"mode": Level3Mode.OFF})
        else:
            level3_meta = level3_meta.model_copy(
                update={
                    "mode": self.mode,
                    "degraded_reason": (
                        self.mode_reason
                        if self.mode_reason and self.mode_reason != "active_not_open"
                        else level3_meta.degraded_reason
                    ),
                }
            )
        items.append(level3_meta)
        return tuple(items)

    @property
    def level1_available(self) -> bool:
        return self.level1.available

    @property
    def level2_available(self) -> bool:
        return self.level2.available

    @property
    def level3_available(self) -> bool:
        return self.level3.available

    def ensure_artifact_integrity(self) -> list[str]:
        """Re-hash the Level 1/2/3 source artifacts; return problems."""
        problems: list[str] = []
        for level, runtime in (
            ("level1", self.level1),
            ("level2", self.level2),
            ("level3", self.level3),
        ):
            if not runtime.available:
                problems.append(f"{level}:unavailable")
                continue
            for name in getattr(runtime, "artifact_files", []):
                if sha256_file(runtime.root / name) is None:  # pragma: no cover - defensive
                    problems.append(f"{level}:{name}")
        return problems

    # -- Level 1 / 2 snapshots --------------------------------------------
    def trait_snapshot(self, profile: dict | None) -> TraitSnapshot | None:
        if profile is None:
            return None
        if not self.level1.available:
            raise ModelUnavailableError(self.level1.error or "level1 unavailable")
        return self.level1.snapshot(profile)

    def state_snapshot(self, profile: dict | None) -> DynamicStateSnapshot | None:
        if profile is None:
            return None
        if not self.level2.available:
            raise ModelUnavailableError(self.level2.error or "level2 unavailable")
        return self.level2.snapshot(profile)

    def build_context(
        self,
        *,
        trait_profile: dict | None,
        state_profile: dict | None,
        history: HistoryBundle | None = None,
    ) -> UserModelContext:
        """Build the typed context used by the agent.

        Never raises: missing/broken models become ``degraded`` + reasons.
        """
        reasons: list[str] = []
        trait: TraitSnapshot | None = None
        state: DynamicStateSnapshot | None = None

        if trait_profile is not None:
            try:
                trait = self.trait_snapshot(trait_profile)
            except Exception as exc:  # noqa: BLE001 - degrade, never crash planning
                reasons.append(f"level1:{type(exc).__name__}")
        else:
            reasons.append("level1:no_trait_profile")

        if state_profile is not None:
            try:
                state = self.state_snapshot(state_profile)
            except Exception as exc:  # noqa: BLE001
                reasons.append(f"level2:{type(exc).__name__}")
        else:
            reasons.append("level2:no_state_profile")

        return UserModelContext(
            trait=trait,
            state=state,
            history=history,
            metadata=self.metadata(),
            degraded=bool(reasons),
            degraded_reasons=tuple(reasons),
            level3_mode=self.mode,
        )

    # -- Level 3 -----------------------------------------------------------
    def build_level3_input(
        self,
        *,
        trait: TraitSnapshot,
        state: DynamicStateSnapshot,
        task: TaskPredictionContext,
        history: HistoryBundle,
        prediction_timestamp: datetime | None = None,
    ) -> level3_schemas.Level3PredictionInput:
        """Convert typed snapshots into the model's own input contract."""
        domains = trait.domains
        trait_input = level3_schemas.TraitInput(
            theta_n=domains["N"].theta,
            theta_e=domains["E"].theta,
            theta_o=domains["O"].theta,
            theta_a=domains["A"].theta,
            theta_c=domains["C"].theta,
            se_n=domains["N"].se,
            se_e=domains["E"].se,
            se_o=domains["O"].se,
            se_a=domains["A"].se,
            se_c=domains["C"].se,
            model_version=trait.model_version,
            schema_version=trait.schema_version,
        )
        state_input = level3_schemas.StateInput(
            fatigue=state.fatigue.value,
            fatigue_uncertainty=state.fatigue.uncertainty,
            stress=state.stress.value,
            stress_uncertainty=state.stress.uncertainty,
            self_efficacy=state.self_efficacy.value,
            self_efficacy_uncertainty=state.self_efficacy.uncertainty,
            model_version=state.model_version,
        )
        timestamp = prediction_timestamp or datetime.now(UTC)
        task_input = level3_schemas.TaskInput(
            task_id=task.task_id,
            estimated_duration_minutes=task.estimated_duration_minutes,
            difficulty=task.difficulty,
            deadline=task.deadline,
            planned_start=task.planned_start,
            task_type=task.task_type,
        )
        context_input = level3_schemas.ContextInput(
            prediction_timestamp=timestamp,
            time_of_day=task.time_of_day,
            available_time_minutes=task.available_time_minutes,
        )
        history_input = level3_schemas.HistoryInput(
            completion_history=list(history.completion_history),
            duration_ratio_history=list(history.duration_ratio_history),
            similar_duration_ratio_history=list(history.similar_duration_ratio_history),
            recent_goal_attainment=history.recent_goal_attainment,
            support=level3_schemas.HistorySupport(
                total_historical_tasks=history.total_historical_tasks,
                completed_task_count=history.completed_task_count,
                failed_task_count=history.failed_task_count,
                usable_duration_samples=history.usable_duration_samples,
                similar_task_sample_count=history.similar_task_sample_count,
                similar_task_type=history.similar_task_type,
            ),
        )
        return level3_schemas.Level3PredictionInput(
            trait=trait_input,
            state=state_input,
            task=task_input,
            context=context_input,
            history=history_input,
        )

    def predict_level3(self, inp: level3_schemas.Level3PredictionInput) -> Level3Prediction:
        if self.mode is Level3Mode.OFF:
            raise ModelUnavailableError("level3 is off")
        if not self.level3.available:
            raise ModelUnavailableError(self.level3.error or "level3 unavailable")
        return self.level3.predict(inp)

    def describe(self) -> dict:
        return {
            "requested_mode": self.requested_mode.value,
            "effective_mode": self.mode.value,
            "mode_reason": self.mode_reason,
            "layers": [
                {
                    "level": meta.level.value,
                    "model_version": meta.model_version,
                    "artifact_version": meta.artifact_version,
                    "artifact_hash": meta.artifact_hash,
                    "feature_version": meta.feature_version,
                    "status": meta.status.value,
                    "mode": meta.mode.value if meta.mode else None,
                    "degraded_reason": meta.degraded_reason,
                }
                for meta in self.metadata()
            ],
        }

    def status_for_level3(self) -> ModelStatus:
        return self.level3.metadata.status


__all__ = ["UserModelRuntime", "resolve_level3_mode"]