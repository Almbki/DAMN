# Authentication · Onboarding · Demo · Synthetic Scenarios (V1.1)

> Scope: turn the developer-runnable closed loop into a usable V1.1:
> login/register/logout, forced Level 1 onboarding, multi-user isolation,
> execution-data integrity, demo auto-login, and guarded synthetic scenario
> import.
>
> Code is the source of truth. Statuses: **implemented**, **tested**,
> **not enough runtime data**, **future work**.

---

## 1. Authentication

### Backend (unchanged contract, tested)

The existing JWT API is reused; no second auth system was introduced.

```text
POST /api/v1/auth/register   -> UserRead (201; 409 if email exists)
POST /api/v1/auth/login      -> { access_token, token_type, expires_in }
GET  /api/v1/users/me        -> UserRead (Bearer JWT)
```

* Password hashing remains PBKDF2; JWT remains stateless with a 7-day default.
* No refresh token exists; an expired token produces 401 and the client returns
  to Login.
* Logout is client-side only (stateless JWT): the token is removed and all
  user-scoped providers are unmounted. There is no server token-revocation list.

### Frontend (implemented + tested at logic level)

New screens:

* `/login` — email + password; loading, invalid credentials, conflict/network
  errors; link to Register.
* `/register` — email + password + optional display name; normal backend
  registration followed by a normal login; link to Login.
* Settings → **退出登录**.

Session model in `new_frontend/src/state/session.tsx`:

```text
booting
  -> stored valid token? -> authenticated
  -> invalid token + demo credentials? -> normal POST /auth/login
  -> otherwise -> unauthenticated (Login/Register)

authenticated <-> logout -> unauthenticated
network failure -> error (Retry)
```

The token is stored in `localStorage` on Web; on native it is in-memory only
(see Remaining risks). `SessionProvider` is now mounted above the router; the
Plan/Profile/Schedule providers only mount for authenticated users, so logout
unmounts all user-specific state instead of leaving a stale cache.

---

## 2. Onboarding (Level 1 is mandatory)

`UserRead.trait_profile` is the onboarding signal.

Central state machine (`src/domain/auth.ts::resolveGuardState`):

```text
booting / error / unauthenticated / onboarding / ready
```

Rules:

* Unauthenticated → `/login` (or `/register`).
* Authenticated + `trait_profile == null` → `/assessment`.
* Authenticated + trait present → Main App.
* Login/Register while authenticated → `/`.
* Mock mode never enforces backend onboarding (it has no backend user).

After CAT completion the assessment screen:
1. refreshes `GET /users/me` and updates the session user (releases the guard);
2. refreshes the Profile provider (Level 1 becomes visible);
3. shows the completion summary.

### Reassessment

Profile keeps “重新测评”:

1. `GET /users/me/trait-assessment/reassessment-eligibility` checks the backend
   cooldown.
2. If not eligible, Profile shows the next eligible date (no dialog).
3. If eligible, a confirmation dialog explains that the new profile will replace
   the current active snapshot; old assessment rows are kept.
4. Confirming calls the existing
   `POST /users/me/trait-assessment/start?restart=true`, then opens
   `/assessment`.

`TRAIT_REASSESSMENT_COOLDOWN_DAYS` (default **30**, `0` disables) lives in
`app/core/config.py` and is enforced by the backend. It is not duplicated as a
frontend-only rule.

History: `trait_assessments` is append-only for audits;
`users.trait_profile` remains the current active snapshot.

---

## 3. Demo Mode

Frontend configuration:

```env
EXPO_PUBLIC_DEMO_EMAIL=
EXPO_PUBLIC_DEMO_PASSWORD=
```

* Both non-empty → demo auto-login enabled.
* Either empty → normal Login/Register.
* Auto-login calls the **normal** `/auth/login` endpoint, stores a normal JWT,
  and then uses the same auth dependency/ownership checks as any user.
* There is no fabricated JWT, no direct `user_id`, and no auth bypass.
* Demo credentials are public in an Expo Web bundle. Use a dedicated test
  account with no privileged/real-user data. `.env.example` documents this.

Demo Login and Synthetic Import are independent features: configuring demo
credentials does not enable synthetic import.

---

## 4. Execution data integrity

### `started_at` read model

