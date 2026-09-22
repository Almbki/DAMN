---
purpose: Rebuild the plan from the full context after a FULL_REPLAN decision.
input_variables: planning_context, ml_prediction, current_plan, progress, replan_reason
expected_output: PlanGenerationResult
constraints: Use the memory and history as evidence. Never output times. Never exceed daily capacity. Do not repeat a failed pattern from the previous version.
when_used: feedback loop graph, node plan_generation when route == FULL_REPLAN
version: v1
---

A full replan was triggered. You receive everything the system knows about this
user: the planning context (semantic / episodic / procedural memory),
the ML prediction, the current plan version and its execution progress, and the
reason for this replan.

Produce a new task set. This becomes a **new plan version**; the previous one is
kept for analysis, so do not try to "fix history".

Rules:
- Only carry forward work that is not finished; do not re-plan completed tasks.
- Use the memory layers as evidence, not decoration: if procedural memory says
  this user never completes high-cognitive work in the evening, do not schedule
  it there conceptually (the scheduler handles times, you handle the mix).
- If ML reports low completion probability or high stress, reduce the daily load
  in the drafts themselves (fewer / shorter tasks), do not just note it.
- Do not repeat a pattern that demonstrably failed in the previous version.
- Do not output dates or times.

REPLAN REASON:
{{replan_reason}}

PLANNING CONTEXT:
{{planning_context}}

ML PREDICTION:
{{ml_prediction}}

CURRENT PLAN:
{{current_plan}}

PROGRESS:
{{progress}}

Return only the structured PlanGenerationResult object.
