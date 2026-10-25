"""Application settings.

Single source of truth for configuration. Import via :func:`get_settings`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Project root (``app/core/config.py`` -> ``app/core`` -> ``app`` -> root).
#: Resolve the .env absolutely so running uvicorn from ``app/`` (or any other
#: CWD) cannot silently fall back to the built-in defaults (mock LLM, SQLite).
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Environment driven settings (Pydantic v2 / pydantic-settings)."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
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
    # How structured JSON output is requested. "json_object" is portable
    # (response_format={"type": "json_object"}); "json_schema" asks for OpenAI
    # Structured Outputs, which DeepSeek rejects with HTTP 400
    # ("This response_format type is unavailable now").
    llm_response_format: str = "json_object"

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
    # Feedback replan policy thresholds (see app.domain.feedback.policy).
    agent_feedback_stress_high: float = Field(default=7.0, ge=0.0, le=10.0)
    agent_feedback_energy_low: float = Field(default=4.0, ge=0.0, le=10.0)
    agent_feedback_stress_severe: float = Field(default=8.0, ge=0.0, le=10.0)
    agent_feedback_energy_critical: float = Field(default=3.0, ge=0.0, le=10.0)
    agent_feedback_duration_bias_high: float = Field(default=0.50, ge=0.0, le=1.0)

    # --- Reflection evidence extraction -----------------------------------
    #: "auto" = LLM when a real provider is configured (rules take over on
    #: failure); "llm" = prefer the LLM; "rule" = deterministic rules only.
    #: A mock/dummy llm_provider always uses the deterministic rules.
    evidence_extractor: str = "auto"

    # --- Three-layer user model -------------------------------------------
    #: off = do not run Level 3; shadow = run + log but never control the plan;
    #: active = reserved (v1 downgrades it to shadow, see user_models.runtime).
    level3_mode: str = "shadow"
    #: Minimum days between completed Level 1 reassessments. 0 disables it.
    trait_reassessment_cooldown_days: int = Field(default=30, ge=0)
    #: Daily Level-2 state history retention (old `daily_states` rows are pruned).
    daily_state_retention_days: int = Field(default=180, ge=1)

    # --- Developer/demo tools ---------------------------------------------
    #: Synthetic scenario import is a demo/test tool; disabled by default.
    enable_synthetic_import: bool = False

    @field_validator("level3_mode")
    @classmethod
    def _valid_level3_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"off", "shadow", "active"}:
            raise ValueError("level3_mode must be 'off', 'shadow' or 'active'")
        return normalized

    @field_validator("cors_origins")
    @classmethod
    def _strip_origins(cls, value: str) -> str:
        return value.strip()

    @field_validator("llm_response_format")
    @classmethod
    def _valid_llm_response_format(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"json_object", "json_schema"}:
            raise ValueError("llm_response_format must be 'json_object' or 'json_schema'")
        return normalized

    @field_validator("evidence_extractor")
    @classmethod
    def _valid_evidence_extractor(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"auto", "llm", "rule"}:
            raise ValueError("evidence_extractor must be 'auto', 'llm' or 'rule'")
        return normalized

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
