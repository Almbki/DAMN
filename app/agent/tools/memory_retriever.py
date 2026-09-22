"""``memory_retriever`` tool - read the planning context's memory layers.

Note: the *database* read happens in the application-layer Context Builder.
This tool only queries the already-assembled :class:`PlanningContext`, so it is
pure and testable. Not exposed to the LLM (it is a lookup, not a decision).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent.context import MemoryItem, MemoryKind, PlanningContext
from app.agent.tools.base import BaseTool


class MemoryQuery(BaseModel):
    kind: MemoryKind | None = None
    contains: str | None = None
    limit: int = Field(default=20, ge=1, le=200)


class MemoryDigest(BaseModel):
    """Compact, prompt-friendly view of the memory layers."""

    semantic: list[str] = Field(default_factory=list)
    episodic: list[str] = Field(default_factory=list)
    procedural: list[str] = Field(default_factory=list)
    items_returned: int = 0

    def as_prompt_block(self) -> str:
        return (
            f"SEMANTIC:\n{self._bullets(self.semantic)}\n"
            f"EPISODIC:\n{self._bullets(self.episodic)}\n"
            f"PROCEDURAL:\n{self._bullets(self.procedural)}"
        )

    @staticmethod
    def _bullets(lines: list[str]) -> str:
        return "\n".join(f"- {line}" for line in lines) if lines else "- (none)"


class MemoryRetrieverInput(BaseModel):
    context: PlanningContext
    query: MemoryQuery = Field(default_factory=MemoryQuery)


class MemoryRetrieverTool(BaseTool[MemoryRetrieverInput, MemoryDigest]):
    name = "memory_retriever"
    description = (
        "Query the user's structured memory (semantic / episodic / procedural) "
        "from the assembled planning context."
    )
    llm_exposed = False

    def run(self, payload: MemoryRetrieverInput) -> MemoryDigest:
        query = payload.query
        selected = self._filter(payload.context.semantic_memory, query)
        episodic = self._filter(payload.context.episodic_memory, query)
        procedural = self._filter(payload.context.procedural_memory, query)

        digest = MemoryDigest(
            semantic=[self._render(item) for item in selected],
            episodic=[self._render(item) for item in episodic],
            procedural=[self._render(item) for item in procedural],
        )
        digest.items_returned = (
            len(digest.semantic) + len(digest.episodic) + len(digest.procedural)
        )
        return digest

    @staticmethod
    def _filter(items: list[MemoryItem], query: MemoryQuery) -> list[MemoryItem]:
        result = items
        if query.kind is not None:
            result = [item for item in result if item.kind == query.kind]
        if query.contains:
            needle = query.contains.lower()
            result = [
                item
                for item in result
                if needle in item.key.lower() or needle in item.summary.lower()
            ]
        return result[: query.limit]

    @staticmethod
    def _render(item: MemoryItem) -> str:
        return item.summary or f"{item.key}: {item.value}"

    def summarize(self, value: MemoryDigest) -> str:
        return f"{value.items_returned} memory item(s)"


__all__ = ["MemoryDigest", "MemoryQuery", "MemoryRetrieverInput", "MemoryRetrieverTool"]
