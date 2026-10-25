# Tools

A **tool** is a reusable capability with an explicit input/output contract. Tools
take a payload and return a value — they never read or write `PlannerState`, so
each one is unit-testable in isolation and reusable by several nodes.

Code: `app/agent/tools/`.

## Contract — `app/agent/tools/base.py`

```python
class BaseTool[TIn, TOut](ABC):
    name: str
    description: str
    llm_exposed: bool = False

    def run(self, payload: TIn) -> TOut: ...
    def invoke(self, payload: TIn) -> ToolResult[TOut]:   # timing + error capture
```

`invoke()` never raises: it returns
`ToolResult{tool, ok, value, duration_ms, summary, used_llm, error}` so a tool
failure degrades a node instead of killing a run.

## The tools

| Tool | File | Input | Output | `llm_exposed` | Notes |
| --- | --- | --- | --- | --- | --- |
| `task_decomposer` | `task_decomposer.py` | `TaskDecomposerInput{goals, user_profile, mbti, execution_weight}` | `GoalAnalysisResult` | **yes** | language understanding |
| `workload_estimator` | `workload_estimator.py` | `WorkloadEstimatorInput{goals, goal_analysis, user_profile}` | `TheoreticalAnalysisResult` | **yes** | theory-side estimation |
| `plan_drafter` | `plan_drafter.py` | `PlanDrafterInput{mode, goals, theoretical, user_situation, preview, …}` | `PlanGenerationResult` | **yes** | INITIAL / ADJUSTMENT / REPLAN |
| `schedule_generator` | `schedule_generator.py` | `ScheduleGeneratorInput{tasks, context}` | `CandidateSchedule` | no | wraps `Scheduler`; owns *when* |
| `rule_validator` | `rule_validator.py` | `RuleValidatorInput{schedule, context}` | `RuleValidationResult` | no | wraps `RuleEngine`; debt authority |
| `user_statistics` | `user_statistics.py` | `UserStatisticsInput{context, preferences}` | `UserStatistics` | no | pure aggregates over the context |
| `memory_retriever` | `memory_retriever.py` | `MemoryRetrieverInput{context, query}` | `MemoryDigest` | no | queries the *assembled* context |
| `task_duration_predictor` | `task_duration_predictor.py` | `TaskDurationPredictorInput{task_features, user, available_minutes}` | `TaskPredictions` | no | adapter over `PredictorSet` |

Registry: `default_registry(llm=…, predictors=…, scheduler=…, rule_engine=…)`
returns all eight; `registry.llm_tools()` returns only the three language tools.

## Why most tools are NOT exposed to the LLM

| Capability | Owner | Reason |
| --- | --- | --- |
| hard constraints | Rule Engine | a model may not decide whether a constraint holds |
| calendar placement | Scheduler | deterministic, testable, explainable |
| database reads | Context Builder | the LLM must not query user data |
| predictions | ML predictors | must be a model, not a prompt |
| statistics | plain Python | arithmetic is not reasoning |

Only `task_decomposer`, `workload_estimator` and `plan_drafter` are marked
`llm_exposed=True`: they are the steps where language understanding is the point.

## How to add a tool

```python
# app/agent/tools/deadline_risk.py
from pydantic import BaseModel, Field
from app.agent.tools.base import BaseTool

class DeadlineRiskInput(BaseModel):
    days_remaining: int = Field(ge=0)
    pending_minutes: int = Field(ge=0)
    daily_capacity: int = Field(gt=0)

class DeadlineRisk(BaseModel):
    ratio: float
    at_risk: bool

class DeadlineRiskTool(BaseTool[DeadlineRiskInput, DeadlineRisk]):
    name = "deadline_risk"
    description = "How much work is pending vs the time left."
    llm_exposed = False          # deterministic -> never expose

    def run(self, payload: DeadlineRiskInput) -> DeadlineRisk:
        capacity = max(payload.days_remaining * payload.daily_capacity, 1)
        ratio = payload.pending_minutes / capacity
        return DeadlineRisk(ratio=ratio, at_risk=ratio > 1.0)

    def summarize(self, value: DeadlineRisk) -> str:
        return f"risk={value.ratio:.2f}"
```

1. Register it in `app/agent/tools/__init__.py::default_registry`.
2. Export the classes in that module's `__all__`.
3. Call it from a node: `outcome = ctx.tool("deadline_risk").invoke(payload)`.
4. Append `ToolCallRecord` to `state["tool_results"]` so it shows up in traces:

```python
updates["tool_results"] = [ToolCallRecord(
    tool="deadline_risk", ok=outcome.ok,
    duration_ms=outcome.duration_ms, summary=outcome.summary, error=outcome.error,
)]
```
5. Add a test to `tests/agent/test_tools.py` (contract + one behaviour).
6. Add a row to the table above.

If the tool needs the LLM, take `StructuredLLM` in `__init__` and use
`complete_model(..., fallback=<deterministic>)` so it still works with
`LLM_PROVIDER=mock` or no key at all.
