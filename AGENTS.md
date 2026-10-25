# AGENTS.md

FastAPI backend for a feedback-driven adaptive task planner: goals → theory
analysis → user-situation (ML) → plan generation (LangGraph) → hard-rule
validation → scheduling → execution feedback → replan.
Python 3.12 · uv · FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · LangGraph.
Single package (`app/`) at the repo root — no monorepo. Windows-first.

## Document authority (read before changing docs or code)

The current human design is the plain-language docs under `docs/`:

- `docs/README.md`, `docs/架构.md`, `docs/需求.md`,
  `docs/决策记录.md`, `docs/三层用户模型.md`, `docs/当前实现.md`,
  `docs/证据现状.md`, `docs/实施指导.md`.

Technical/implementation docs: `docs/技术索引.md`,
`docs/架构总览.md`, `docs/agent/`,
`docs/模型与Agent集成-v1.md`, `docs/前端模型集成-v1.md`,
`docs/开发手册.md`, `docs/模块详解.md`.
Evidence: `docs/research/`.

On conflict: the human docs win; change code to match them. If a decision
genuinely changes, update `docs/决策记录.md` first, then
`docs/架构.md` / `docs/需求.md`.
Agent-only docs: this `AGENTS.md` and `docs/research/AGENTS.md`; they may stay
technical.

## Commands (verified)

- Install: `uv sync --extra dev` (creates `.venv`; requires Python 3.12)
- All tests (opt-in): `uv run pytest` → 229 pre-Phase-1 tests + Phase 1–6 additions; the default loop is targeted runs, see Testing quirks.
- Frontend: `cd new_frontend && npm test` → 19 logic tests · `npm run typecheck` · `npm run lint`
- Web export: `cd new_frontend && npx expo export --platform web`
- One file / one test: `uv run pytest tests/unit/test_rules.py -q` · `uv run pytest -k scheduler -v`
- Lint: `uv run ruff check .` (line length 100, target py312)
- Run API: `uv run uvicorn app.main:app --reload` → http://localhost:8000/docs
- Migrations: `uv run alembic upgrade head` · `uv run alembic revision --autogenerate -m "..."`
- Predictor scoring: `uv run python scripts/evaluate_predictors.py [--user-id N]`
- If a dev tool reports "program not found", install/run with `uv run --extra dev <tool>`.

Use port **8000**. Some Windows ports are OS-reserved and uvicorn fails with
`WinError 10013` (observed on 8123) — not a code bug.

## Architecture rules (easy to violate)

Dependencies flow API → Application → Domain/Core → Infrastructure.
`app/agent` and `app/user_models` are side-cars driven by the Application layer.
`app/user_models` is the only owner of the Level 1/2/3 models and artifacts.

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
- **Level 3 is shadow-only in v1.** `LEVEL3_MODE=off|shadow|active` defaults to
  `shadow`; `active` is parsed but downgraded to shadow. Shadow output is written to
  `shadow_predictions` **after** the plan is committed and must never change task
  fields, the scheduler input or the rule-engine result.
- Agent/Application consume `UserModelContext` (typed Level 1 trait + Level 2 state
  snapshots); they never read model artifacts or raw model dicts.
- **Level 1 CAT assessment is resumable server-side.** `trait_assessments` stores
  only ordered responses + `rr_index` + artifact identity; `Level1Runtime`
  replays them. `POST /users/me/trait-assessment/start` is idempotent (resume),
  `?restart=true` abandons the active session, and completion writes
  `users.trait_profile`. CAT maths live only in `level1/cat.py`.
- **Auth is normal JWT; demo auto-login is not a bypass.** The frontend only
  auto-calls `/auth/login` when both `EXPO_PUBLIC_DEMO_EMAIL` and
  `EXPO_PUBLIC_DEMO_PASSWORD` are configured. `trait_profile == null` forces
  `/assessment`; reassessment cooldown is backend-authoritative
  (`TRAIT_REASSESSMENT_COOLDOWN_DAYS`).
