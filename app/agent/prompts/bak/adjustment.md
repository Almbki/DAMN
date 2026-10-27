---
purpose: Revise a plan preview according to a single, bounded piece of user feedback.
input_variables: preview, user_adjustment, preferences, adjustment_count
expected_output: PlanGenerationResult
constraints: Apply only the requested change. Do not redesign the whole plan. Never output dates or times. Preserve series/occurrence identity. Adjustment budget is limited.
when_used: initial plan graph, after the user chooses "adjust" on a preview
version: v1
---

The user looked at the preview plan and asked for a change. Apply **only** what
they asked for and keep everything else identical.

Rules:
- Do not redesign the plan. No new goals, no re-ordering the whole schedule.
- Do not output scheduled dates or times; the scheduler re-runs afterwards.
- If the preview contains a series (`series_id` / `occurrence_date`), keep every
  occurrence's `series_id` and `occurrence_date` unchanged. Do not merge
  occurrences, do not change their dates, and do not turn a series into one-off
  tasks. You may adjust `title`, `description`, `estimated_duration` and
  `standards`; the deterministic layer re-runs scheduling.
- If the request conflicts with the user's stated constraints (e.g. "study 6h"
  when their available time is 2h), apply the closest feasible version and note
  the conflict in `notes`.
- This adjustment is number {{adjustment_count}}. The budget is small on
  purpose: real personalisation should come from execution feedback, not from
  endless manual editing.
- If the request is impossible, return the unchanged plan and explain why in
  `notes`.

CURRENT PREVIEW:
{{preview}}

USER REQUEST:
{{user_adjustment}}

PREFERENCES:
{{preferences}}

USER MODEL (Level 1 traits + Level 2 state - evidence, never a hard constraint):
{{user_model}}

Return only the structured PlanGenerationResult object.
