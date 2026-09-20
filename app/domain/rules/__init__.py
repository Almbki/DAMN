"""Hard-constraint rule engine.

Constraint -> module mapping (first version):

1. High-cognitive tasks must not be consecutive        -> cognitive_load.py
2. Math and algorithm must not share a day             -> same_day_conflict.py
3. Daily total task minutes cap                        -> daily_limit.py
4. Mandatory buffer between tasks                      -> buffer_time.py
5. Must not exceed available time                      -> daily_limit.py
6. A task must not be scheduled after its DDL          -> deadline.py
7. Completed tasks must not be re-scheduled            -> completed_tasks.py
"""

from app.domain.rules.base import (
    Rule,
    RuleContext,
    RuleEngine,
    RuleViolation,
    default_rules,
)

__all__ = [
    "Rule",
    "RuleContext",
    "RuleEngine",
    "RuleViolation",
    "default_rules",
]
