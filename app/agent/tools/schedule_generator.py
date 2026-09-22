"""``schedule_generator`` tool - deterministic calendar placement.

Wraps :class:`~app.domain.scheduling.scheduler.Scheduler`. Deliberately **not**
exposed to the LLM: the model decides *what* to do, never *when*.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.agent.tools.base import BaseTool
from app.domain.models import Task
from app.domain.rules.base import RuleContext
from app.domain.scheduling.schedule_result import CandidateSchedule
from app.domain.scheduling.scheduler import Scheduler


class ScheduleGeneratorInput(BaseModel):
    """Tasks (provisional ids) plus the rule context that carries the limits."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    tasks: list[Task] = Field(default_factory=list)
    context: RuleContext


class ScheduleGeneratorTool(BaseTool[ScheduleGeneratorInput, CandidateSchedule]):
    name = "schedule_generator"
    description = (
        "Heuristically place tasks on the calendar honouring capacity, buffers, "
        "high-cognitive spacing and subject conflicts. Deterministic, LLM-free."
    )
    llm_exposed = False

    def __init__(self, scheduler: Scheduler | None = None) -> None:
        self._scheduler = scheduler or Scheduler()

    def run(self, payload: ScheduleGeneratorInput) -> CandidateSchedule:
        return self._scheduler.schedule(payload.tasks, payload.context)

    def summarize(self, value: CandidateSchedule) -> str:
        return (
            f"placed {len(value.tasks)} task(s), "
            f"{len(value.unscheduled_task_ids)} unscheduled"
        )


__all__ = ["ScheduleGeneratorInput", "ScheduleGeneratorTool"]
