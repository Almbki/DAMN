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

## Frontend (`frontend/`)

Expo SDK 57 · RN 0.86 · expo-router · react-native-web. One frontend only. The data layer
supports two sources selected by `EXPO_PUBLIC_DATA_SOURCE` (`mock` | `api`) — see the
wiring section below. Imports use the `@/*` alias → `frontend/src/*`.

```
src/api/        client / config / endpoints / mapper / types / format   HTTP + wire types
src/state/      plan provider (mock|api switch), session, theme, plan-context
src/domain/     task, task-ops (pure), selectors, quick-add, stats, insight, date
src/components/ shell + ui primitives + page-level pieces
src/app/        routes: index (Todo), profile, feedback, settings
src/constants/  tokens (colour / type / spacing), nav
```

Identity: paper + hairlines, black/white/grey with a **single** accent (mint) reserved for
"now"; time numerals in IBM Plex Mono, CJK on the system stack. Review visuals by pixels,
not by reading the DOM.

### Looking at the page (the human runs Expo; the agent does not)

**The agent must not launch Expo or any long-running background process.** Ask for the port
the human already has open (Expo web default `8081`) and screenshot against it with system
Edge headless:

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless --disable-gpu `
  --window-size=1440,1000 --screenshot=out.png "http://localhost:8081/?theme=light"
```

- Theme via the app's own URL override: `?theme=light` / `?theme=dark` / `?theme=system`.
  Do **not** rely on `--force-dark-mode` — it does not change `prefers-color-scheme`.
- To catch overflow, drive CDP in the same session and read `document.scrollWidth` plus each
  element's `getBoundingClientRect`; a screenshot alone can show phantom clipping. Write a
  small throwaway Node CDP script (Node 24 has `WebSocket` built in) — there is **no**
  committed screenshot tool in the repo.
- Verify at **390 / 768 / 1440** in **both** schemes before claiming a visual change works.
- `npx expo export --platform web` is a **smoke test only** — it renders the SSR frame (the
  narrow branch) and does not hydrate under `file://` (ES-module CORS). Content/errors only.
- Under a confined sandbox Chromium may die with `FATAL:mojo platform_channel ... 0x5`
  (exit `0x80000003`) and produce no image — a sandbox limit, not a flag problem.

### react-native-web traps (still true)

- **CJK overflows its container.** RNW renders every `<Text>` with `white-space: pre-wrap`
  and CJK does not break per character. Fixed globally in `frontend/src/global.css`
  (`white-space: normal !important` — required because RNW writes the value inline).
- **`flexWrap` is unreliable** (a `row` + `wrap` container can compute back as
  `column` + `nowrap`). Split rows explicitly and compute columns from
  `useWindowDimensions()` (see `SmartListTabs`, `Segmented`).
- **RNW renders `accessibilityRole="button"` as a real `<button>`** — never nest a pressable
  inside another pressable; use sibling buttons or you emit invalid HTML.

### Never silence a native-boundary type error with a cast

**`tsc` passing proves nothing about native calls.** A wrong value at a native boundary
compiles clean and then hard-crashes the device:

```ts
// WRONG — compiled fine, red-screened on every phone
Appearance.setColorScheme(mode === 'system' ? null : mode as ColorSchemeName);
```

Rules:

- **Never write `as SomeType`, `as any`, `@ts-ignore` or `@ts-expect-error` to get past a
  native-module signature.** If the compiler rejects the value, the value is wrong — read the
  native source and use what it takes. The "system" value for `Appearance.setColorScheme` is
  the string `'unspecified'`, not `null`/`undefined`.
- **`tsc` cannot see this class of bug**, so native-affecting changes (Appearance,
  notifications, splash, system UI, permissions) need a real device/emulator run before being
  called done — a browser screenshot is not sufficient evidence.

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

## Frontend ↔ backend wiring (`frontend/`)

Config lives in `frontend/.env` (gitignored; `EXPO_PUBLIC_*` is inlined at build time →
restart with `--clear`):

- `EXPO_PUBLIC_API_BASE_URL` — backend origin, e.g. `http://192.168.9.67:8000` (LAN machine).
- `EXPO_PUBLIC_DATA_SOURCE` — `mock` (no backend) or `api`.
- `EXPO_PUBLIC_DEV_EMAIL` / `EXPO_PUBLIC_DEV_PASSWORD` — silent dev login (register → 409 → login).

Layers: `src/app/*` → `src/state/*` (providers) → `src/api/*`; pages never call `fetch`.
`src/domain/*` is pure (task model, recurrence, quick-add parser, stats, insight builder).

In `api` mode the backend cannot create/edit/delete/reorder tasks, so those UI actions are
disabled; the add-bar becomes "goal → `POST /plans/generate`".

Behaviours that are **measured against the live backend** (not read from `docs/api.md`,
which drifts from `/openapi.json`):

- `/health` is at the **root**, not under `/api/v1`; the API prefix is `/api/v1`.
- `POST /plans/generate` is **synchronous** (`status:"completed"`, `plan` inline) → no SSE;
  never fake the six-stage progress.
- `PATCH {completed:false}` does **not** un-complete a task; un-complete via
  `{status:'scheduled'}`. Skip is `{status:'skipped'}`; focus time is `{actual_duration}`.
- Feedback with `completion_rate < 0.5` **creates a new plan version** → switch to
  `replan_plan_id` (the new plan may legitimately have zero tasks). Replan cooldown is
  per-user (24 h, 409 `replan_not_eligible`); the 409 body carries `next_eligible_at`.
- `"YYYY-MM-DD"` parses as UTC midnight and `"HH:MM:SS"` is not a Date — use `src/api/format.ts`.
- Generating a new plan marks the previous `active` plan `superseded`; only one is active.
- **`PlanRead.goals` is mis-mapped server-side** (titles come from the account's oldest
  goals) → do **not** render `plan.goals`. `TaskRead.goal_id` is still trustworthy.
- The LAN backend can stall (measured 18.3 s once) → the request timeout is 30 s on purpose.

## Pointers

- Design docs: `docs/architecture.md`, `docs/api.md`, `docs/langgraph.md`,
  `docs/ml.md`, `docs/domain.md`, `docs/development.md`.
- `docs/design/` holds the original Chinese design notes, mind map and prompts
  (`docs/design/notes/`) — reference material, not code.