`TaskRead` now includes `started_at` sourced from the **active**
`TaskExecution` (started, not completed, not finished). `PlanService.get_plan`
joins the user's executions and sets the field on the read model; completed or
skipped tasks expose `null`.

* survives a refresh / API re-fetch;
* clears once the task is completed;
* no execution entity is leaked through the API.

### Interruptions: null ≠ 0

* `task_executions.interruption_count` is nullable.
* `TaskUpdateRequest.interruption_count` is optional.
* Task UI: “中断次数（可选）”; blank = not observed, explicit `0` = observed
  zero, `3` = three.
* Level 2 adapter passes `None` through; DDSR metrics sum only observed values.
  Missing observations do **not** contribute interruption evidence.
* Tests prove `None`, `0`, and `3` remain semantically distinct.

---

## 5. Synthetic scenarios

### Purpose and safety

Synthetic scenarios are **demo/test observations only**. They are not real-user
evidence and must not be used for real accuracy/calibration claims.

Feature flag:

```env
ENABLE_SYNTHETIC_IMPORT=false
```

Disabled by default → endpoints return 404 and the Developer UI hides the
section. When enabled, all endpoints require authentication and always target
`current_user.id`; the request schema forbids extra `user_id` fields.

### API

```text
GET  /api/v1/dev/scenarios
GET  /api/v1/dev/scenarios/status
POST /api/v1/dev/scenarios/import   { scenario_name } OR { scenario }
POST /api/v1/dev/scenarios/reset
```

### Scenario format (version 1.0)

`SyntheticScenario` contains:

* `name`, `description`, `scenario_version`
* optional `level1`:
  * ordered CAT `responses` (replayed by the real `Level1Runtime`), or
  * a validated `trait_profile`
* `days[]`, each with task observations and optional feedback:
  * title, estimated/actual duration, completion rate, completed,
    interruption_count, difficulty, planned_start/actual_start
  * feedback completion/stress/energy/free_text/sleep

No level 2/3 outputs are accepted. Fatigue/stress/self-efficacy/completion
probability cannot be supplied by the caller.

### Real model chain

```text
synthetic observations
  -> synthetic Plan/Task/TaskExecution/Feedback (data_origin=synthetic)
  -> real UserModelService.refresh_dynamic_state()  (Level 2 DDSR-V1)
  -> real UserModelService.run_shadow_for_plan()     (Level 3 shadow)
  -> shadow_predictions (data_origin=synthetic)
```

The import service calls the existing `UserModelService` / `UserModelRuntime` /
`Level3ShadowRunner`. It does not copy model code or write model output tables
directly.

### Provenance

`data_origin` (`real` | `synthetic`) is persisted on:

* `plans`, `tasks`, `task_executions`, `feedbacks`
* `prediction_logs`, `shadow_predictions`
* `trait_assessments`

A real plan replayed from a synthetic parent inherits `synthetic` provenance,
so reset can remove the whole demo lineage.

`scripts/evaluate_predictors.py` defaults to **real data only**; synthetic rows
require `--include-synthetic` and must not be reported as real accuracy.

### Reset

`POST /dev/scenarios/reset` deletes only the current user's
`data_origin='synthetic'` rows:

* tasks/standards/executions/feedback/plans/prediction logs/shadow rows/
  replan events/synthetic trait assessments;
* real observations and all other users are untouched;
* if a real imported trait existed before the synthetic import, a real snapshot
  is preserved and restored; a synthetic-only Level 1 is cleared and onboarding
  becomes required again;
* Level 2 is deleted and recomputed from remaining real observations, if any.

### Fixtures

`fixtures/scenarios/`:

* `stable_executor.json`
* `deadline_stress.json`
* `procrastination.json`
* `overload.json`
* `recovery.json`

They contain chronological observations only; no expected model outputs.

### Developer UI

`/developer` (API mode) shows the scenario list, import buttons, synthetic
status/counts, import summary (Level 1/2 status, shadow runs before/after,
warnings), and a synthetic reset action. The section is hidden when the backend
feature is disabled.
The App Shell shows a low-distraction `DEMO` badge when public demo auto-login is
configured.

---

## 6. Multi-user isolation / IDOR

`tests/api/test_idor.py` creates Alice and Bob with real JWTs and verifies Bob
cannot read/patch/delete Alice's:

