"""Generation service: plan-generation jobs + SSE event stream.

The first version runs the (mock) pipeline synchronously in :meth:`create_job`
and stores the ordered :class:`GenerationEvent` list. The SSE endpoint replays
those events. This keeps the HTTP/SSE contract real while a background worker
(Arq/Celery) is out of scope for the skeleton - marked as PLACEHOLDER.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

from app.agent.state import GenerationRequest
from app.application.dto.generation import GenerationJob, JobStatus
from app.application.exceptions import NotFoundError, PermissionDeniedError
from app.application.services.plan_service import PlanService
from app.core.config import get_settings


class GenerationService:
    """In-memory job registry. The PlanService is passed per request so the
    registry itself can live for the whole process without holding a session."""

    def __init__(self) -> None:
        self._jobs: dict[str, GenerationJob] = {}
        self._settings = get_settings()

    # -- job lifecycle -----------------------------------------------------
    def create_job(
        self, plan_service: PlanService, user_id: int, request: GenerationRequest
    ) -> GenerationJob:
        self._purge_expired()
        job = GenerationJob(job_id=uuid4().hex, user_id=user_id, status=JobStatus.RUNNING)
        self._jobs[job.job_id] = job
        try:
            detail, events = plan_service.generate_plan_with_events(user_id, request)
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)
            raise
        job.events = events
        job.plan_id = detail.plan.id
        job.status = JobStatus.COMPLETED
        return job

    def get_job(self, job_id: str, user_id: int) -> GenerationJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise NotFoundError("generation job not found")
        if job.user_id != user_id:
            raise PermissionDeniedError("job belongs to another user")
        return job

    # -- SSE ---------------------------------------------------------------
    def stream_sse(self, job_id: str, user_id: int) -> Iterator[str]:
        """Yield Server-Sent Events for a completed/failed job."""
        job = self.get_job(job_id, user_id)
        for event in job.events:
            yield _sse(event.stage, event.model_dump(mode="json"))
        if job.status == JobStatus.FAILED:
            yield _sse("failed", {"error": job.error or "generation failed"})
        else:
            yield _sse(
                "completed",
                {
                    "plan_id": job.plan_id,
                    "status": job.status.value,
                    "job_id": job.job_id,
                },
            )

    def _purge_expired(self) -> None:
        ttl = self._settings.generation_job_ttl_seconds
        now = datetime.now(UTC)
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if (now - job.created_at).total_seconds() > ttl
        ]
        for job_id in expired:
            self._jobs.pop(job_id, None)


def _sse(event: str, data: dict) -> str:
    """Format one SSE frame."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
