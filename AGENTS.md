# AGENTS.md

FastAPI backend for a feedback-driven adaptive task planner: goals → theory
analysis → user-situation (ML) → plan generation (LangGraph) → hard-rule
validation → scheduling → execution feedback → replan.
Python 3.12 · uv · FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · LangGraph.
Single package (`app/`) at the repo root — no monorepo. Windows-first.

## Citation rules

- Any file reference in discussion, review, or generated docs must give the
  **full path**, plus a line number when a specific line is meant.
- Bare filenames are ambiguous in this repo: write `app/agent/graph.py:364`,
  never `graph.py:364`.
- Document shorthand must be expanded to its full path on first use:
  `docs/research/RO-5-RuleEngine与决策架构.md`, not "RO-5".

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

## Frontend: how to actually LOOK at the page (read before styling)

The Expo app lives in `damn-app/` (Expo SDK 57 · RN 0.86 · expo-router · react-native-web).
Styling decisions here are about **layering and texture**, so reading the DOM is not
enough — look at pixels. Use the system Edge, no install needed:

```powershell
# PREREQUISITE: the human is already running `npx expo start` — see "Do NOT start a dev
# server" below. Nothing here may launch Expo or any long-running process.

# one shot
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless --disable-gpu `
  --window-size=1440,1000 --screenshot=out.png http://localhost:8099/workbench

# light / dark: use the app's own URL override (preferred — it also exercises the toggle)
#   ?theme=light   ?theme=dark   ?theme=system
# Browser-flag fallback, historically unreliable here: --blink-settings=preferredColorScheme=1|0

# measure real layout + full-page shot, same session (zero deps, drives CDP)
node .shots/measure.js <url> <width> <height> [out.png] [1=light 0=dark]
node .shots/shot.js    <url> <width> <height> <anchorText> <out.png>   # scroll to a section + print console errors
```

Pitfalls that cost real time — do not rediscover them:

- **Chromium needs named pipes for IPC.** Under a confined sandbox it dies with
  `FATAL:mojo platform_channel Check failed: 拒绝访问 (0x5)` and exit `0x80000003`,
  producing no image. It is a sandbox limit, **not a flag problem** — do not burn time
  on `--no-sandbox` / `--headless=old` / CDP ports. Run with file access relaxed.
- **`--force-dark-mode` does NOT change `prefers-color-scheme`.** Two "light/dark"
  shots come out byte-identical. `--blink-settings=preferredColorScheme=` works, but
  prefer the app's `?theme=` override (it also exercises the real toggle path).
- **A screenshot alone can lie about overflow.** Measure `document.scrollWidth` and
  each element's `getBoundingClientRect` in the same session — a capture whose device
  width does not match the layout viewport shows phantom "clipped" content.
- **Restart the dev server (`--clear`) after editing `global.css` or adding files.**
  HMR did not pick them up in headless sessions; the page kept rendering the old bundle.
- **Metro HMR is not wired to the headless browser.** Re-navigate (the script does) or
  restart; otherwise you are reviewing stale output.

Two react-native-web traps found this way — see `damn-app/src/constants/tokens.ts` and
`components/controls.tsx`:

- **Chinese text overflows its container.** RNW renders every `<Text>` with
  `white-space: pre-wrap`, and **CJK does not break per character under `pre-wrap`**.
  Fixed globally in `damn-app/src/global.css` (`white-space: normal !important` —
  `!important` is required because RNW writes it inline).
- **`flexWrap` is unreliable.** A container given `flexDirection:'row'` +
  `flexWrap:'wrap'` computed back as `column` + `nowrap`, stacking every child at one
  coordinate. Do not build wrapping layouts on it: split rows explicitly and compute
  columns from `useWindowDimensions()` (see `CardGrid` in `components/controls.tsx`).

Verification loop that actually catches things: screenshot **and** measure at
390 / 768 / 1440 wide, in **both** schemes, before claiming a visual change works.

### Do NOT start a dev server — the human runs Expo

**The agent must not launch Expo or any long-running background process.** The human
owns the dev server. To review the UI:

1. Ask for / use the port the human already has open (default `8099`), and point the
   screenshot scripts at it.
2. For theme switching, use the **URL override** — `?theme=light` / `?theme=dark` —
   instead of browser flags. Browser color-scheme flags were measured to be unreliable
   here (two "light/dark" captures came out byte-identical), and the override also
   tests the real toggle path.
3. If nothing is running, a **static export is a smoke test only**:
   `npx expo export --platform web --output-dir .shots/preview`. It renders the SSR
   frame only — desktop layout and theme **cannot** be evaluated from it, because
   `useIsWide()` forces the narrow branch during SSR and the JS bundle does not
   hydrate under `file://` (ES-module CORS). Use it to check content presence and
   server-side errors, nothing more.