* plan, task, feedback, plan changes, insights
* replan eligibility / replan
* goal
* trait assessment
* schedule event

Current status policy:

* plan/task/feedback/goal/replan → **403** (`PermissionDeniedError`);
* trait assessment and schedule event → **404** (avoid confirming existence);
* Bob's plan list never contains Alice's plan.

IDs are never accepted as a target user in the synthetic import API.

---

## 7. Validation (actual results)

| Gate | Result |
| --- | --- |
| `uv run pytest` | **229 passed** |
| `uv run ruff check .` | **All checks passed** |
| `alembic upgrade head` / `downgrade -1` / `upgrade head` | pass (`adde00b2004f`) |
| `npm run typecheck` | pass |
| `npm run lint` | pass |
| `npm test` | **19 passed** (4 files) |
| `npx expo export --platform web` | pass (`new_frontend/dist`) |

New backend tests include:

* auth/assessment start/resume/finish/invalid/cross-user/503;
* reassessment cooldown (409, next eligible, configurable 0);
* synthetic import/reset/feature flag/no target user/real Level 2/3/provenance/
  invalid scenario/real data survival/repeat import/other-user isolation;
* IDOR matrix;
* `started_at` survives GET and clears on completion;
* interruption null vs 0 vs 3 in API and DDSR adapter;
* existing closed-loop smoke (`test_user_model_loop.py`).

Frontend logic tests cover:

* route-guard state machine (booting/unauthenticated/onboarding/ready/mock);
* demo credentials enablement and auth error mapping;
* email/password validation;
* null-safe completion probability, prediction provenance, `started_at`;
* execution patch null/zero/three interruption semantics;
* trait presentation and trend null preservation.

---

## 8. Smoke paths

**A. Normal user (API-level, automated):** `test_user_model_loop.py` passes:
new user has `trait_profile=null` → complete CAT → trait stored → generate plan
→ start task → partial execution → feedback → Level 2 state → manual replan →
Level 3 shadow rows → model runtime reports shadow runs.

**B. Multi-user (API-level, automated):** `test_idor.py` passes (see §6).

**C. Demo:** demo auto-login path is implemented using the normal login
endpoint; enablement/disablement and guard behavior are covered by pure frontend
tests. **Interactive browser click-through was not executed.**

**D. Synthetic:** `test_synthetic_scenarios.py` passes: reset → import overload/
stable/recovery → observations persisted with `data_origin=synthetic` → real
Level 2 state → real shadow rows → reset only synthetic → real data survives →
other users unaffected.

Interactive UI/browser smoke remains a manual follow-up. No screenshots or
manual results are claimed.

---

## 9. Remaining risks / future work

1. **No browser/component automation** for Login, Register, onboarding guard,
   Profile reassessment dialog, or Developer scenario buttons. Pure logic tests,
   typecheck/lint and the web export pass, but a human click-through is still
   required.
2. **Native session restore is not persistent.** Web uses `localStorage`; native
   keeps the JWT in memory only, so a native app restart returns to Login.
   `expo-secure-store` (async storage) would be the next step.
3. **JWT is stateless** (no refresh token/revocation list). Logout is client-side
   only; an already-issued token remains valid until expiry.
4. **IDOR status codes are not fully uniform** (403 for owned resources, 404 for
   assessment/schedule). Tests pin the current policy; unifying it is a separate
   API decision.
5. **Synthetic import is a demo/test tool.** It creates an observation plan
   directly (not via PlannerRuntime) and invokes the real Level 2/3 services for
   state/shadow. Do not use it as real-user history.
6. **Synthetic reset + imported Level 1:** a real imported trait snapshot is
   preserved, but a synthetic-only Level 1 is cleared and onboarding returns.
7. **Interruptions are only captured at completion/partial completion**, not as
   live events; blank remains `null` (not zero).
8. **`started_at` read model** scans the user's executions on each plan read
   (`limit=2000`). Fine for V1.1, but a dedicated active-execution query/index is
   preferable at scale.
9. **Demo credentials are public** when bundled into Web. Use a dedicated,
   non-privileged account and leave both variables blank in production.
10. **Synthetic analytics are excluded by default** in
    `evaluate_predictors.py`; never report synthetic metrics as real accuracy.