"""StructuredLLM tolerant parsing for wrapped / aliased narrative output."""

from __future__ import annotations

from app.agent.llm import StructuredLLM, StructuredResult
from app.agent.schemas import UserSituationNarrative
from app.infrastructure.llm.client import LLMResponse


class _FakeClient:
    name = "fake"

    def __init__(self, text: str) -> None:
        self.text = text

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_schema: dict | None = None,
    ) -> LLMResponse:
        return LLMResponse(text=self.text, model="fake")


def _run(text: str) -> StructuredResult[UserSituationNarrative]:
    return StructuredLLM(_FakeClient(text), max_retries=0).complete_model(
        prompt_name="user_situation",
        schema=UserSituationNarrative,
        variables={"user_context": "", "user_model": {}, "situation_estimate": {}, "progress": {}},
        fallback=UserSituationNarrative(narrative="fallback"),
    )


def test_unwraps_envelope_and_summary_alias() -> None:
    result = _run('{"data": {"summary": "today was hard"}}')
    assert result.used_llm is True
    assert result.value.narrative == "today was hard"


def test_accepts_extra_numeric_fields() -> None:
    result = _run('{"narrative": "ok", "duration_factor": 1.2, "stress_state": 7}')
    assert result.used_llm is True
    assert result.value.narrative == "ok"


def test_falls_back_when_no_expected_fields() -> None:
    result = _run('{"foo": "bar"}')
    assert result.used_llm is False
    assert result.value.narrative == "fallback"
