"""Daily DDSR-V1 orchestration: prior -> correction -> posterior -> tomorrow prior."""

from __future__ import annotations

from collections.abc import Mapping

from .config import DDSRConfig
from .evidence.base import (
    EvidenceExtractionError,
    EvidenceExtractor,
    ExtractionContext,
)
from .evidence.rule_based import RuleBasedEvidenceExtractor
from .schemas import (
    DayInput,
    DynamicStateProfile,
    EvidenceMetadata,
    ExtractionResult,
    NextDayPrior,
    PredictionError,
    SignedVector,
    StateEstimate,
    StateName,
    StateVector,
    UncertaintyVector,
)
from .state_model import (
    PriorState,
    cold_start,
    correct,
    predict_next,
    prediction_error,
)
from .task_metrics import derive_behavioral_indicators
from .trait_context import TraitContext


def _posterior_values(profile: DynamicStateProfile) -> dict[str, float]:
    return profile.current_posterior.as_dict()


def _posterior_uncertainty(profile: DynamicStateProfile) -> dict[str, float]:
    return {
        "fatigue": profile.fatigue.uncertainty,
        "stress": profile.stress.uncertainty,
        "self_efficacy": profile.self_efficacy.uncertainty,
    }


class DDSREngine:
    """Stateful daily engine; feed days in strictly increasing date order."""

    def __init__(
        self,
        config: DDSRConfig | None = None,
        extractor: EvidenceExtractor | None = None,
    ) -> None:
        self.config = config if config is not None else DDSRConfig.from_json()
        self.extractor = (
            extractor
            if extractor is not None
            else RuleBasedEvidenceExtractor(self.config)
        )
        self._previous: DynamicStateProfile | None = None

    def reset(self) -> None:
        self._previous = None

    def _ensure_trait(self, trait: TraitContext | Mapping) -> TraitContext:
        if isinstance(trait, TraitContext):
            return trait
        return TraitContext.from_profile(trait)

    def _make_prior(self, day: DayInput) -> tuple[PriorState, bool, int]:
        if self._previous is None:
            return cold_start(self.config), True, 0
        gap = (day.date - self._previous.date).days
        if gap <= 0:
            raise ValueError(
                "days must be processed in strictly increasing date order; "
                f"got {day.date} after {self._previous.date}"
            )
        if gap == 1:
            stored = self._previous.next_day_prior
            return (
                PriorState(
                    value=stored.value.as_dict(),
                    uncertainty=stored.uncertainty.as_dict(),
                    source="stored_next_day_prior",
                    gap_days=1,
                ),
                False,
                1,
            )
        return (
            predict_next(
                _posterior_values(self._previous),
                _posterior_uncertainty(self._previous),
                self.config,
                steps=gap,
                source="transition_over_gap",
            ),
            False,
            gap,
        )

    def _extract(
        self, day: DayInput
    ) -> tuple[ExtractionResult, str, str | None, bool]:
        reflection = day.reflection
        present = reflection is not None and not reflection.is_empty()
        if not present:
            return ExtractionResult(), "no_reflection", None, False

        known_ids = frozenset(
            [plan.task_id for plan in day.task_plans]
            + [execution.task_id for execution in day.task_executions]
        )
        context = ExtractionContext(
            known_task_ids=known_ids,
            date=day.date,
            min_quote_chars=self.config.min_quote_chars,
        )
        try:
            result = self.extractor.extract(reflection, context)
        except EvidenceExtractionError as exc:
            return ExtractionResult(), "failed", str(exc), True
        except Exception as exc:  # fail closed, never invent evidence
            return (
                ExtractionResult(),
                "failed",
                f"{type(exc).__name__}: {exc}",
                True,
            )
        return result, "ok", None, True

    def process_day(
        self,
        day: DayInput,
        trait: TraitContext | Mapping,
    ) -> DynamicStateProfile:
        trait_context = self._ensure_trait(trait)
        prior, is_cold, gap_days = self._make_prior(day)

        result, extraction_status, extraction_error, reflection_present = self._extract(day)
        extraction_ok = extraction_status == "ok"
        indicators = derive_behavioral_indicators(
            day,
            self.config,
            evidence=result.evidence,
            reflection_present=extraction_ok,
        )
        correction = correct(
            prior,
            evidence=result.evidence,
            indicators=indicators,
            config=self.config,
        )
        raw_error, standardized_error = prediction_error(
            correction.posterior, prior
        )
        next_prior = predict_next(
            correction.posterior,
            correction.uncertainty,
            self.config,
            steps=1,
            source="transition_from_posterior",
        )

        estimates: dict[str, StateEstimate] = {}
        for state in StateName:
            key = state.value
            estimates[key] = StateEstimate(
                observed_on=day.date,
                prior=prior.value[key],
                prior_uncertainty=prior.uncertainty[key],
                value=correction.posterior[key],
                uncertainty=correction.uncertainty[key],
                evidence_availability=correction.evidence_availability[key],
                evidence_count=correction.evidence_counts[key],
                conflict=state in correction.conflict_states,
            )

        limitations = [
            "State scale is a 0-1 engineering scale, not a clinical or published scale.",
            (
                "Persistence and noise parameters are engineering initializations, "
                "not estimated coefficients."
            ),
            "V1 stores prediction errors but does not learn personalized transition parameters.",
        ]
        if not extraction_ok and reflection_present:
            limitations.append(
                "Evidence extraction failed or was invalid; no reflection evidence "
                "was used for this day (fail-closed)."
            )
        if day.passive_context is not None:
            limitations.append(
                "Passive context was received but is intentionally not used in DDSR-V1."
            )

        profile = DynamicStateProfile(
            config_version=self.config.config_version,
            date=day.date,
            cold_start=is_cold,
            gap_days=gap_days,
            source_trait_model=trait_context.source_model(),
            fatigue=estimates["fatigue"],
            stress=estimates["stress"],
            self_efficacy=estimates["self_efficacy"],
            prior=StateVector.from_mapping(prior.value),
            current_posterior=StateVector.from_mapping(correction.posterior),
            prediction_error=PredictionError(
                raw=SignedVector.from_mapping(raw_error),
                standardized=SignedVector.from_mapping(standardized_error),
            ),
            next_day_prior=NextDayPrior(
                value=StateVector.from_mapping(next_prior.value),
                uncertainty=UncertaintyVector.from_mapping(
                    next_prior.uncertainty
                ),
                source=next_prior.source,
            ),
            behavioral_indicators=indicators,
            evidence=EvidenceMetadata(
                extractor=self.extractor.name,
                extractor_version=self.extractor.version,
                extraction_status=extraction_status,
                reflection_fields_present=(
                    day.reflection.present_fields()
                    if day.reflection is not None
                    else []
                ),
                evidence_items=result.evidence,
                conflict_states=correction.conflict_states,
                rejected_item_count=0,
                error=extraction_error,
            ),
            passive_context_used=False,
            passive_context=day.passive_context,
            limitations=limitations,
        )
        self._previous = profile
        return profile

    def replay(
        self,
        days: list[DayInput],
        trait: TraitContext | Mapping,
    ) -> list[DynamicStateProfile]:
        self.reset()
        return [self.process_day(day, trait) for day in days]
