"""Generation service: real background plan-generation jobs + live SSE.

A job is submitted with :meth:`GenerationService.submit`, which registers it and
starts one daemon worker thread. The worker builds its own ``PlanService`` (and
thus its own DB session, decoupled from the request session), runs the caller
supplied ``runner`` and records every emitted event on the job. The SSE endpoint
follows the job live via a per-job :class:`_Channel`, replaying any events that
were already recorded before the subscriber arrived.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import uuid4

from app.agent.state import PlannerRequest
from app.application.dto.generation import AgentEvent, GenerationJob, JobStatus
from app.application.exceptions import NotFoundError, PermissionDeniedError
from app.application.services.plan_service import PlanService
from app.core.config import get_settings

#: Event sink handed to a runner: ``emit(event_name, payload)``.
Emit = Callable[[str, dict], None]

_TERMINAL_STATUSES = frozenset({JobStatus.COMPLETED, JobStatus.FAILED})
_HEARTBEAT_SECONDS = 15.0
_JOIN_TIMEOUT_SECONDS = 5.0


class _Channel:
    """Per-job wake-up primitive shared by the worker and SSE subscribers."""

    def __init__(self) -> None:
        self.condition = threading.Condition()
        self.closed = False

    def close(self) -> None:
        with self.condition:
            self.closed = True
            self.condition.notify_all()


class GenerationService:
    """In-memory job registry backed by one daemon thread per job.

    ``service_factory`` is called on the worker thread so every run gets a fresh
    :class:`PlanService` with its own DB session, decoupled from the request
    session that called :meth:`submit`.
    """

    def __init__(self, service_factory: Callable[[], PlanService] | None = None) -> None:
        self._service_factory = service_factory
        self._jobs: dict[str, GenerationJob] = {}
        self._channels: dict[str, _Channel] = {}
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._settings = get_settings()

    # -- job lifecycle -----------------------------------------------------
    def submit(
        self,
        *,
        user_id: int,
        kind: str,
        runner: Callable[[PlanService, Emit], dict],
    ) -> GenerationJob:
        """Register a RUNNING job and start its worker; returns immediately."""
        self._purge_expired()
        job = GenerationJob(
            job_id=uuid4().hex,
            user_id=user_id,
            kind=kind,
            status=JobStatus.RUNNING,
        )
        channel = _Channel()
        with self._lock:
            self._jobs[job.job_id] = job
            self._channels[job.job_id] = channel
        thread = threading.Thread(
            target=self._run_job,
            args=(job, channel, runner),
            name=f"generation-{job.job_id}",
            daemon=True,
        )
        with self._lock:
            self._threads.append(thread)
        thread.start()
        return job

    def create_job(
        self, plan_service: PlanService, user_id: int, request: PlannerRequest
    ) -> GenerationJob:
        """Synchronous compatibility path used by ``POST /plans/generate``.

        Runs the full pipeline inline in the caller's thread (legacy behaviour)
        and returns a terminal job. A channel is registered so the SSE endpoint
        can still replay the recorded events.
        """
        self._purge_expired()
        job = GenerationJob(
            job_id=uuid4().hex,
            user_id=user_id,
            kind="generate",
            status=JobStatus.RUNNING,
        )
        channel = _Channel()
        with self._lock:
            self._jobs[job.job_id] = job
            self._channels[job.job_id] = channel
        try:
            detail, run_events = plan_service.generate_plan_with_events(user_id, request)
        except Exception as exc:  # noqa: BLE001 - record then re-raise to the route
            with channel.condition:
                job.error = f"{type(exc).__name__}: {exc}"
                job.status = JobStatus.FAILED
            channel.close()
            raise
        with channel.condition:
            job.events = [AgentEvent.from_dict(event) for event in run_events]
            job.plan_id = detail.plan.id
            job.status = JobStatus.COMPLETED
        channel.close()
        return job

    def get_job(self, job_id: str, user_id: int) -> GenerationJob:
        self._purge_expired()
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise NotFoundError("generation job not found")
        if job.user_id != user_id:
            raise PermissionDeniedError("job belongs to another user")
        return job

    def get_status(self, job_id: str, user_id: int) -> dict:
        """Thread-safe snapshot of a job, safe to poll from another thread."""
        job = self.get_job(job_id, user_id)
        channel = self._channel_for(job_id)
        with channel.condition:
            return {
                "job_id": job.job_id,
                "kind": job.kind,
                "status": job.status.value,
                "result": job.result,
                "error": job.error,
                "events": [event.model_dump(mode="json") for event in job.events],
            }

    # -- SSE ---------------------------------------------------------------
    def stream_sse(self, job_id: str, user_id: int) -> Iterator[str]:
        """Yield Server-Sent Events for a job as they happen.

        Already-recorded events are replayed first, then the generator waits on
        the job's channel for new ones. A late subscriber therefore sees the
        full history, while a live subscriber follows the worker. Node-completed
        events are re-emitted with the **node name as the event name**, so the
        documented stage contract (``goal_analysis`` ... ``plan_repair``) holds.
        """
        job = self.get_job(job_id, user_id)
        channel = self._channel_for(job_id)
        cursor = 0
        while True:
            with channel.condition:
                if (
                    cursor >= len(job.events)
                    and job.status not in _TERMINAL_STATUSES
                    and not channel.closed
                ):
                    channel.condition.wait(timeout=_HEARTBEAT_SECONDS)
                pending = list(job.events[cursor:])
                cursor = len(job.events)
                terminal = job.status in _TERMINAL_STATUSES
                closed = channel.closed
            for event in pending:
                yield _frame(event)
            if terminal and cursor >= len(job.events):
                yield _terminal_frame(job)
                return
            if closed and cursor >= len(job.events):
                return
            if not pending:
                yield ": ping\n\n"

    # -- shutdown ----------------------------------------------------------
    def close(self) -> None:
        """Stop workers and release subscribers (best-effort)."""
        with self._lock:
            channels = list(self._channels.values())
            threads = list(self._threads)
        for channel in channels:
            channel.close()
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=_JOIN_TIMEOUT_SECONDS)

    # -- worker ------------------------------------------------------------
    def _run_job(
        self,
        job: GenerationJob,
        channel: _Channel,
        runner: Callable[[PlanService, Emit], dict],
    ) -> None:
        """Worker-thread body: run the pipeline, record events, never raise."""
        service: PlanService | None = None

        def sink(name: str, payload: dict) -> None:
            event = AgentEvent.from_dict({"event": name, **payload})
            with channel.condition:
                job.events.append(event)
                channel.condition.notify_all()

        try:
            service = self._build_service()
            result = runner(service, sink)
            job.result = dict(result or {})
            plan_id = job.result.get("plan_id")
            if isinstance(plan_id, int):
                job.plan_id = plan_id
            job.status = JobStatus.COMPLETED
        except Exception as exc:  # noqa: BLE001 - a failed job must not kill the thread
            job.error = f"{type(exc).__name__}: {exc}"
            job.status = JobStatus.FAILED
        finally:
            if service is not None:
                try:
                    service.close()
                except Exception:  # noqa: BLE001 - best-effort cleanup
                    pass
            with channel.condition:
                channel.condition.notify_all()

    def _build_service(self) -> PlanService:
        if self._service_factory is not None:
            return self._service_factory()
        return _default_service_factory()

    def _channel_for(self, job_id: str) -> _Channel:
        with self._lock:
            channel = self._channels.get(job_id)
            if channel is None:
                channel = _Channel()
                self._channels[job_id] = channel
            return channel

    def _purge_expired(self) -> None:
        ttl = self._settings.generation_job_ttl_seconds
        now = datetime.now(UTC)
        stale: list[_Channel] = []
        with self._lock:
            expired = [
                job_id
                for job_id, job in list(self._jobs.items())
                if job.status in _TERMINAL_STATUSES
                and (now - job.created_at).total_seconds() > ttl
            ]
            for job_id in expired:
                self._jobs.pop(job_id, None)
                channel = self._channels.pop(job_id, None)
                if channel is not None:
                    stale.append(channel)
            self._threads = [thread for thread in self._threads if thread.is_alive()]
        for channel in stale:
            channel.close()


def _default_service_factory() -> PlanService:
    """Fallback factory when the service is built without one.

    Mirrors ``app.api.deps._plan_service_factory`` so a directly-constructed
    service still gets its own session, LLM and checkpointer.
    """
    from app.agent.checkpointer import get_checkpointer
    from app.agent.llm import StructuredLLM
    from app.infrastructure.database import SessionLocal
    from app.infrastructure.llm.client import get_llm_client

    settings = get_settings()
    llm = StructuredLLM(
        get_llm_client(settings),
        max_retries=settings.agent_llm_max_retries,
        prompt_version=settings.agent_prompt_version,
    )
    return PlanService(SessionLocal(), llm=llm, checkpointer=get_checkpointer(settings))


def _frame(event: AgentEvent) -> str:
    """Format one recorded event as an SSE frame."""
    if event.event == "node.completed" and event.node:
        return _sse(event.node, event.model_dump(mode="json"))
    return _sse(event.stage or event.event, event.model_dump(mode="json"))


def _terminal_frame(job: GenerationJob) -> str:
    """The final frame of a stream (COMPLETED / FAILED)."""
    if job.status == JobStatus.FAILED:
        return _sse(
            "failed",
            {"job_id": job.job_id, "status": job.status.value, "error": job.error},
        )
    return _sse(
        "completed",
        {"job_id": job.job_id, "status": job.status.value, "result": job.result},
    )


def _sse(event: str, data: dict) -> str:
    """Format one SSE frame."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


__all__ = ["Emit", "GenerationService"]
