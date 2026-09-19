# Architecture

## 1. Layering

```
Frontend (React Native / Web)
        │  HTTP + SSE
        ▼
┌───────────────────────────────────────────────┐
│ API / Presentation     app/api, app/schemas   │  routing, auth deps, validation,
└───────────────────────────────────────────────┘  HTTP status mapping, OpenAPI
        │
        ▼
┌───────────────────────────────────────────────┐
│ Application / Service  app/application        │  orchestration, transactions,
└───────────────────────────────────────────────┘  permissions, DTOs
        │                         │
        │                         ├──────────────► app/agent  (LangGraph orchestration)
        │                         └──────────────► app/ml     (predictor protocols)
        ▼
┌───────────────────────────────────────────────┐
│ Domain / Core          app/domain, app/core   │  entities, rules, scheduler,
└───────────────────────────────────────────────┘  config, security, logging
        │
        ▼
┌───────────────────────────────────────────────┐
│ Infrastructure         app/infrastructure     │  SQLAlchemy, repositories,
└───────────────────────────────────────────────┘  LLM client, model store
```

`app/agent` and `app/ml` are **side-cars used only by the Application layer**.
They are not below Domain — they are consumers/collaborators of Domain types.

## 2. Dependency rules (enforced by convention, checked by review)

| Rule | Meaning |
| --- | --- |
| `app/core` and `app/domain` never import FastAPI or SQLAlchemy | Domain is portable and unit-testable with zero I/O |
| Agents never touch the database | `PlanService` builds a `UserFeatureSet` and injects it into `PlannerState` |
| The Rule Engine is the only authority on hard constraints | LLM/agent output produces a *candidate*; `RuleEngine` accepts or rejects |
| Repositories never commit | Services own transaction boundaries |
| The API layer never exposes ORM or domain objects directly | `app/schemas` are the wire contract |
| Predictors are Protocols | Concrete models are injected, never imported by services |

## 3. Layer responsibilities

### API / Presentation — `app/api`, `app/schemas`

- `app/api/deps.py` — `get_db` (session lifecycle), service providers, `get_current_user` (Bearer JWT), and the process-wide `GenerationService` registry.
- `app/api/v1/*.py` — one module per resource: `auth`, `users`, `plans`, `feedback`, `tasks`, `insights`.
- `app/api/v1/mappers.py` — domain → response schema mapping.
- `app/schemas/*.py` — Pydantic v2 request/response models with `examples`, `summary`, `description`, explicit status codes and error models.
- `app/main.py` — app factory, lifespan, CORS, global `ApplicationError` handler, `/health`, OpenAPI at `/docs` + `/redoc`.

The API layer contains **no business logic**: it validates input, calls a service and maps the result.

### Application / Service — `app/application`

| Service | Responsibility |
| --- | --- |
| `AuthService` | register, authenticate, JWT issuance, profile update |
| `PlanService` | persist goals, run the agent graph, persist plan version + tasks + standards, task updates, execution recording |
| `FeedbackService` | daily check-in, auto-replan trigger when completion < 0.5 and eligible |
| `ReplanService` | eligibility (user-level cooldown), versioned replanning, `ReplanEvent` |
| `UserModelService` | derive `UserModel` + `UserFeatureSet` from history |
| `GenerationService` | generation jobs + SSE event replay |
| `InsightService` | read-only analytics over executions/feedback |

Exceptions are framework-free (`app/application/exceptions.py`): each carries a `code` and `http_status`, which `main.py` maps to `ErrorResponse`.

### Domain / Core — `app/domain`, `app/core`

- `app/domain/models/` — Pydantic entities (`from_attributes=True`) + enums.
- `app/domain/rules/` — `Rule` ABC, `RuleEngine`, `RuleViolation`, `RuleContext` and 7 hard constraints.
- `app/domain/scheduling/` — `CandidateSchedule`/`ScheduledTask` value objects and the heuristic `Scheduler`.
- `app/core/` — `Settings`, PBKDF2 + JWT security primitives, logging.

### Infrastructure — `app/infrastructure`

