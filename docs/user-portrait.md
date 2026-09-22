# User Portrait (画像)

A per-user behavioural model made of two halves:

| Half | What | Where it lives |
| --- | --- | --- |
| **Static portrait** | MBTI type, per-dimension weights, free-text identity | `users.mbti_type` / `users.mbti_dims` / `users.identity` |
| **Adaptive state** | 12 numeric fields updated by EWMA as feedback arrives | `user_states` (one row per user) |

> **MBTI is a SOFT self-report input, never a diagnosis.** The template numbers
> are engineering estimates that act as a *cold-start prior*; observed feedback
> (EWMA) takes over as `update_count` grows. Every API response carries
> `degraded = update_count < 3` so the UI can label cold-start numbers honestly.

## Layout

```
app/domain/profile/          pure engine (no I/O, no frameworks)
├── models.py                UserProfileData / UserStateData / estimates
├── mbti_templates.py        16 types + _default (8 keys each, 【工程】 values)
├── engine.py                resolve / init / predict / update / replan
└── __init__.py

app/application/services/profile_service.py   persistence + wiring
app/schemas/profile.py                        ProfileRead / ProfileUpdate
app/infrastructure/database/models/user_state.py
app/infrastructure/database/repositories/user_state_repository.py
tests/unit/test_profile.py                    engine (pure)
tests/api/test_profile_api.py                 HTTP + DB integration
```

The engine is **pure** (`frozen=True, slots=True` dataclasses; `update_state`
returns a new state and never mutates its input), so it is testable with no I/O.

## Formula summary (all coefficients are 【工程】 pending calibration)

| Function | Rule |
| --- | --- |
| `resolve_mbti_type` | explicit type is the base; each `mbti_dims` weight ≥ 0.5 picks the FIRST letter of the pair (`ie` → `I/E`); anything unresolvable → `_default` |
| `init_state` | exact template copy with no dims; otherwise per-dimension blend `w × first-letter-template + (1−w) × second-letter-template`; `preferred_time_slots` always from the majority type; dynamic fields start at 0.5; `update_count = 0` |
| `predict_duration` | `base = theoretical × TYPE_MULTIPLIER[task_type]`; `× duration_factor × (1 + 0.3·(fatigue − 0.5)) × (1 − 0.2·(energy − 0.5))`; `q80 = 1.25·q50` |
| `predict_completion` | cold start → `completion_prob`; otherwise `0.5·prior + 0.5·recent_7d`; clamped `[0.05, 0.98]` |
| `update_state` | EWMA α = 0.3 for `duration_factor` (ratio clamped `[0.5, 3.0]`), `state_energy`, `state_fatigue`, `stress_baseline`; self-efficacy event rule `+0.15·s·(1−SE) − 0.25·(1−s)·SE` |
| `replan_decision` | 5 consecutive days < 0.40 → `full_replan`; last two < 0.60 → `local_repair`; `duration_bias > 0.50` → `local_repair`; else `none` |
| `should_prompt` | `send` iff <3 prompts in 24 h, not in a focus block, fatigue < 0.8 |

### Fixed on merge: minority-weight inversion

The handed-over `init_state` anchored the blend on the **resolved (majority)**
type: `w × resolved + (1−w) × flipped`. That is correct for `w ≥ 0.5` but
inverted below it — `ie = 0.2` (20 % I / 80 % E) produced an **I**-weighted
state. It is now anchored on the letter pair, so `w` always means "pull toward
the first letter" as the `mbti_dims` contract states.
`test_minority_weight_is_not_inverted` guards the regression.

## The feedback loop

```
users.mbti_type/dims/identity ──init_state──► user_states
                                                  │
        feedback (completion/stress/energy) ──────┤ EWMA
        task execution (actual vs planned) ───────┘
                                                  │
                                                  ▼
                        ProfileService.build_user_features ──► UserFeatureSet ──► ML predictors
                        PlanningContext.profile_prompt     ──► plan_draft prompt block
                        PlanningContext.profile_replan     ──► AdjustmentRouter escalation
```

- `FeedbackService.submit_feedback` → `ProfileService.update_from_feedback(...)`
  with `energy_level` / `stress_level` / `completion_rate`.
- `PlanService.update_task(completed=True)` → same, with
  `actual_duration` vs `planned_duration` (after the task commit, so a portrait
  failure can never roll back the user's execution record).
- Both are **best-effort**: a failure is rolled back and never breaks the write
  that matters (`feedbacks` / `task_executions` are the records of truth).

## How the agent consumes it

| Consumer | Field | Effect |
| --- | --- | --- |
| ML predictors | `UserFeatureSet` from `ProfileService.build_user_features` | `duration_factor`, completion rates, stress/energy (0..10 scale), time slots, `sample_size = update_count` |
| `plan_generation` prompt | `PlanningContext.profile_prompt` → `PlanDrafterInput.profile_context` → `{{profile}}` | biases the task mix; explicitly labelled "prior, not a diagnosis" |
| `AdjustmentRouter` | `PlanningContext.profile_replan` → `state["profile_replan"]` | **escalates only** (`full_replan` → FULL_REPLAN, `local_repair` → MICRO_ADJUST when the ML said NO_CHANGE). It can never downgrade the ML or policy route. |

Memory derivation also reads the state: `agent/memory/semantic.py`
(duration factor, preferred slots) and `procedural.py` (completion prior).

## API

| Endpoint | Behaviour |
| --- | --- |
| `GET /users/me/profile` | Static portrait + full adaptive state; **404** when nothing is set |
| `PATCH /users/me` (`mbti_type` / `mbti_dims` / `identity`) | Field omitted → keep; explicit `null` → clear; changing the portrait **re-initialises** the state (`update_count = 0`) |
| `POST /auth/register` (same three fields) | Seeds the state at sign-up |

`mbti_dims` rejects unknown dimension keys (422) and clamps weights to `[0, 1]`.

## Why `user_models` is gone

It overlapped the portrait state (`duration_factor`, `completion_prob`,
`stress_response`, `preferred_time_slots`) with a different shape (per
load-bucket dicts) and had **no caller** — `UserModelService` was dead code.
Two tables claiming to model the same thing is a divergence risk, so
`user_models` and its five files were removed; the portrait state is the single
behavioural model and feeds the predictors directly.

## Tests

```bash
uv run pytest tests/unit/test_profile.py -q      # engine: resolution, blending, EWMA, decisions
uv run pytest tests/api/test_profile_api.py -q   # 404, PATCH semantics, register seeding,
                                                 # feedback/execution -> state, portrait -> predictions
```

## Extending

| Goal | Where |
| --- | --- |
| recalibrate MBTI numbers | `app/domain/profile/mbti_templates.py` (keep the 【工程】 note until real data exists) |
| change a formula | `app/domain/profile/engine.py` + a unit test |
| add a state field | `UserStateData`, the ORM column, `_FIELDS` in the repository, and a migration |
| change how the agent sees it | `ProfileService.build_user_features` / `_profile_variables` in the plan drafter |
| change when we escalate | `AdjustmentRouter.decide` (profile block) |
