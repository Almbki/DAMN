---
purpose: Estimate the *theoretical* workload of each goal (video/reading/practice minutes, difficulty, cognitive load).
input_variables: goals, goal_analysis
expected_output: TheoreticalAnalysisResult
constraints: This is the theory side only - do NOT personalise to the user. Do not exceed 480 minutes for a single item.
when_used: initial plan graph and full replan, node theoretical_analysis
version: v1
---

You estimate how much work an item *normally* requires, before any
personalisation. Assume a motivated average student.

Produce TheoreticalItems at the **work-unit level**, not one blob per goal:

- For a `project` / `project_recurring` goal: one item **per work unit**, with
  `goal_id` (1-based) and `work_unit_index` (0-based). Do not collapse the
  curriculum into a single goal-level estimate.
- For a `recurring` goal: one item for the **reusable occurrence** (per
  occurrence workload), not the whole multi-month lifecycle. Its `subtasks`
  must stay empty: recurring habits are opaque execution blocks.
- For a `one_off` goal: one item.

Each item has:
- `video_minutes`, `reading_minutes`, `practice_minutes` (integers, min 0)
- `total_minutes` = the sum of the three
- `difficulty` from 1 (trivial) to 5 (very hard)
- `cognitive_load`: `high` for数学/算法/408/物理-style deep work, `medium` for
  language/coding practice, `low` for light reading, `restorative` for exercise
  or music
- `subtasks`: reuse the decomposition for one-off goals; empty for recurring
  and for project work units unless the user explicitly supplied steps

Rules:
- This is the theoretical baseline only. Do NOT adjust for the individual user
  here; that happens in a later step.
- If the user gave `estimated_minutes`, treat it as an upper sanity bound.
- Be internally consistent: practice-heavy subjects get more practice minutes.
- Never invent a work unit for a project that has none; that is a
  clarification problem, not a workload problem.

GOAL ANALYSIS:
{{goal_analysis}}

Return only the structured TheoreticalAnalysisResult object.
