"""Agent nodes: node functions + their deterministic (mock) agents.

Every node is a plain ``def`` that takes the :class:`PlannerState` dict and
returns a dict of updates. Node names are fixed and used verbatim by both the
LangGraph state machine and the sequential fallback executor.

Provisional id contract: every task draft carries a *temporary* id equal to
``order_index + 1`` (1-based). This mapping is identical in
``plan_generation``, ``rule_validation`` and ``plan_repair``; the Plan Service
remaps these provisional ids to real primary keys after persisting the plan.
"""

from app.agent.nodes.goal_analysis import GoalAnalysisAgent, goal_analysis_node
from app.agent.nodes.plan_generation import (
    PlanGenerationAgent,
    drafts_to_tasks,
    plan_generation_node,
)
from app.agent.nodes.plan_repair import PlanRepairAgent, plan_repair_node
from app.agent.nodes.rule_validation import build_rule_context, rule_validation_node
from app.agent.nodes.theoretical_analysis import (
    TheoreticalAnalysisAgent,
    theoretical_analysis_node,
)
from app.agent.nodes.user_situation_analysis import (
    UserSituationAnalysisAgent,
    user_situation_analysis_node,
)

__all__ = [
    "GoalAnalysisAgent",
    "PlanGenerationAgent",
    "PlanRepairAgent",
    "TheoreticalAnalysisAgent",
    "UserSituationAnalysisAgent",
    "build_rule_context",
    "drafts_to_tasks",
    "goal_analysis_node",
    "plan_generation_node",
    "plan_repair_node",
    "rule_validation_node",
    "theoretical_analysis_node",
    "user_situation_analysis_node",
]