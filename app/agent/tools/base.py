"""Tool contract.

A *tool* is a reusable capability with an explicit input/output contract. Tools
never touch the graph state - they take a payload and return a value, so they
can be unit-tested in isolation and reused by several nodes.

``llm_exposed`` marks tools that *may* be bound to a model's tool-calling
interface. Deterministic capabilities (scheduling, rule validation, statistics)
deliberately stay ``False``: the LLM must not decide hard constraints.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from pydantic import BaseModel


@dataclass(slots=True)
class ToolResult[TOut]:
    """Uniform outcome of a tool invocation (never raises to the caller)."""

    tool: str
    ok: bool = True
    value: TOut | None = None
    duration_ms: int = 0
    summary: str = ""
    used_llm: bool = False
    error: str | None = None


class BaseTool[TIn, TOut](ABC):
    """Base class for every agent tool."""

    name: str = "tool"
    description: str = ""
    #: True only when the capability is safe/useful for the LLM to call itself.
    llm_exposed: bool = False

    @abstractmethod
    def run(self, payload: TIn) -> TOut:
        """Execute the capability. May raise; :meth:`invoke` converts it."""

    def invoke(self, payload: TIn) -> ToolResult[TOut]:
        """Run the tool and capture timing/errors without failing the graph."""
        started = time.perf_counter()
        try:
            value = self.run(payload)
        except Exception as exc:  # noqa: BLE001 - a tool failure must not kill a run
            return ToolResult(
                tool=self.name,
                ok=False,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error=f"{type(exc).__name__}: {exc}",
            )
        return ToolResult(
            tool=self.name,
            ok=True,
            value=value,
            duration_ms=int((time.perf_counter() - started) * 1000),
            summary=self.summarize(value),
        )

    def summarize(self, value: TOut) -> str:
        """Short human-readable summary used for traces/SSE."""
        return self.name


@dataclass
class ToolRegistry:
    """Small registry so tools can be discovered, listed and tested."""

    _tools: dict[str, BaseTool] = field(default_factory=dict)

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools)

    def all(self) -> list[BaseTool]:
        return [self._tools[name] for name in self.names()]

    def llm_tools(self) -> list[BaseTool]:
        return [tool for tool in self.all() if tool.llm_exposed]


def describe_schema(schema: type[BaseModel] | None) -> dict:
    """JSON-schema of a tool payload (used for documentation / LLM binding)."""
    return schema.model_json_schema() if schema is not None else {}


__all__ = ["BaseTool", "ToolRegistry", "ToolResult", "describe_schema"]
