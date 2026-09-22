# Prompts

Prompts are Markdown files in `app/agent/prompts/`. They are **not** embedded in
Python, so behaviour changes never touch the graph.

## Location & format

```
app/agent/prompts/
├── __init__.py          # loader (load_prompt / list_prompts / clear_prompt_cache)
├── goal_analysis.md
├── theoretical_analysis.md
├── user_situation.md
├── initial_plan.md
├── adjustment.md
├── replanning.md
└── repair.md
```

Each file starts with front-matter:

```
---
purpose: one line - what this step is for
input_variables: goals, user_profile
expected_output: GoalAnalysisResult
constraints: the hard rules the model must not break
when_used: initial plan graph, node goal_analysis
version: v1
---
<prompt body with {{placeholders}}>
```

## The prompts

| Prompt | Used by | Tool / node | Input variables | Expected output |
| --- | --- | --- | --- | --- |
| `goal_analysis.md` | node `goal_analysis` | `task_decomposer` | `goals`, `user_profile`, `mbti`, `execution_weight` | `GoalAnalysisResult` |
| `theoretical_analysis.md` | node `theoretical_analysis` | `workload_estimator` | `goals`, `goal_analysis`, `user_profile` | `TheoreticalAnalysisResult` |
| `user_situation.md` | node `user_situation_analysis` | node (narrative only) | `user_context`, `ml_prediction`, `progress` | `UserSituationResult` (`narrative` only) |
| `initial_plan.md` | node `plan_generation` (INITIAL) | `plan_drafter` | `theoretical_analysis`, `user_situation`, `goals`, `preferences` | `PlanGenerationResult` |
| `adjustment.md` | node `plan_generation` (ADJUSTMENT) | `plan_drafter` | `preview`, `user_adjustment`, `preferences`, `adjustment_count` | `PlanGenerationResult` |
| `replanning.md` | node `plan_generation` (REPLAN) | `plan_drafter` | `planning_context`, `ml_prediction`, `current_plan`, `progress`, `replan_reason` | `PlanGenerationResult` |
| `repair.md` | **reserved** for the LLM repair path | — | `plan_draft`, `rule_violations`, `attempt` | `PlanRepairResult` |

> `repair.md` ships documented but unused: v1 repairs deterministically in
> `nodes/repair.py`. Wiring it in means calling `StructuredLLM` from that node
> and keeping the Rule Engine as the judge. It is listed here so the seam is
> visible, not to imply it runs today.

## How a prompt is executed

`app/agent/llm.py::StructuredLLM.complete_model`:

1. `load_prompt(name)` (cached, front-matter parsed),
2. `template.render(**variables)` — `{{var}}` substitution; unknown variables are
   left in place and reported in the rendered text,
3. `client.complete(prompt, system=<purpose>, json_schema=<schema>)`,
4. extract JSON, validate into the Pydantic schema,
5. on failure: append the validation error and retry up to
   `AgentConfig.llm_max_retries`,
6. on repeated failure: return the tool's **deterministic fallback** and report
   `used_llm=False`.

Schema strictness matters: every LLM-output schema extends `LLMOutput`
(`extra="forbid"`) and `StructuredLLM` also requires at least one of the
schema's own fields to be present. Without both, a wrong-but-valid JSON object
(e.g. `{"scaffold": ...}`) would silently validate into an empty result.

## How to change a prompt

1. Edit the `.md` body (and bump `version:` if the change is behavioural).
2. In the app, nothing else changes — `load_prompt` is `lru_cache`d per process,
   so a restart picks it up.
3. In a **test**, the cache must be cleared because the loader is memoised:

```python
from app.agent.prompts import clear_prompt_cache, load_prompt

clear_prompt_cache()
assert "new instruction" in load_prompt("goal_analysis").body
```

4. Preview the effect with the deterministic path first:

```bash
uv run pytest tests/agent -q
uv run python -c "from app.agent.prompts import list_prompts; print(list_prompts())"
```

## Adding a prompt

1. Create `app/agent/prompts/<name>.md` with the front-matter block.
2. Call it from a tool or node:

```python
result = self._llm.complete_model(
    prompt_name="my_prompt",
    schema=MyOutput,          # must extend LLMOutput
    variables={"foo": foo},
    fallback=MyOutput(),      # deterministic path
)
return result.value
```

3. Add a test that the prompt file exists and renders (see `tests/agent/test_tools.py`).

## Conventions

- One prompt = one step = one schema. Do not stack unrelated instructions.
- State the "never" rules explicitly (no dates/times, no re-estimating ML
  numbers, no diagnosing the user from MBTI).
- Keep `input_variables` accurate — the loader reports missing ones at render time.
