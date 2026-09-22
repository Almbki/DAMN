"""``rule_validator`` tool - the hard-constraint authority.

Wraps :class:`~app.domain.rules.base.RuleEngine`. Deliberately **not** exposed
to the LLM: the engine, not the model, decides whether a constraint holds.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.agent.schemas import RuleValidationResult
from app.agent.tools.base import BaseTool
from app.domain.rules.base import RuleContext, RuleEngine
from app.domain.scheduling.schedule_result import CandidateSchedule


class RuleValidatorInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    schedule: CandidateSchedule
    context: RuleContext


class RuleValidatorTool(BaseTool[RuleValidatorInput, RuleValidationResult]):
    name = "rule_validator"
    description = (
        "Validate a candidate schedule against the hard constraints "
        "(cognitive load spacing, same-day conflicts, daily limits, buffers, "
        "deadlines, completed tasks). The only authority on hard rules."
    )
    llm_exposed = False

    def __init__(self, rule_engine: RuleEngine | None = None) -> None:
        self._rule_engine = rule_engine or RuleEngine()

    def run(self, payload: RuleValidatorInput) -> RuleValidationResult:
        violations = self._rule_engine.hard_violations(payload.schedule, payload.context)
        return RuleValidationResult(passed=not violations, violations=violations)

    def summarize(self, value: RuleValidationResult) -> str:
        return "valid" if value.passed else f"{len(value.violations)} hard violation(s)"


__all__ = ["RuleValidatorInput", "RuleValidatorTool"]
