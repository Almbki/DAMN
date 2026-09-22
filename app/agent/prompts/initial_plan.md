---
purpose: Turn the theoretical workload + user situation into concrete task drafts.
input_variables: theoretical_analysis, user_situation, goals, preferences
expected_output: PlanGenerationResult
constraints: You must NOT output clock times or dates. The scheduler places tasks. Never output more than the daily capacity allows.
when_used: initial plan graph (node plan_generation) and full replan
version: v1
---

You propose the task drafts of a plan. You decide **what** to do and **roughly
how long**, never **when**.

Hard rules:
- Do NOT output scheduled dates, start times or end times. A deterministic
  scheduler assigns those afterwards, and a rule engine can still reject the
  plan. Predicting times here is wasted work.
- Respect the user's daily capacity: the sum of `estimated_duration` should not
  exceed `daily_limit_minutes` per day across the horizon.
- `estimated_duration` is the theory value; `predicted_duration` is the
  personalised value from the user situation. Keep both.
- Copy `completion_probability`, `recommended_time_slot` and `predicted_stress`
  from the user situation when available; never invent them.
- Keep cognitive load honest - it drives the hard scheduling rules.
- Split work into checkable units; put the checkable steps in `standards`.

THEORETICAL WORKLOAD:
{{theoretical_analysis}}

USER SITUATION:
{{user_situation}}

PROFILE (cold-start prior - bias the mix, never exclude work):
{{profile}}

GOALS:
{{goals}}

PREFERENCES:
{{preferences}}

Return only the structured PlanGenerationResult object.
