from __future__ import annotations

import json
from datetime import date

import pytest
from ddsr.engine import DDSREngine
from ddsr.evidence.base import (
    EvidenceExtractionError,
    ExtractionContext,
    validate_extraction,
)
from ddsr.evidence.llm import LLMEvidenceExtractor, StaticLLMClient
from ddsr.evidence.rule_based import RuleBasedEvidenceExtractor
from ddsr.schemas import (
    EvidenceType,
    ExtractionResult,
    ReflectionInput,
)
from helpers import day, trait_profile


def context(known: set[str] | None = None) -> ExtractionContext:
    return ExtractionContext(
        known_task_ids=frozenset(known or set()),
        date=date(2026, 10, 20),
        min_quote_chars=2,
    )


def payload(**overrides) -> str:
    item = {
        "evidence_type": "fatigue",
        "direction": "increase",
        "strength": "moderate",
        "period": "evening",
        "task_id": None,
        "cause_category": None,
        "voluntary": None,
        "evidence_text": "今天很累",
        "source_field": "state_review",
    }
    item.update(overrides)
    return json.dumps({"evidence": [item]}, ensure_ascii=False)


def test_rule_based_extracts_explicit_states():
    reflection = ReflectionInput(
        state_review="今天下午很累，压力很大，但我有信心完成。",
        tomorrow_outlook="明天我有把握完成报告。",
    )
    result = RuleBasedEvidenceExtractor().extract(reflection, context())
    types = {item.evidence_type for item in result.evidence}
    assert EvidenceType.FATIGUE in types
    assert EvidenceType.STRESS in types
    assert EvidenceType.SELF_EFFICACY in types
    for item in result.evidence:
        assert item.evidence_text in reflection.text_for(item.source_field)


def test_rule_based_external_interruption_is_not_procrastination():
    reflection = ReflectionInput(
        stuck_points="我本来准备开始，但临时开会，不是拖延。"
    )
    result = RuleBasedEvidenceExtractor().extract(reflection, context())
    types = [item.evidence_type for item in result.evidence]
    assert EvidenceType.INTERRUPTION in types
    assert EvidenceType.PROCRASTINATION not in types
    interruption = next(
        item for item in result.evidence if item.evidence_type is EvidenceType.INTERRUPTION
    )
    assert interruption.voluntary is False
    assert interruption.cause_category.value == "external_interruption"


def test_rule_based_explicit_avoidance_is_procrastination():
    reflection = ReflectionInput(
        stuck_points="我一直在拖延，明知道该做却不想开始，主动逃避了。"
    )
    result = RuleBasedEvidenceExtractor().extract(reflection, context())
    procrastination = [
        item
        for item in result.evidence
        if item.evidence_type is EvidenceType.PROCRASTINATION
    ]
    assert len(procrastination) == 1
    assert procrastination[0].voluntary is True
    assert procrastination[0].cause_category.value == "avoidance"


def test_rule_based_late_start_alone_is_not_procrastination():
    reflection = ReflectionInput(stuck_points="我晚开始了一个小时，起晚了。")
    result = RuleBasedEvidenceExtractor().extract(reflection, context())
    assert not any(
        item.evidence_type is EvidenceType.PROCRASTINATION
        for item in result.evidence
    )


def test_rule_based_tomorrow_area_only_yields_self_efficacy():
    reflection = ReflectionInput(
        tomorrow_outlook="明天上午开会，可能很累，但我有把握完成报告。"
    )
    result = RuleBasedEvidenceExtractor().extract(reflection, context())
    assert result.evidence
    assert all(
        item.evidence_type is EvidenceType.SELF_EFFICACY
        for item in result.evidence
    )


def test_rule_based_generic_completion_is_not_self_efficacy():
    reflection = ReflectionInput(day_review="今天完成得不错。")
    result = RuleBasedEvidenceExtractor().extract(reflection, context())
    assert result.evidence == []


