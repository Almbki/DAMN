"""Agent nodes.

Every node is a plain ``def (state, runtime) -> dict`` returning *updates* for
:class:`~app.agent.state.PlannerState`. Nodes orchestrate (load prompt, call a
tool, validate, write state); they never touch the database, HTTP or a session.

Node name -> graph stage mapping is 1:1 and is what the SSE layer publishes.
"""

from app.agent.nodes._shared import (
    build_rule_context,
    current_drafts,
    drafts_to_tasks,
    get_context,
    resolve_preferences,
)
from app.agent.nodes.adjustment_router import adjustment_router_node
from app.agent.nodes.classify import classify_request_node
from app.agent.nodes.context import load_context_node
from app.agent.nodes.feedback import process_feedback_node
from app.agent.nodes.finalization import plan_finalization_node
from app.agent.nodes.goal_analysis import goal_analysis_node
from app.agent.nodes.micro_adjustment import micro_adjustment_node
from app.agent.nodes.plan_generation import plan_generation_node
from app.agent.nodes.prediction import ml_prediction_node
from app.agent.nodes.preview import build_preview_payload, preview_node
from app.agent.nodes.repair import plan_repair_node
from app.agent.nodes.replan import new_plan_node
from app.agent.nodes.theoretical_analysis import theoretical_analysis_node
from app.agent.nodes.user_situation import user_situation_analysis_node
from app.agent.nodes.validation import rule_validation_node

__all__ = [
    "adjustment_router_node",
    "build_preview_payload",
    "build_rule_context",
    "classify_request_node",
    "current_drafts",
    "drafts_to_tasks",
    "get_context",
    "goal_analysis_node",
    "load_context_node",
    "micro_adjustment_node",
    "ml_prediction_node",
    "new_plan_node",
    "plan_finalization_node",
    "plan_generation_node",
    "plan_repair_node",
    "preview_node",
    "process_feedback_node",
    "resolve_preferences",
    "rule_validation_node",
    "theoretical_analysis_node",
    "user_situation_analysis_node",
]