- `database/session.py` — engine, `SessionLocal`, `session_scope`, `init_db`.
- `database/models/` — 9 SQLAlchemy 2.0 typed ORM models.
- `database/repositories/` — one repository per entity; converts ORM ↔ domain, `flush` only.
- `llm/client.py` — `LLMClient` Protocol, `MockLLMClient`, `HttpLLMClient` (OpenAI-compatible).
- `ml/model_store.py` — `ModelStore` Protocol + in-memory/file implementations (PLACEHOLDER: no trained models yet).

## 4. The five responsibilities

```
理论模型 + 用户行为模型 + 硬约束 + 任务调度 + 反馈闭环
```

| Component | Question it answers | Code |
| --- | --- | --- |
| Theoretical Analysis Agent | How much work does this *normally* need? | `app/agent/nodes/theoretical_analysis.py` |
| User Situation Analysis Agent | How much does *this user* actually need? | `app/agent/nodes/user_situation_analysis.py` |
| ML User Model | How does that gap shrink with history? | `app/ml/`, `UserModelService` |
| Scheduler | How do predictions become a calendar? | `app/domain/scheduling/scheduler.py` |
| Rule Engine | Is the plan hard-constraint safe? | `app/domain/rules/` |
| LangGraph | How is the complex flow orchestrated? | `app/agent/graph.py` |

## 5. Request lifecycle: `POST /api/v1/plans/generate`

```
1. API          validate PlanGenerateRequest, resolve current_user
2. deps         provide PlanService (Session) + GenerationService (registry)
3. PlanService  persist Goal rows -> build goal_id_map {index+1: goal_id}
4. UserModelSvc load executions/feedback/model -> UserFeatureSet
5. PlannerGraph run: goal_analysis -> theoretical_analysis ->
                user_situation_analysis -> plan_generation -> rule_validation
                -(hard violations & attempts<max)-> plan_repair -> rule_validation
6. RuleEngine   hard_violations() on the candidate schedule
7. PlanService  persist Plan (version, parent_plan_id, confidence),
                Tasks (with scheduled date/start/end from the candidate),
                TaskStandards; commit
8. GenerationService store ordered GenerationEvents, return job_id
9. API          respond 202 with job_id + events_url + plan
10. SSE         GET /plans/generation/{job_id}/events replays the events
```

Everything the graph needs is injected through `PlannerState`; the graph opens no session.

## 6. Transactions

- `get_db` yields a session and closes it; it never commits.
- Services call `session.commit()` at the end of a logical unit (`register`, `generate_plan`, `submit_feedback`, `replan`, `update_task`, `update_model`).
- Repositories `flush()` to obtain ids/refresh rows but never commit.
- On failure the session is closed without commit; use `session_scope()` for scripted/background work.

## 7. Plan versioning

A plan is immutable per version:

```
Plan v1 ──feedback──► ReplanService ──► Plan v2 (parent_plan_id = v1.id)
                                   └─► ReplanEvent(old_version, new_version, changed_tasks)
v1.status = superseded, v2.status = active
```

## 8. Replacement seams

| To replace | Implement / change | Untouched |
| --- | --- | --- |
| LLM | `LLMClient` (`app/infrastructure/llm/client.py`), set `LLM_PROVIDER` | agents (they take `llm=None`) |
| Agent | swap the agent class inside a node module | graph + state contract |
| ML model | implement the four Protocols in `app/ml/`, inject via `PlanService(...)` | services, API, DB |
| Scheduler | replace `Scheduler.schedule` | rules, services |
| Database | implement repositories against another store | domain, services |

## 9. Mock inventory (honest labelling)

| Path | Status |
| --- | --- |
| `app/agent/nodes/*` | Mock heuristic agents — deterministic, no LLM call |
| `app/infrastructure/llm/client.py::MockLLMClient` | MOCK — canned JSON, no network |
| `app/ml/*_predictor.py`, `app/ml/user_model.py` | `statistical-*` — simple statistics, **no trained model** |
| `app/infrastructure/ml/model_store.py` | PLACEHOLDER — nothing is trained/loaded yet |
| `app/application/services/generation_service.py` | synchronous run + event replay instead of a background worker |
