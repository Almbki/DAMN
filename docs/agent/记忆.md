# Memory

Three structured memory layers. **No vector database** — everything is derived
from existing relational tables, and consolidated into `agent_memories` (P1).

```
Database ──► Context Builder (application) ──► PlanningContext ──► PlannerState
              app/application/context/          app/agent/context.py
              repo_context_builder.py

Feedback ──► MemoryService.refresh() ──► agent_memories (upsert)
                                            ▲
                        RepoContextBuilder ──┘  (merge_memory: persisted wins)
```

## Layer boundary (important)

| Concern | Where | Why |
| --- | --- | --- |
| Deriving memory items from rows | `app/agent/memory/*.py` | pure functions, unit-testable, no I/O |
| **Reading** the rows | `app/application/context/repo_context_builder.py` | the agent must not touch a session |
| **Persisting** the consolidation | `app/application/services/memory_service.py` | same reason; also needs repositories |
| Carrying the result | `PlanningContext` (`app/agent/context.py`) | reaches nodes as `state["user_context"]` |

The protocol the agent depends on is `ContextBuilderProtocol`
(`app/agent/context.py`); the concrete implementation lives in the application
layer. This keeps the "agents never touch the DB" rule intact while still giving
the graph rich context.

## Read / write loop (P1)

**Write** — `MemoryService.refresh(user_id)`, called by `FeedbackService` right
after a check-in is committed:

- derives semantic + episodic + procedural items with the pure derivers,
- **upserts** them into `agent_memories` keyed by `(user_id, kind, key)` (so the
  latest consolidated view wins rather than appending duplicates),
- prunes episodic rows to the most recent `EPISODIC_KEEP = 50`.
- Memory is best-effort: a failure is rolled back and never fails the feedback
  submission (the `feedbacks` row is the record of truth).

**Read** — `RepoContextBuilder.build()` derives fresh items *and* loads the
persisted rows, then `merge_memory(derived, stored)` overlays them:
**persisted wins per `(kind, key)`**, derived-only keys are kept. This means a
cold user still gets context from day one, while explicit/consolidated facts
survive.

```python
# app/application/context/repo_context_builder.py
def merge_memory(derived: list[MemoryItem], stored: list[AgentMemory]) -> list[MemoryItem]
```

Unknown `kind` values in the table are ignored rather than crashing planning.

## The three layers

| Layer | Module | Derives from | Example item |
| --- | --- | --- | --- |
| **Semantic** — stable facts, preferences, abilities | `memory/semantic.py` | `users.profile`, `users.execution_weight`, `user_models.duration_factors`, `user_models.preferred_time_slots` | `key="duration_factors"`, `summary="duration multipliers: {'high': 1.4}"` |
| **Episodic** — concrete things that happened | `memory/episodic.py` | `task_executions` (last 10), `feedbacks` (last 7) | `key="feedback:2026-09-20"`, `summary="2026-09-20: completion 40%, stress 8, energy 3"` |
| **Procedural** — how this user should be scheduled | `memory/procedural.py` | time-of-day completion rates, actual/planned overrun ratio, stress/energy averages, `user_models.completion_probability` | `key="avoid_time_of_day"`, `summary="avoid scheduling demanding work in the evening"` |

Procedural patterns need at least 3 samples (`_MIN_SAMPLES`) before they are
reported, and each item carries a `confidence` derived from the sample size.

## `MemoryItem`

```python
MemoryItem(
    kind=MemoryKind.SEMANTIC | EPISODIC | PROCEDURAL,
    key="stable-slug",
    value={"...": "JSON-serialisable"},
    summary="one line, used in prompts and traces",
    confidence=0.0..1.0,
    source="task_executions.time_of_day",   # provenance for debugging
)
```

`value` must stay JSON-serialisable: `PlanningContext` is stored in the
LangGraph checkpoint during a preview pause.

## How a node uses memory

Nodes never query memory directly. `plan_generation` renders a prompt block:

```python
digest = ctx.tool("memory_retriever").run(
    MemoryRetrieverInput(context=state["user_context"], query=MemoryQuery(limit=15))
)
payload.planning_context = digest.as_prompt_block()
```

`MemoryDigest.as_prompt_block()` produces a compact
`SEMANTIC / EPISODIC / PROCEDURAL` bullet list for the replanning prompt.

> Procedural memory is a **hint**, never a constraint. "This user performs badly
> in the evening" informs the drafts; the hard rules (buffers, daily limits,
> high-cognitive spacing) remain the Rule Engine's job.

## PII stance

Only derived summaries are written into prompts. Raw free-text feedback is not
copied into `value` (only the parsed `delay_reason`), and `RunMetadata` /
`agent_runs` record counts and versions rather than prompt bodies.

`MemoryService.forget(user_id)` deletes all persisted memory for a user
(privacy / reset); derived memory will simply be rebuilt on the next run.
