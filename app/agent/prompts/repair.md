---
purpose: Explain and, if useful, propose a repair for the hard-rule violations reported by the Rule Engine.
input_variables: plan_draft, rule_violations, attempt
expected_output: PlanRepairResult
constraints: The Rule Engine is authoritative - you cannot declare a plan valid. Never output times. Never drop a task the user marked as fixed.
when_used: plan_repair node, after rule_validation reports violations
version: v1
---

The deterministic Rule Engine rejected the candidate plan. You receive the draft
tasks and the exact violations.

Your job:
- Explain, in one short line per violation, what caused it.
- Propose a repaired task list that is likely to pass validation.

Rules:
- You do **not** decide whether a constraint is satisfied. Only the Rule Engine
  does. Never claim "this is now valid".
- Prefer reducing load or re-mixing cognitive load over deleting work. Only drop
  a task when nothing else can satisfy a hard constraint, and prefer the lowest
  priority one.
- Never output scheduled dates or times.
- `attempt` is the current repair round; the loop is bounded.

CURRENT DRAFT:
{{plan_draft}}

RULE VIOLATIONS:
{{rule_violations}}

ATTEMPT: {{attempt}}

Return only the structured PlanRepairResult object.