def test_llm_extractor_accepts_valid_json():
    reflection = ReflectionInput(state_review="今天很累")
    extractor = LLMEvidenceExtractor(StaticLLMClient(payload()))
    result = extractor.extract(reflection, context())
    assert len(result.evidence) == 1
    assert result.evidence[0].evidence_type is EvidenceType.FATIGUE
    assert result.evidence[0].evidence_text == "今天很累"


def test_llm_extractor_rejects_invalid_json():
    extractor = LLMEvidenceExtractor(StaticLLMClient("not json"))
    with pytest.raises(EvidenceExtractionError, match="invalid JSON"):
        extractor.extract(ReflectionInput(state_review="今天很累"), context())


def test_llm_extractor_rejects_fenced_json():
    extractor = LLMEvidenceExtractor(
        StaticLLMClient("```json\n" + payload() + "\n```")
    )
    with pytest.raises(EvidenceExtractionError, match="invalid JSON"):
        extractor.extract(ReflectionInput(state_review="今天很累"), context())


def test_llm_extractor_rejects_schema_invalid_payload():
    extractor = LLMEvidenceExtractor(
        StaticLLMClient('{"evidence":[{"evidence_type":"fatigue"}]}')
    )
    with pytest.raises(EvidenceExtractionError, match="schema"):
        extractor.extract(ReflectionInput(state_review="今天很累"), context())


def test_llm_extractor_rejects_extra_state_value():
    data = json.loads(payload())
    data["state_value"] = 0.9
    extractor = LLMEvidenceExtractor(StaticLLMClient(json.dumps(data)))
    with pytest.raises(EvidenceExtractionError, match="schema"):
        extractor.extract(ReflectionInput(state_review="今天很累"), context())


def test_llm_extractor_rejects_hallucinated_quote():
    extractor = LLMEvidenceExtractor(
        StaticLLMClient(payload(evidence_text="我很累"))
    )
    with pytest.raises(EvidenceExtractionError, match="verbatim"):
        extractor.extract(ReflectionInput(state_review="今天很累"), context())


def test_llm_extractor_rejects_unknown_task_id():
    extractor = LLMEvidenceExtractor(
        StaticLLMClient(payload(task_id="unknown"))
    )
    with pytest.raises(EvidenceExtractionError, match="unknown task_id"):
        extractor.extract(ReflectionInput(state_review="今天很累"), context({"t1"}))


def test_llm_extractor_rejects_external_cause_as_procrastination():
    raw = payload(
        evidence_type="procrastination",
        voluntary=True,
        cause_category="external_interruption",
        evidence_text="临时开会",
    )
    extractor = LLMEvidenceExtractor(StaticLLMClient(raw))
    with pytest.raises(EvidenceExtractionError, match="external cause"):
        extractor.extract(
            ReflectionInput(stuck_points="临时开会"), context()
        )


def test_validate_extraction_rejects_empty_source_field():
    item = {
        "evidence_type": "fatigue",
        "direction": "increase",
        "strength": "moderate",
        "period": "unspecified",
        "task_id": None,
        "cause_category": None,
        "voluntary": None,
        "evidence_text": "今天很累",
        "source_field": "state_review",
    }
    result = ExtractionResult.model_validate({"evidence": [item]})
    with pytest.raises(EvidenceExtractionError, match="empty reflection field"):
        validate_extraction(result, ReflectionInput(), context())


class BrokenExtractor:
    name = "broken"
    version = "0.0"

    def extract(self, reflection, context):
        raise EvidenceExtractionError("bad extractor output")


def test_engine_fails_closed_on_invalid_extraction(config):
    engine = DDSREngine(config=config, extractor=BrokenExtractor())
    profile = engine.process_day(
        day(reflection=ReflectionInput(state_review="今天很累")),
        trait_profile(),
    )
    assert profile.evidence.extraction_status == "failed"
    assert "bad extractor output" in (profile.evidence.error or "")
    assert profile.evidence.evidence_items == []
    for state in (profile.fatigue, profile.stress, profile.self_efficacy):
        assert state.value == pytest.approx(state.prior)
        assert state.evidence_count == 0
    assert any("fail-closed" in note for note in profile.limitations)
