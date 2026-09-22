"""Application settings.

Single source of truth for configuration. Import via :func:`get_settings`.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment driven settings (Pydantic v2 / pydantic-settings)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application -------------------------------------------------------
    app_name: str = "AI Adaptive Task Planner"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "*"

    # --- Database ----------------------------------------------------------
    database_url: str = "sqlite:///./dev.db"
    db_echo: bool = False

    # --- Auth --------------------------------------------------------------
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    password_hash_iterations: int = 480_000

    # --- LLM ---------------------------------------------------------------
    llm_provider: str = "mock"
    llm_api_base: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "mock-model"
    llm_timeout_seconds: float = 30.0

    # --- Scheduler / rules -------------------------------------------------
    scheduler_daily_limit_minutes: int = Field(default=300, ge=1)
    scheduler_buffer_minutes: int = Field(default=15, ge=0)
    scheduler_high_cognitive_max_per_day: int = Field(default=2, ge=1)
    scheduler_min_replan_interval_hours: int = Field(default=24, ge=0)

    # --- Generation jobs / SSE --------------------------------------------
    generation_job_ttl_seconds: int = Field(default=1800, ge=60)

    # --- Agent layer -------------------------------------------------------
    # "auto" -> Postgres checkpointer when DATABASE_URL is Postgres, else memory.
    agent_checkpointer: str = "auto"
    # Maximum user-requested preview adjustments before the user is pushed to
    # execution (no more LLM regeneration).
    agent_max_preview_adjustments: int = Field(default=3, ge=0)
    # Maximum plan_repair rounds before the graph gives up.
    agent_max_repair_attempts: int = Field(default=2, ge=1)
    agent_llm_max_retries: int = Field(default=2, ge=0)
    agent_llm_timeout_seconds: float = 30.0
    agent_graph_version: str = "planner-v1"
    agent_prompt_version: str = "v1"
    agent_trace_enabled: bool = True

    @field_validator("cors_origins")
    @classmethod
    def _strip_origins(cls, value: str) -> str:
        return value.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a list."""
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in {"development", "dev", "local"}

    @property
    def checkpointer_mode(self) -> str:
        """Resolved checkpointer backend: ``postgres`` or ``memory``."""
        if self.agent_checkpointer != "auto":
            return self.agent_checkpointer
        return "postgres" if self.database_url.startswith("postgresql") else "memory"

    @property
    def checkpointer_dsn(self) -> str:
        """libpq DSN for the LangGraph checkpointer (no SQLAlchemy driver suffix)."""
        return self.database_url.replace("+psycopg", "").replace("+psycopg2", "")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()