4. Never write to `damn-app/dist` — that may be what the human packages with Tauri.

### Never silence a native-boundary type error with a cast

**`tsc` passing proves nothing about native calls.** A wrong value at a native boundary
compiles clean and then hard-crashes the device. This already happened once and bricked
the Android app on launch:

```ts
// WRONG — compiled fine, red-screened on every phone
Appearance.setColorScheme(mode === 'system' ? null : mode as ColorSchemeName);
//  Parameter specified as non-null is null: method
//  com.facebook.react.modules.appearance.AppearanceModule.setColorScheme, parameter style
```

Rules:

- **Never write `as SomeType`, `as any`, `@ts-ignore` or `@ts-expect-error` to get past a
  native-module signature.** If the compiler rejects the value, the value is wrong —
  read the native source (RN sources are fetchable from
  `raw.githubusercontent.com/facebook/react-native/v<version>/...`) and use what it takes.
- In that case the answer was in our own `node_modules` the whole time:
  `type ColorSchemeName = 'light' | 'dark' | 'unspecified'`. The "system" value for
  `Appearance.setColorScheme` is the **string `'unspecified'`**, not `null`/`undefined`
  (both marshall to `null` and throw).
- **`tsc` cannot see this class of bug.** So native-affecting changes need a real device
  or emulator run before being called done — a browser screenshot is not sufficient
  evidence. Check that the app still *launches* after touching anything that reaches a
  native module (Appearance, notifications, splash, system UI, permissions).

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

## Frontend ↔ backend wiring (verified against the live LAN backend)

The Expo app talks to the FastAPI backend over `EXPO_PUBLIC_API_BASE_URL`
(`damn-app/.env`, build-time inlined → restart with `--clear`). Layers:
`src/app/*` → `src/plan` + `src/session` → `src/api`; pages never call `fetch` directly.
`_layout.tsx` gates on the session — signed out renders `components/auth-screen.tsx`
instead of `Slot`.

Behaviours that are **measured, not read from `docs/api.md`** (that file drifts from
`/openapi.json`):

- `/health` is at the **root**, not under `/api/v1`.
- `POST /plans/generate` is **synchronous** (~1.5 s, `status:"completed"`, `plan` inline)
  → no SSE needed; never fake the six-stage progress.
- `PATCH {completed:false}` does **not** un-complete a task (and yields `pending`
  otherwise); uncheck via `{status:'scheduled'}`.
- Feedback with `completion_rate < 0.5` **creates a new plan version** — the UI must
  switch to `replan_plan_id`. Replan keeps only unfinished tasks, so the new plan can
  legitimately have zero tasks.
- Replan cooldown is per-user (24 h, 409 `replan_not_eligible`); the 409 body's `detail`
  carries `next_eligible_at`.
- `"YYYY-MM-DD"` parses as UTC midnight and `"HH:MM:SS"` is not a Date — use
  `src/api/format.ts`.
- Generating a new plan marks the previous `active` plan `superseded` (versions keep
  counting up); only one plan is `active` at a time.
- **`PlanRead.goals` is mis-mapped server-side**: the count matches the plan but the
  titles come from the account's oldest N goals (verified: plan #5's own goal is
  "finish the half marathon plan" yet `goals` reports goal#1 "gaoshu limits review").
  No page renders `plan.goals` yet — do **not** wire the "属于「目标」" line until the
  backend join is fixed. `TaskRead.goal_id` is still trustworthy.
- The LAN backend can stall (measured 18.3 s for `/health` while unauthenticated calls
  answered in 0.36 s) → `REQUEST_TIMEOUT_MS` is 30 s on purpose; do not lower it.

UI verification (needs Edge headless → whole script at relaxed file access; Chromium's
IPC is denied under the confined sandbox with `FATAL:mojo platform_channel ... 0x5`):
`.shots/capture-all.ps1` (9 viewports/schemes, injects a JWT into localStorage),
`.shots/interact.ps1` and `.shots/interact-generate.ps1` (real clicks; judge them by the
**server state** they print, not the console text — PS 5.1 mangles non-ASCII argv).

Re-run the probes: `.shots/smoke-api.ps1`, `.shots/smoke-api-flows.ps1`
(ASCII-only; PS 5.1 reads BOM-less `.ps1` as ANSI). Full write-up:
`docs/frontend-api-integration.md`.

## Pointers

- Design docs: `docs/architecture.md`, `docs/api.md`, `docs/langgraph.md`,
  `docs/ml.md`, `docs/domain.md`, `docs/development.md`.
- `ideas and structures/` holds the original Chinese design notes/prompts — reference
  material, not code.
