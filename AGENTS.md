# AGENTS.md

FastAPI backend for a feedback-driven adaptive task planner: goals → theory
analysis → user-situation (ML) → plan generation (LangGraph) → hard-rule
validation → scheduling → execution feedback → replan.
Python 3.12 · uv · FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · LangGraph.
Single package (`app/`) at the repo root — no monorepo. Windows-first.

## Commands (verified)

- Install: `uv sync --extra dev` (creates `.venv`; requires Python 3.12)
- All tests: `uv run pytest` → 43 tests
- One file / one test: `uv run pytest tests/unit/test_rules.py -q` · `uv run pytest -k scheduler -v`
- Lint: `uv run ruff check .` (line length 100, target py312)
- Run API: `uv run uvicorn app.main:app --reload` → http://localhost:8000/docs
- Migrations: `uv run alembic upgrade head` · `uv run alembic revision --autogenerate -m "..."`
- If a dev tool reports "program not found", install/run with `uv run --extra dev <tool>`.

Use port **8000**. Some Windows ports are OS-reserved and uvicorn fails with
`WinError 10013` (observed on 8123) — not a code bug.

## Architecture rules (easy to violate)

Dependencies flow API → Application → Domain/Core → Infrastructure.
`app/agent` and `app/ml` are side-cars driven by the Application layer.

- `app/core` and `app/domain` must NOT import FastAPI or SQLAlchemy.
- Agents never touch the DB. `PlanService` injects `user_features`, `goal_id_map`,
  `predictors`, `scheduler`, `rule_engine` through `PlannerState`.
- `RuleEngine` (`app/domain/rules/`) is the ONLY authority on hard constraints;
  agent/LLM output is only a candidate.
- `Scheduler` must never call an LLM.
- Repositories never commit — `flush()` only. Services own transactions.
- API never returns ORM/domain objects; map to `app/schemas` via `app/api/v1/mappers.py`.
- Services/agents/repositories/predictors are all synchronous; only the SSE route is async.
  `LLMClient.complete` is synchronous.

## Non-obvious contracts

- **Provisional task ids = `order_index + 1`** while the graph runs (tasks are not yet
  persisted). Used identically by `plan_generation.drafts_to_tasks`,
  `rule_validation.build_rule_context`, the `CandidateSchedule`, and `plan_repair`
  (which re-indexes). `PlanService._persist_plan` remaps them to real PKs.
- **SSE stage names must equal node names** (`goal_analysis`, `theoretical_analysis`,
  `user_situation_analysis`, `plan_generation`, `rule_validation`, `plan_repair`)
  plus `completed`. `GenerationEvent.stage` produces the `event:` line — set it when
  adding events.
- Register new hard rules in `default_rules()` (`app/domain/rules/base.py`) with a
  unique `rule.name` and violation `code`.
- Plan versions are immutable: replan creates `v(n+1)`, marks the old one `superseded`,
  sets `parent_plan_id`, and writes a `ReplanEvent`. Replan cooldown is **per-user**
  (not per-plan) via `ReplanEventRepository.get_latest_for_user`.

## Database & config

- Dev default is SQLite (`DATABASE_URL=sqlite:///./dev.db`). The app `lifespan` runs
  `init_db()` (create_all) **only** for SQLite; Postgres goes through Alembic.
- `alembic.ini` has no `sqlalchemy.url` — `alembic/env.py` reads `Settings`.
  SQLite uses `render_as_batch=True`.
- Never hand-write migrations: `revision --autogenerate`, then review (batch mode
  rewrites tables).
- `get_settings()` is `lru_cache`d — changing `.env` needs a restart or
  `get_settings.cache_clear()`.
- `pyproject.toml` declares `readme = "README.md"`; deleting it breaks `uv sync`/build.

## Testing quirks

- `tests/conftest.py` sets `DATABASE_URL` / `JWT_SECRET_KEY` **before** importing
  `app`, then clears the settings cache. Preserve that import order in new tests.
- Fixtures: `client` (TestClient, runs lifespan), `registered_user`, `auth_headers`
  (Bearer JWT). Schema is created/dropped per session against a file DB
  (`test_damn.db`).
- `tests/integration/test_plan_flow.py` covers the real closed loop (generate →
  execute → low-completion feedback → auto-replan v2 → cooldown 409). Update it when
  changing the plan/feedback/replan flow.

## Mocks — do not overclaim

`app/agent/nodes/*` are deterministic heuristics (no LLM call), `MockLLMClient`
returns canned JSON, `app/ml/*` are `statistical-*` predictors with **no trained
model**, `app/infrastructure/ml/model_store.py` is a placeholder, and plan
generation runs synchronously (events are stored then replayed over SSE).

## Pointers

- **中文模块详解（含调用链与调试清单）：`docs/modules.md`** — start here when
  adding/debugging a module.
- Design docs: `docs/architecture.md`, `docs/api.md`, `docs/langgraph.md`,
  `docs/ml.md`, `docs/domain.md`, `docs/development.md`.
- `ideas and structures/` holds the original Chinese design notes/prompts — reference
  material, not code.
