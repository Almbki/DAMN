"""DDSR-V1: Daily Dynamic Self-Regulation State Model (Level 2).

Level 2 reads TraitProfile V1 as a read-only, versioned context dependency.  It
does not modify the Level 1 trait model.
"""

from .config import DDSRConfig, load_config
from .engine import DDSREngine
from .evidence import (
    EvidenceExtractionError,
    EvidenceExtractor,
    ExtractionContext,
    LLMClient,
    LLMEvidenceExtractor,
    RuleBasedEvidenceExtractor,
    StaticLLMClient,
)
from .schemas import (
    BehavioralIndicators,
    DayInput,
    DynamicStateProfile,
    EvidenceItem,
    PassiveContext,
    ReflectionInput,
    TaskExecution,
    TaskPlan,
)
from .store import JsonHistoryStore
from .trait_context import TraitContext

__version__ = "ddsr_v1"

__all__ = [
    "DDSRConfig",
    "load_config",
    "DDSREngine",
    "TraitContext",
    "JsonHistoryStore",
    "DayInput",
    "TaskPlan",
    "TaskExecution",
    "ReflectionInput",
    "PassiveContext",
    "EvidenceItem",
    "DynamicStateProfile",
    "BehavioralIndicators",
    "EvidenceExtractionError",
    "EvidenceExtractor",
    "ExtractionContext",
    "RuleBasedEvidenceExtractor",
    "LLMEvidenceExtractor",
    "LLMClient",
    "StaticLLMClient",
]
