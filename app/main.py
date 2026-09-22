"""FastAPI application entry point.

Run with::

    uv run uvicorn app.main:app --reload

OpenAPI docs: /docs (Swagger UI) and /redoc (ReDoc).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.router import api_router
from app.application.exceptions import ApplicationError
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.infrastructure.database import init_db
from app.schemas.common import ErrorResponse, HealthResponse

logger = logging.getLogger(__name__)

_DESCRIPTION = """
Feedback-driven adaptive task planning backend.

Pipeline: goals -> theoretical workload -> user situation (ML) -> plan generation
(LangGraph) -> hard-constraint rule validation -> heuristic scheduling -> execution
feedback -> user model update -> replanning.

Layering: API -> Application -> Domain -> Infrastructure. LLM output never decides
hard constraints; the Rule Engine does.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings)
    # Convenience for local SQLite development; use Alembic for PostgreSQL.
    if settings.is_sqlite:
        init_db()
    # Warm up the agent checkpointer so the LangGraph checkpoint tables exist
    # before the first preview/confirm request. If Postgres is unreachable the
    # factory logs loudly and degrades to in-memory (previews then do not survive
    # a restart) - it never blocks startup.
    try:
        from app.agent.checkpointer import get_checkpointer, get_checkpointer_mode

        get_checkpointer(settings)
        logger.info("agent checkpointer ready: %s", get_checkpointer_mode())
    except Exception as exc:  # noqa: BLE001 - startup must never fail on this
        logger.warning("agent checkpointer warm-up failed: %s: %s", type(exc).__name__, exc)
    yield
    # Release the checkpointer's connection pool so shutdown leaves no open
    # Postgres sockets behind (no-op when running on the in-memory saver).
    try:
        from app.agent.checkpointer import close_checkpointer

        close_checkpointer()
    except Exception as exc:  # noqa: BLE001 - shutdown must never fail on this
        logger.warning("agent checkpointer shutdown failed: %s: %s", type(exc).__name__, exc)
    # Stop background generation workers (join briefly) and release their DB
    # sessions before the LLM client and engine pools are torn down.
    try:
        from app.api.deps import close_generation_service

        close_generation_service()
    except Exception as exc:  # noqa: BLE001 - shutdown must never fail on this
        logger.warning("generation service shutdown failed: %s: %s", type(exc).__name__, exc)
    # Release the process-wide LLM client's HTTP connection pool.
    try:
        from app.infrastructure.llm.client import close_llm_client

        close_llm_client()
    except Exception as exc:  # noqa: BLE001 - shutdown must never fail on this
        logger.warning("llm client shutdown failed: %s: %s", type(exc).__name__, exc)
    # Dispose the SQLAlchemy engine so pooled DB connections are closed cleanly.
    try:
        from app.infrastructure.database import engine

        engine.dispose()
    except Exception as exc:  # noqa: BLE001 - shutdown must never fail on this
        logger.warning("db engine shutdown failed: %s: %s", type(exc).__name__, exc)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=_DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    allow_all = "*" in settings.cors_origin_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=not allow_all,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ApplicationError)
    async def application_error_handler(_: Request, exc: ApplicationError) -> JSONResponse:
        payload = ErrorResponse(code=exc.code, message=exc.message, detail=exc.detail)
        return JSONResponse(status_code=exc.http_status, content=payload.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        payload = ErrorResponse(
            code="validation_error",
            message="request validation failed",
            detail={"errors": jsonable_encoder(exc.errors())},
        )
        return JSONResponse(status_code=422, content=payload.model_dump(mode="json"))

    @app.get("/health", response_model=HealthResponse, tags=["system"], summary="Health check")
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            app=settings.app_name,
            version=__version__,
            environment=settings.environment,
        )

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()


def run() -> None:  # pragma: no cover - console entry point
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
