"""FastAPI application entry point.

Run with::

    uv run uvicorn app.main:app --reload

OpenAPI docs: /docs (Swagger UI) and /redoc (ReDoc).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.router import api_router
from app.application.exceptions import ApplicationError
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.infrastructure.database import init_db
from app.schemas.common import ErrorResponse, HealthResponse

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
    yield


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
