"""Process-wide UserModelRuntime factory.

Loading the real artifacts is cheap but not free; one runtime per process keeps
version/hash metadata stable for every request and worker thread.

The factory also wires the nightly-reflection evidence extractor:

* evidence_extractor=rule (or a mock/dummy llm_provider) uses the deterministic
  rule extractor;
* auto uses the LLM only when a real provider is configured;
* a failed LLM extraction falls back to the rules for that day, and the
  fallback's identity is what the engine/persistence records.

The adapter below is the ONLY bridge between the infrastructure LLM client and
the model package's tiny complete(prompt) -> str contract.
"""

from __future__ import annotations

import logging
import threading
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.infrastructure.llm.client import get_llm_client
from app.user_models.level2.ddsr.config import DDSRConfig
from app.user_models.level2.ddsr.evidence import (
    EvidenceExtractor,
    LLMEvidenceExtractor,
    RuleBasedEvidenceExtractor,
)
from app.user_models.level2.ddsr.evidence.base import ExtractionContext
from app.user_models.level2.ddsr.schemas import ExtractionResult, ReflectionInput
from app.user_models.runtime import UserModelRuntime

logger = logging.getLogger(__name__)

_MOCK_PROVIDERS = frozenset({"", "mock", "dummy"})


class HttpLLMCompletionAdapter:
    """Expose the infrastructure LLM client as complete(prompt) -> str.

    HttpLLMClient.complete returns an LLMResponse; the DDSR extractor consumes
    only the text, so this adapter keeps the model package free of any
    infrastructure import.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def complete(self, prompt: str) -> str:
        # Resolve the process-wide client per call so a settings change or a
        # client reset can never leave this long-lived runtime holding a closed
        # connection pool.
        return get_llm_client(self._settings).complete(prompt).text


class FallbackEvidenceExtractor:
    """Use the deterministic rules when the primary extractor fails.

    Fail-closed still applies at the engine boundary: if both extractors fail,
    the exception propagates and that day is recorded as failed. The
    name/version properties report the extractor that produced the current
    thread's last extraction, so persisted evidence keeps an honest provenance
    trail instead of always claiming the LLM ran.
    """

    def __init__(
        self,
        primary: EvidenceExtractor,
        fallback: EvidenceExtractor,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._local = threading.local()

    @property
    def name(self) -> str:
        return getattr(self._local, "name", self._primary.name)

    @property
    def version(self) -> str:
        return getattr(self._local, "version", self._primary.version)

    def extract(
        self,
        reflection: ReflectionInput,
        context: ExtractionContext,
    ) -> ExtractionResult:
        try:
            result = self._primary.extract(reflection, context)
        except Exception as exc:  # noqa: BLE001 - the rules must take over
            logger.warning(
                "evidence extractor %s failed; falling back to %s: %s: %s",
                self._primary.name,
                self._fallback.name,
                type(exc).__name__,
                exc,
            )
            result = self._fallback.extract(reflection, context)
            self._local.name = self._fallback.name
            self._local.version = self._fallback.version
            return result
        self._local.name = self._primary.name
        self._local.version = self._primary.version
        return result


def _provider(settings: Settings) -> str:
    return (settings.llm_provider or "mock").strip().lower()


def _llm_is_configured(settings: Settings) -> bool:
    """A real provider needs an API key or an explicit OpenAI-compatible base."""
    if _provider(settings) in _MOCK_PROVIDERS:
        return False
    return bool((settings.llm_api_key or "").strip()) or bool(
        (settings.llm_api_base or "").strip()
    )


def _rule_extractor() -> RuleBasedEvidenceExtractor:
    return RuleBasedEvidenceExtractor(DDSRConfig.from_json())


def build_evidence_extractor(settings: Settings | None = None) -> EvidenceExtractor:
    """Choose the reflection-evidence extractor from settings."""
    settings = settings or get_settings()
    choice = (settings.evidence_extractor or "auto").strip().lower()
    rule = _rule_extractor()
    if choice == "rule" or _provider(settings) in _MOCK_PROVIDERS:
        return rule
    if not _llm_is_configured(settings):
        logger.warning(
            "evidence_extractor=%r needs a configured LLM provider "
            "(llm_provider=%r); using deterministic rules",
            choice,
            settings.llm_provider,
        )
        return rule
    llm = LLMEvidenceExtractor(HttpLLMCompletionAdapter(settings))
    return FallbackEvidenceExtractor(llm, rule)


@lru_cache(maxsize=1)
def get_user_model_runtime() -> UserModelRuntime:
    settings = get_settings()
    return UserModelRuntime.from_settings(
        extractor=build_evidence_extractor(settings)
    )


def reset_user_model_runtime() -> None:
    """Test/settings helper: force the next call to reload artifacts."""
    get_user_model_runtime.cache_clear()


__all__ = [
    "FallbackEvidenceExtractor",
    "HttpLLMCompletionAdapter",
    "build_evidence_extractor",
    "get_user_model_runtime",
    "reset_user_model_runtime",
]
