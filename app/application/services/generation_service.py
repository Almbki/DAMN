"""Generation service: durable background plan-generation jobs + live SSE.

A job is submitted with :meth:`GenerationService.submit`, which persists the
initial row and starts one daemon worker thread. The worker builds its own
``PlanService`` (and thus its own DB session, decoupled from the request
session), runs the caller supplied ``runner`` and records every emitted event on
the job. The SSE endpoint follows the job live via a per-job
:class:`_Channel`, replaying any events that were already recorded before the
subscriber arrived.

Every event snapshot is also written to ``generation_jobs`` using a short-lived
session (never the request's or the worker's business session). After a restart
the in-memory registry is empty, so :meth:`get_job` rehydrates the stored
status/result/events, and terminal jobs can still be streamed. A persisted
``pending``/``running`` job is an orphan (its thread died with the previous
process): it is marked failed instead of leaving subscribers waiting forever.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.application.dto.generation import AgentEvent, GenerationJob, JobStatus
from app.application.exceptions import NotFoundError, PermissionDeniedError
from app.application.services.plan_service import PlanService
from app.core.config import get_settings
from app.domain.models import GenerationJobRecord
from app.infrastructure.database import SessionLocal
from app.infrastructure.database.repositories import GenerationJobRepository

logger = logging.getLogger(__name__)

#: Event sink handed to a runner: ``emit(event_name, payload)``.
Emit = Callable[[str, dict], None]

_TERMINAL_STATUSES = frozenset({JobStatus.COMPLETED, JobStatus.FAILED})
_HEARTBEAT_SECONDS = 15.0
_JOIN_TIMEOUT_SECONDS = 5.0
_ORPHAN_ERROR = "generation job was interrupted by a server restart"


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
    """In-memory job registry with durable snapshots and one daemon thread/job.

    ``service_factory`` is called on the worker thread so every run gets a fresh
    :class:`PlanService` with its own DB session, decoupled from the request
    session that called :meth:`submit`. ``session_factory`` is used only for the
    short-lived job-persistence sessions (one per status/event write).
    """

    def __init__(
        self,
        service_factory: Callable[[], PlanService] | None = None,
        *,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self._service_factory = service_factory
        self._session_factory = session_factory or SessionLocal
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
        """Register a RUNNING job, persist it and start its worker."""
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
        # Persist before the thread starts so a poll that arrives immediately
        # sees the job even if this process dies right after accepting it.
        self._persist_job(job)
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

    def get_job(self, job_id: str, user_id: int) -> GenerationJob:
        """Return the live job, or rehydrate it from the durable row."""
        self._purge_expired()
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            record = self._load_record(job_id)
            if record is None:
                raise NotFoundError("generation job not found")
            if record.user_id != user_id:
                raise PermissionDeniedError("job belongs to another user")
            return _record_to_dto(record)
        if job.user_id != user_id:
            raise PermissionDeniedError("job belongs to another user")
        return job

    def get_status(self, job_id: str, user_id: int) -> dict:
        """Thread-safe snapshot of a job, safe to poll from another thread."""
        job = self.get_job(job_id, user_id)
        if not self._is_live(job_id):
            # A durable non-terminal row has no worker in this process.
            job = self._recover_if_orphaned(job)
            return _snapshot(job)
        channel = self._channel_for(job_id)
        with channel.condition:
            return _snapshot(job)

    def latest_preview(self, user_id: int) -> dict | None:
        """Newest completed resumable preview result for ``user_id`` (or None).

        The persisted result is returned verbatim; the API layer validates it
        against ``PreviewResponse``. Being "actionable" only means the result
        still has ``thread_id`` + ``preview`` - the graph checkpoint itself may
        have expired since, in which case confirm returns 404 / the existing plan
        (documented at the endpoint).
        """
        record = self._with_repository(
            lambda repo: repo.latest_actionable_preview(user_id)
        )
        return dict(record.result) if record is not None and record.result else None

    # -- SSE ---------------------------------------------------------------
    def stream_sse(self, job_id: str, user_id: int) -> Iterator[str]:
        """Yield Server-Sent Events for a job as they happen.

        Live jobs replay already-recorded events and then follow the worker's
        channel. A job rehydrated from the durable row has no live channel:
        terminal jobs replay every stored event followed by their terminal
        frame; non-terminal jobs are orphans and are failed before replaying.
        Node-completed events are re-emitted with the **node name as the event
        name**, so the documented stage contract
        (``goal_analysis`` ... ``plan_repair``) holds.
        """
        job = self.get_job(job_id, user_id)
        if not self._is_live(job_id):
            job = self._recover_if_orphaned(job)
            for event in list(job.events):
                yield _frame(event)
            yield _terminal_frame(job)
            return

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

    # -- recovery ----------------------------------------------------------
    def recover_orphaned_jobs(self) -> int:
        """Mark every persisted pending/running job as failed (startup)."""
        return recover_orphaned_generation_jobs(self._session_factory)

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
                # Persist the full snapshot while holding the lock so a slower
                # write can never overwrite a newer terminal snapshot.
                self._persist_job(job)
                channel.condition.notify_all()

        try:
            service = self._build_service()
            result = runner(service, sink)
            # Publish the terminal state under the channel lock: the subscriber
            # may be waiting for the final `completed` frame, which must already
            # carry the job result.
            with channel.condition:
                job.result = dict(result or {})
                plan_id = job.result.get("plan_id")
                if isinstance(plan_id, int):
                    job.plan_id = plan_id
                job.status = JobStatus.COMPLETED
                self._persist_job(job)
                channel.condition.notify_all()
        except Exception as exc:  # noqa: BLE001 - a failed job must not kill the thread
            with channel.condition:
                job.error = f"{type(exc).__name__}: {exc}"
                job.status = JobStatus.FAILED
                self._persist_job(job)
                channel.condition.notify_all()
        finally:
            if service is not None:
                try:
                    service.close()
                except Exception:  # noqa: BLE001 - best-effort cleanup
                    pass
            with channel.condition:
                channel.condition.notify_all()

    def _build_service(self) -> PlanService:
        return self._service_factory()

    def _channel_for(self, job_id: str) -> _Channel:
        with self._lock:
            channel = self._channels.get(job_id)
            if channel is None:
                channel = _Channel()
                self._channels[job_id] = channel
            return channel

    def _is_live(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._jobs

    # -- persistence -------------------------------------------------------
    def _with_repository(self, operation):
        """Run ``operation`` against a fresh session, then close it."""
        session = self._session_factory()
        try:
            repo = GenerationJobRepository(session)
            result = operation(repo)
            session.commit()
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _load_record(self, job_id: str) -> GenerationJobRecord | None:
        try:
            return self._with_repository(lambda repo: repo.get_by_job_id(job_id))
        except Exception as exc:  # noqa: BLE001 - a read failure is a 404, not a 500
            logger.warning("could not read generation job %s: %s", job_id, exc)
            return None

    def _persist_job(self, job: GenerationJob) -> None:
        """Write the current job snapshot; never fail the worker on DB errors."""
        record = GenerationJobRecord(
            job_id=job.job_id,
            user_id=job.user_id,
            kind=job.kind,
            status=job.status.value,
            plan_id=job.plan_id,
            result=job.result,
            error=job.error,
            events=[event.model_dump(mode="json") for event in job.events],
            created_at=job.created_at,
            updated_at=datetime.now(UTC),
        )
        try:
            self._with_repository(lambda repo: repo.upsert(record))
        except Exception as exc:  # noqa: BLE001 - persistence is best-effort
            logger.warning("could not persist generation job %s: %s", job.job_id, exc)

    def _recover_if_orphaned(self, job: GenerationJob) -> GenerationJob:
        """Fail a durable non-terminal job that has no worker in this process."""
        if job.status in _TERMINAL_STATUSES:
            return job
        job.status = JobStatus.FAILED
        job.error = _ORPHAN_ERROR
        self._persist_job(job)
        logger.warning("generation job %s was orphaned; marked failed", job.job_id)
        return job

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


def recover_orphaned_generation_jobs(
    session_factory: Callable[[], Session] | None = None,
    *,
    error: str = _ORPHAN_ERROR,
) -> int:
    """Startup crash recovery: fail every persisted pending/running job.

    Called from ``app.main.lifespan``. Returns the number of jobs updated.
    """
    factory = session_factory or SessionLocal
    session = factory()
    try:
        count = GenerationJobRepository(session).fail_active_jobs(error)
        session.commit()
        return count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _record_to_dto(record: GenerationJobRecord) -> GenerationJob:
    return GenerationJob(
        job_id=record.job_id,
        user_id=record.user_id,
        kind=record.kind,
        status=JobStatus(record.status),
        plan_id=record.plan_id,
        result=record.result,
        error=record.error,
        events=[AgentEvent.model_validate(event) for event in record.events],
        created_at=record.created_at,
    )


def _snapshot(job: GenerationJob) -> dict:
    return {
        "job_id": job.job_id,
        "kind": job.kind,
        "status": job.status.value,
        "result": job.result,
        "error": job.error,
        "events": [event.model_dump(mode="json") for event in job.events],
    }


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


__all__ = [
    "Emit",
    "GenerationService",
    "recover_orphaned_generation_jobs",
]
