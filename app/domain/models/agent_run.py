"""AgentRun domain entity - one agent execution, for auditability.

Records *what ran* (graph/prompt version, nodes, tools, counts) and the outcome
summary. It deliberately stores no prompt bodies and no free-text user input:
logs follow the minimum-necessary principle.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.domain.models.base import DomainModel, utcnow


class AgentRun(DomainModel):
    id: int | None = None
    #: Correlates with the LangGraph ``thread_id`` used for preview state.
    run_id: str
    user_id: int
    plan_id: int | None = None
    #: initial_plan | preview_adjusted | feedback_cycle | replan | micro_adjust
    trigger_type: str = "initial_plan"
    graph_version: str = "planner-v1"
    prompt_version: str = "v1"
    #: running | completed | failed
    status: str = "running"
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    #: Node names in execution order (counts, not payloads).
    nodes_executed: list[str] = Field(default_factory=list)
    #: [{tool, ok, duration_ms, summary, used_llm}] - no tool payloads.
    tool_calls: list[dict] = Field(default_factory=list)
    llm_calls: int = 0
    ml_prediction_id: int | None = None
    #: Small non-sensitive summary: route, task counts, confidence, degraded.
    result_summary: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
