# DAMN — Dynamic Agentic Modified No-more-delay todolist (Backend)

A **feedback-driven adaptive task planning system** — not a todo list. It turns
goals into a plan, watches how the user actually executes it, learns a per-user
model, and replans.

```
theory workload + user history (ML) + hard constraints (rules) + scheduling + feedback loop
```

> Engineering skeleton, first version. ML is **mock/statistical only** — no
> trained models ship here. Mocks and placeholders are marked in code.

---

## Architecture

```
Frontend (React Native / Web)
        │
        ▼
API / Presentation          app/api, app/schemas
        │
        ▼
Application / Service       app/application  (orchestration, transactions, authz)
        │
        ▼
Domain / Core               app/domain, app/core  (entities, rules, scheduler)
        │
        ▼
Infrastructure              app/infrastructure  (DB, repos, LLM, model store)
```

Plus two side-cars used **by the Application layer only**:

- `app/agent` — LangGraph state machine + structured (mock) agents
- `app/ml` — predictor Protocol interfaces + statistical mocks

Design rules enforced throughout:

1. `app/core` and `app/domain` never import FastAPI or SQLAlchemy.
2. Agents never touch the database — the Service injects everything.
3. The **Rule Engine** is the only authority on hard constraints; LLM output
   never decides whether a constraint holds.
4. Repositories never commit — services own transactions.
5. Predictors are Protocols — swap in LightGBM/XGBoost/sklearn/PyTorch without
   touching services or API.

See [`docs/architecture.md`](docs/architecture.md) for the full module map.

---

## Requirements

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/) for dependency management
- SQLite (default, zero setup) or PostgreSQL 16
- Docker (optional, for Postgres + API)

---

## Quick start

```bash
# 1. install dependencies (creates .venv)
uv sync --extra dev

# 2. configure environment
cp .env.example .env          # Windows: Copy-Item .env.example .env

# 3. run the API (SQLite dev DB is created automatically)
uv run uvicorn app.main:app --reload
```

- Swagger UI → <http://localhost:8000/docs>
- ReDoc → <http://localhost:8000/redoc>
- Health → <http://localhost:8000/health>

### Database migrations (Alembic)

```bash
uv run alembic upgrade head
```

### Tests

```bash
uv run pytest
```

### PostgreSQL via Docker

```bash
docker compose up --build
```

---

## API overview

Base path: `/api/v1`

| Method | Path | Description |
| --- | --- | --- |
| POST | `/auth/register` | Register |
| POST | `/auth/login` | Login → JWT |
| GET | `/users/me` | Current user |
| PATCH | `/users/me` | Update profile |
| POST | `/plans/generate` | Generate plan (returns job id) |
| GET | `/plans/generation/{job_id}/events` | **SSE** generation progress |
| GET | `/plans` | List plans |
| GET | `/plans/{plan_id}` | Plan detail (tasks + standards) |
| PATCH | `/plans/{plan_id}/tasks/{task_id}` | Patch task / record execution |
| POST | `/plans/{plan_id}/feedback` | Submit daily feedback |
| GET | `/plans/{plan_id}/feedback` | Feedback history |
| POST | `/plans/{plan_id}/replan` | Replan → new version |
| GET | `/plans/{plan_id}/replan/eligibility` | Cooldown / eligibility |
| GET | `/plans/{plan_id}/insights` | Data insights |

Full reference: [`docs/api.md`](docs/api.md).

---

## Repository layout

```
app/
├── main.py                     FastAPI app factory
├── api/                        presentation: deps, router, v1 endpoints
├── application/                services, DTOs, application exceptions
│   ├── services/               auth / plan / feedback / replan / user_model / generation / insight
│   └── dto/
├── domain/                     entities, hard rules, heuristic scheduler
│   ├── models/
│   ├── rules/
│   └── scheduling/
├── core/                       config, security (JWT + PBKDF2), logging
├── agent/                      LangGraph state machine + mock agents
│   ├── nodes/
│   ├── graph.py
│   ├── state.py
│   └── schemas.py
├── ml/                         predictor Protocols + statistical mocks
├── infrastructure/             SQLAlchemy models, repositories, LLM + model store
└── schemas/                    Pydantic request/response models
tests/
├── unit/  integration/  api/
docs/
alembic/
```

---

## The five responsibilities

| Component | Question it answers |
| --- | --- |
| **Theoretical Analysis Agent** | How much work does this *normally* need? |
| **User Situation Analysis Agent** | How much work does *this user* actually need? |
| **ML User Model** | How does that gap shrink as history accumulates? |
| **Scheduler** | How do predictions become a calendar? |
| **Rule Engine** | Is the plan hard-constraint safe? |
| **LangGraph** | How do complex planning/replan flows get orchestrated? |

---

## Mock / placeholder inventory

Honest labelling — these are **not** trained ML:

| Area | Status |
| --- | --- |
| `app/agent/nodes/*` | Mock heuristic agents (deterministic, no LLM call) |
| `app/infrastructure/llm/client.py` → `MockLLMClient` | MOCK — returns canned JSON |
| `app/ml/*` | `statistical-*` predictors: simple statistics, no trained model |
| `app/infrastructure/ml/model_store.py` | PLACEHOLDER — no models to load yet |
| SSE generation | Pipeline runs synchronously, events are stored and replayed |

---

## Roadmap seams (designed for replacement)

- **LLM** — implement `LLMClient`; agents already accept it.
- **Agents** — replace a node's agent class; graph/state contract unchanged.
- **ML** — implement `DurationPredictor` / `CompletionPredictor` /
  `StressPredictor` / `TimeSlotPredictor`; inject via `PlanService`.
- **Scheduler** — replace `Scheduler.schedule`; rules stay authoritative.
- **Database** — repository interfaces isolate SQLAlchemy.

See [`docs/development.md`](docs/development.md) and [`docs/ml.md`](docs/ml.md).