- **Synthetic scenarios are observations, never model outputs.** The dev-only
  import (`ENABLE_SYNTHETIC_IMPORT=false` by default) writes tasks/executions/
  feedback with `data_origin='synthetic'`; Level 2/3 are computed by the real
  runtime. Reset deletes only the current user's synthetic rows.

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

- **Incremental-first (2026-10-25):** do NOT run the whole suite on every change.
  Run only the affected test files; a full run is opt-in. When a full run is
  needed, first delete/merge tests whose coverage is already provided elsewhere
  or whose asserted behaviour is gone — keep the suite meaningful, not big.
- `tests/conftest.py` sets `DATABASE_URL` / `JWT_SECRET_KEY` **before** importing
  `app`, then clears the settings cache. Preserve that import order in new tests.
  Its `setdefault` means a per-run `DATABASE_URL` env var gives each run its own
  SQLite file (useful when tests run concurrently).
- Fixtures: `client` (TestClient, runs lifespan), `registered_user`, `auth_headers`
  (Bearer JWT). Schema is created/dropped per session against a file DB
  (`test_damn.db`).
- `tests/integration/test_plan_flow.py` covers the real closed loop (generate →
  execute → low-completion feedback → auto-replan v2 → cooldown 409). Update it when
  changing the plan/feedback/replan flow.

## Mocks — do not overclaim

`app/agent/nodes/*` are deterministic heuristics (no LLM call). `app/user_models/**`
contains the **real** copied model code and artifacts (Level 1 GRM/CAT, Level 2
DDSR-V1, Level 3 predictor); `models_test/` is the frozen source package and is not
imported at runtime. `MockLLMClient` returns canned JSON; no production model
emits a completion probability (Level 3 runs in shadow only). Plan generation runs
synchronously (events are stored then replayed over SSE).

## Pointers

- **中文模块详解（含调用链与调试清单）：`docs/模块详解.md`** — start here when
  adding/debugging a module.
- **Frontend contract: `docs/前后端接口对齐.md`** — the endpoint map,
  the decisions behind it, and what was deliberately left unchanged.
- **Model/Agent integration: `docs/模型与Agent集成-v1.md`** — the final
  three-layer runtime, shadow mode, workflow refactor, migration and validation.
- **Frontend integration: `docs/前端模型集成-v1.md`** — the
  frontend/backend contract audit, CAT assessment UI/API, Profile Level 1/2,
  task execution capture, developer runtime page.
- **Auth/Demo/Synthetic: `docs/认证与合成数据-v1.md`** — Login/Register/
  Logout, Level 1 onboarding guard, reassessment cooldown, IDOR tests, execution
  provenance, and guarded synthetic scenario import/reset.
- **User portrait (画像): `docs/用户画像.md`** — historical portrait reference;
  MBTI columns were removed on 2026-10-25 (`remove_legacy_mbti_20261025`), the
  live portrait is Level 1 CAT traits + Level 2 daily state (`docs/三层用户模型.md`).
- **Agent layer (P0+P1): `docs/agent/`** — state-machine, data-flow, prompts,
  tools, ml-interface, memory, testing, development.
- Human docs: `docs/README.md`, `docs/架构.md`, `docs/需求.md`,
  `docs/决策记录.md`, `docs/三层用户模型.md`, `docs/当前实现.md`,
  `docs/证据现状.md`, `docs/实施指导.md`.
- Technical index: `docs/技术索引.md`; implementation details in
  `docs/架构总览.md`, `docs/开发手册.md`,
  `docs/模块详解.md`, `docs/agent/`.
- Schema history: `docs/database/数据库迁移.md` (`7f9ae3f96ba3` added
  `agent_runs`/`prediction_logs`/`agent_memories`; `d696086158be` added
  `users.scheduling_preferences`; `4d1dc7a359da` added the portrait columns +
  `user_states` and dropped `user_models`; `remove_legacy_mbti_20261025`/
  `persist_generation_jobs_20261025` came with the upstream merge; phase 1 added
  the six record-layer tables/columns; `49623649564a` added `daily_plans` +
  `unscheduled_tasks`). Current head: `49623649564a`.
- `ideas and structures/` holds the original Chinese design notes/prompts — reference
  material, not code.
