"""Task-decomposition domain logic.

Only pure functions live here: the agent supplies candidate drafts, the domain
decides whether their structure is acceptable. No database, no framework, no
quality judgement (format errors only).
"""

from app.domain.decomposition.validation import DraftIssue, validate_draft_tasks

__all__ = ["DraftIssue", "validate_draft_tasks"]
