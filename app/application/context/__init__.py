"""Application-layer context assembly (the agent's only door to the database).

Implements :class:`app.agent.context.ContextBuilderProtocol` using the existing
repositories, then calls the pure memory derivers. The agent never imports this
module - it only sees the resulting ``PlanningContext``.
"""

from app.application.context.repo_context_builder import RepoContextBuilder

__all__ = ["RepoContextBuilder"]
