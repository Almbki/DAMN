# Dependencies

## Layer boundaries

```
api/               app/api, app/schemas
  │
application/       app/application        ← owns transactions & permissions
  ├─► agent/       app/agent              (orchestration, prompts, tools)
  ├─► ml/          app/ml                 (predictor interfaces + fallbacks)
  ▼
domain/ + core/    app/domain, app/core   ← pure logic, no frameworks
  ▲
infrastructure/    app/infrastructure     (SQLAlchemy, repositories, LLM client)
```

| Rule | How it is enforced |
| --- | --- |
| `app/core` and `app/domain` never import FastAPI or SQLAlchemy | convention + review |
| Agent nodes never touch the database | the concrete reader lives in `app/application/context/repo_context_builder.py`; the agent only knows `ContextBuilderProtocol` |
| Agent does not import `app.infrastructure` at runtime | `LLMClient` is imported under `TYPE_CHECKING` only; the client is duck-typed |
| Agent never manages transactions | `PlanService` commits |
| The LLM never decides hard constraints | `rule_validation` uses the Rule Engine tool only |

## How dependencies reach a node

LangGraph's run-scoped context:

```python
graph = StateGraph(PlannerState, context_schema=PlannerContext)
result = graph.invoke(state, config={"configurable": {"thread_id": tid}}, context=ctx)

def some_node(state: PlannerState, runtime: Runtime[PlannerContext]) -> dict:
    ctx = runtime.context          # scheduler, rule_engine, predictors, llm, ...
```

`PlannerContext` (a dataclass in `app/agent/state.py`) carries:

| Field | Type | Purpose |
| --- | --- | --- |
| `scheduler` | `domain.scheduling.Scheduler` | deterministic placement |
| `rule_engine` | `domain.rules.RuleEngine` | hard constraints |
| `predictors` | `app.ml.predictors.PredictorSet` | ML interfaces |
| `llm` | `StructuredLLM \| None` | prompt-driven reasoning |
| `context_builder` | `ContextBuilderProtocol \| None` | the only DB reader |
| `config` | `AgentConfig` | budgets, versions, retry limits |
| `emit` | `Callable[[str, dict], None] \| None` | event sink (SSE/trace) |
| `tools` | lazily built `ToolRegistry` | `ctx.tool("plan_drafter")` |

## Why dependencies are NOT in the state

`PlannerState` is checkpointed by LangGraph, so it must be serialisable. Putting
`Scheduler`/`RuleEngine`/`PredictorSet`/`LLMClient` instances in the state (as
the previous implementation did) makes.

- checkpointing fail (or emit unregistered-type warnings),
- `interrupt()` / resume impossible,
- state migration impossible.

`PlannerState` therefore holds **only data** (Pydantic models, enums, scalars,
lists) plus accumulating fields with `operator.add` reducers.

## Per-call event sink

`PlannerGraph._with_emit(sink)` returns a `dataclasses.replace` copy of the
context carrying that call's sink, falling back to `self.context.emit` when
`None`. That is why the Service can wire the sink once
(`self._graph(emit)`) and still get events from every graph call.

## Provider wiring

`app/api/deps.py::get_plan_service` builds the graph collaborators per request:

```python
llm = StructuredLLM(get_llm_client(settings), max_retries=..., prompt_version=...)
return PlanService(db, llm=llm, checkpointer=get_checkpointer(settings))
```

`PlanService` defaults the rest (`PredictorSet.default()`, `Scheduler()`,
`RuleEngine()`, `RepoContextBuilder(db)`), so tests can inject fakes without
touching production code.
