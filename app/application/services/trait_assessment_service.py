"""Application orchestration for the resumable Level 1 CAT assessment.

All adaptive item selection / posterior updating / stopping is delegated to
``app.user_models.level1.cat`` via ``Level1Runtime``. This service only persists
the minimal session state and owns the transaction.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.application.dto.trait_assessment import (
    TraitAssessmentData,
    TraitAssessmentDomainProgressData,
    TraitAssessmentItemData,
    TraitAssessmentProgressData,
    TraitReassessmentEligibilityData,
)
from app.application.exceptions import ConflictError, NotFoundError
from app.application.services.model_runtime import get_user_model_runtime
from app.application.services.user_model_service import UserModelService
from app.core.config import get_settings
from app.domain.models.trait_assessment import TraitAssessment
from app.infrastructure.database.repositories import (
    TraitAssessmentRepository,
    UserRepository,
)
from app.user_models.errors import ModelInputError, ModelUnavailableError
from app.user_models.runtime import UserModelRuntime


class TraitAssessmentService:
    def __init__(
        self, session: Session, *, runtime: UserModelRuntime | None = None
    ) -> None:
        self._session = session
        self._runtime = runtime or get_user_model_runtime()
        self._assessments = TraitAssessmentRepository(session)
        self._users = UserRepository(session)
        self._user_models = UserModelService(session, runtime=self._runtime)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def start(self, user_id: int, *, restart: bool = False) -> TraitAssessmentData:
        self._require_user(user_id)
        self._require_model()

        active = self._assessments.get_active_for_user(user_id)
        if restart and active is not None:
            # An unfinished session can always be restarted; the completed
            # snapshot cooldown only applies when there is nothing to resume.
            self._assessments.update_fields(active.id, status="abandoned")
            self._session.commit()
            active = None
        elif restart:
            eligibility = self.reassessment_eligibility(user_id)
            if not eligibility.eligible:
                raise ConflictError(
                    "reassessment cooldown active",
                    detail=eligibility.model_dump(mode="json"),
                )
        if active is not None:
            return self._snapshot(active)

        latest = self._assessments.get_latest_for_user(user_id)
        if latest is not None and latest.status == "completed" and not restart:
            if latest.trait_profile is None:
                profile = self._user_models.get_trait_profile(user_id)
                if profile is not None:
                    latest = self._assessments.update_fields(
                        latest.id, trait_profile=profile
                    ) or latest
                    self._session.commit()
            return self._snapshot(latest)

        session = self._runtime.level1.new_session()
        item_id = self._runtime.level1.next_item(session)
        meta = self._runtime.level1.metadata
        now = datetime.now(UTC)
        if item_id is None:  # pragma: no cover - a fresh session always has items
            profile = self._runtime.level1.profile_from_session(session)
            payload = profile.model_dump(mode="json")
            self._user_models.set_trait_profile(user_id, payload)
            assessment = TraitAssessment(
                id=uuid4().hex,
                user_id=user_id,
                status="completed",
                responses=[],
                rr_index=session.rr_index,
                trait_profile=payload,
                model_version=meta.model_version,
                calibration_version=meta.artifact_version,
                artifact_hash=meta.artifact_hash,
                feature_version=meta.feature_version,
                created_at=now,
                updated_at=now,
                completed_at=now,
            )
        else:
            assessment = TraitAssessment(
                id=uuid4().hex,
                user_id=user_id,
                status="in_progress",
                responses=[],
                rr_index=session.rr_index,
                current_item_id=item_id,
                model_version=meta.model_version,
                calibration_version=meta.artifact_version,
                artifact_hash=meta.artifact_hash,
                feature_version=meta.feature_version,
                created_at=now,
                updated_at=now,
            )
        created = self._assessments.create(assessment)
        self._session.commit()
        return self._snapshot(created)

    def get(self, user_id: int, assessment_id: str) -> TraitAssessmentData:
        assessment = self._require_owned(user_id, assessment_id)
        return self._snapshot(assessment)

    def reassessment_eligibility(self, user_id: int) -> TraitReassessmentEligibilityData:
        """Backend authority for the Level 1 reassessment cooldown."""
        self._require_user(user_id)
        settings = get_settings()
        cooldown_days = settings.trait_reassessment_cooldown_days
        latest = self._assessments.get_latest_completed_for_user(user_id)
        completed_at = latest.completed_at if latest is not None else None
        if completed_at is not None and completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=UTC)

        if completed_at is None or cooldown_days <= 0:
            return TraitReassessmentEligibilityData(
                eligible=True,
                cooldown_days=cooldown_days,
                last_completed_at=completed_at,
                next_eligible_at=None,
            )

        next_eligible = completed_at + timedelta(days=cooldown_days)
        return TraitReassessmentEligibilityData(
            eligible=datetime.now(UTC) >= next_eligible,
            cooldown_days=cooldown_days,
            last_completed_at=completed_at,
            next_eligible_at=next_eligible,
        )

    def answer(
        self,
        user_id: int,
        assessment_id: str,
        *,
        item_id: str,
        response: int,
    ) -> TraitAssessmentData:
        assessment = self._require_owned(user_id, assessment_id)
        self._require_model()
        if assessment.status != "in_progress":
            raise ConflictError("assessment is already completed")
        if not self._runtime.level1.item_exists(item_id):
            raise ModelInputError(f"unknown item_id: {item_id}")
        if assessment.current_item_id is not None and item_id != assessment.current_item_id:
            raise ConflictError("stale assessment item; reload the assessment")

        session = self._runtime.level1.session_from_state(
            assessment.responses, assessment.rr_index, assessment.unavailable
        )
        self._runtime.level1.record_response(session, item_id, response)
        responses = [*assessment.responses, {"item_id": item_id, "response": response}]
        next_item = self._runtime.level1.next_item(session)
        now = datetime.now(UTC)
        fields: dict[str, Any] = {
            "responses": responses,
            "rr_index": session.rr_index,
            "updated_at": now,
        }
        if session.completed or next_item is None:
            profile = self._runtime.level1.profile_from_session(session)
            payload = profile.model_dump(mode="json")
            self._user_models.set_trait_profile(user_id, payload)
            fields.update(
                {
                    "status": "completed",
                    "current_item_id": None,
                    "trait_profile": payload,
                    "completed_at": now,
                }
            )
        else:
            fields["current_item_id"] = next_item

        updated = self._assessments.update_fields(assessment.id, **fields)
        self._session.commit()
        if updated is None:  # pragma: no cover - row cannot disappear mid-request
            raise NotFoundError("assessment not found")
        return self._snapshot(updated)

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _require_user(self, user_id: int) -> None:
        if self._users.get_by_id(user_id) is None:
            raise NotFoundError("user not found")

    def _require_model(self) -> None:
        if not self._runtime.level1.available:
            raise ModelUnavailableError(self._runtime.level1.error or "level1 unavailable")

    def _require_owned(self, user_id: int, assessment_id: str) -> TraitAssessment:
        assessment = self._assessments.get_by_id(assessment_id)
        if assessment is None or assessment.user_id != user_id:
            raise NotFoundError("assessment not found")
        return assessment

    def _snapshot(self, assessment: TraitAssessment) -> TraitAssessmentData:
        next_item = None
        progress = self._fallback_progress(assessment)
        try:
            session = self._runtime.level1.session_from_state(
                assessment.responses, assessment.rr_index, assessment.unavailable
            )
            progress = TraitAssessmentProgressData(**self._runtime.level1.progress(session))
            if assessment.status == "in_progress" and assessment.current_item_id:
                next_item = TraitAssessmentItemData(
                    **self._runtime.level1.item_info(assessment.current_item_id)
                )
        except Exception:  # noqa: BLE001 - stored profile remains valid if replay fails
            if assessment.status == "in_progress":
                raise

        return TraitAssessmentData(
            assessment_id=assessment.id,
            status=assessment.status,
            next_item=next_item,
            progress=TraitAssessmentProgressData(
                answered=progress.answered,
                remaining_min=progress.remaining_min,
                remaining_max=progress.remaining_max,
                completed_domains=progress.completed_domains,
                total_domains=progress.total_domains,
                current_domain=progress.current_domain,
                domains={
                    key: TraitAssessmentDomainProgressData(**value.model_dump())
                    for key, value in progress.domains.items()
                },
            ),
            trait_profile=assessment.trait_profile,
            created_at=assessment.created_at,
            updated_at=assessment.updated_at,
            completed_at=assessment.completed_at,
        )

    @staticmethod
    def _fallback_progress(assessment: TraitAssessment) -> TraitAssessmentProgressData:
        answered = len(assessment.responses)
        # 5 domains x 4 min items = 20; 5 domains x 12 max items = 60.
        remaining_min = max(0, 20 - answered)
        remaining_max = max(0, 60 - answered)
        return TraitAssessmentProgressData(
            answered=answered,
            remaining_min=remaining_min,
            remaining_max=remaining_max,
            completed_domains=0,
            total_domains=5,
            current_domain=None,
            domains={},
        )


__all__ = ["TraitAssessmentService"]