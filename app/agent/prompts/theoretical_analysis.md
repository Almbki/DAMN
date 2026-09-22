---
purpose: Estimate the *theoretical* workload of each goal (video/reading/practice minutes, difficulty, cognitive load).
input_variables: goals, goal_analysis, user_profile
expected_output: TheoreticalAnalysisResult
constraints: This is the theory side only - do NOT personalise to the user. Do not exceed 480 minutes for a single item.
when_used: initial plan graph and full replan, node theoretical_analysis
version: v1
---

You estimate how much work an item *normally* requires, before any
personalisation. Assume a motivated average student.

For every goal produce one TheoreticalItem with:
- `video_minutes`, `reading_minutes`, `practice_minutes` (integers, min 0)
- `total_minutes` = the sum of the three
- `difficulty` from 1 (trivial) to 5 (very hard)
- `cognitive_load`: `high` for数学/算法/408/物理-style deep work, `medium` for
  language/coding practice, `low` for light reading, `restorative` for exercise
  or music
- `subtasks`: reuse the decomposition you were given

Rules:
- This is the theoretical baseline only. Do NOT adjust for the individual user
  here; that happens in a later step.
- If the user gave `estimated_minutes`, treat it as an upper sanity bound.
- Be internally consistent: practice-heavy subjects get more practice minutes.

GOAL ANALYSIS:
{{goal_analysis}}

USER PROFILE (context only - do not personalise):
{{user_profile}}

Return only the structured TheoreticalAnalysisResult object.
