"""Deterministic rule-based evidence extraction (auditable offline fallback).

This extractor exists so the DDSR pipeline can be exercised without an LLM: unit
tests, CI, local demos, and graceful degradation when the production extractor is
unavailable.  It is **not** the production path.  The production path is the LLM
extractor, whose output is audited by :func:`validate_extraction`; this module is
the transparent, reproducible stand-in.

Design constraints (all intentional):

* It reads only the four ``ReflectionInput`` text fields.  Task logs, state
  values, traits, and passive context are never consulted, and the extractor
  never computes a state value.
* It emits evidence only for *explicit* lexical statements, and every
  ``evidence_text`` is the exact sentence (or an exact substring of it) from the
  source field, so the audit in ``validate_extraction`` always passes.
* A late start, a high start delay, or a bare "delay" word is never treated as
  procrastination.  Procrastination additionally requires a negation-free,
  voluntary statement (``不是拖延`` / ``not procrastinating`` are skipped).
* External interruptions (meetings, phone calls, family emergencies, being
  called away) become ``INTERRUPTION`` with ``voluntary=False`` and
  ``cause_category=EXTERNAL_INTERRUPTION`` -- never procrastination.
* Generic completion statements ("今天完成得不错") are not self-efficacy
  evidence; only confidence/capability language is.

The bilingual lexicon below is deliberately small.  Recall is therefore limited:
anything not covered is reported as "no evidence", which the state layer treats
as additional uncertainty rather than as a negative signal.
"""

from __future__ import annotations

import re

from ..config import DDSRConfig
from ..schemas import (
    CauseCategory,
    Direction,
    EvidenceItem,
    EvidenceType,
    ExtractionResult,
    Period,
    ReflectionField,
    ReflectionInput,
    Strength,
)
from .base import ExtractionContext, validate_extraction

__all__ = ["RuleBasedEvidenceExtractor"]


# ---------------------------------------------------------------------------
# Lexicon (Chinese + English).  Only explicit wording is listed on purpose.
# ---------------------------------------------------------------------------

FATIGUE_INCREASE: tuple[str, ...] = (
    "精疲力尽",
    "精疲力竭",
    "疲惫不堪",
    "疲劳",
    "很累",
    "好累",
    "太累",
    "累死",
    "累",
    "没精神",
    "精力不足",
    "没力气",
    "很困",
    "好困",
    "太困",
    "困死了",
    "tired",
    "exhausted",
    "exhausting",
    "fatigue",
    "fatigued",
    "drained",
    "worn out",
    "burned out",
    "burnt out",
    "sleepy",
)

FATIGUE_DECREASE: tuple[str, ...] = (
    "精力充沛",
    "精力旺盛",
    "精神很好",
    "精神不错",
    "精神好",
    "休息好了",
    "不累",
    "不太累",
    "不怎么累",
    "没那么累",
    "不疲劳",
    "energetic",
    "rested",
    "refreshed",
    "full of energy",
    "not tired",
    "not exhausted",
    "not drained",
)

STRESS_INCREASE: tuple[str, ...] = (
    "压力很大",
    "压力大",
    "有压力",
    "压力",
    "焦虑",
    "紧张",
    "崩溃",
    "扛不住",
    "受不了",
    "心慌",
    "烦躁",
    "担心",
    "stressed",
    "stressful",
    "stress",
    "overwhelmed",
    "anxious",
    "anxiety",
    "panicking",
    "freaking out",
    "nervous",
)

STRESS_DECREASE: tuple[str, ...] = (
    "放松",
    "压力不大",
    "没压力",
    "没有压力",
    "不紧张",
    "不焦虑",
    "不崩溃",
    "心情平静",
    "平静",
    "轻松",
    "calm",
    "relaxed",
    "not stressed",
    "no stress",
    "not anxious",
    "not nervous",
    "at ease",
)

SELF_EFFICACY_INCREASE: tuple[str, ...] = (
    "有信心",
    "有把握",
    "能完成",
    "可以完成",
    "能做到",
    "可以做到",
    "相信自己",
    "自信",
    "信心满满",
    "搞得定",
    "能搞定",
    "confident",
    "can handle",
    "sure I can",
    "I can do it",
    "capable",
    "up for it",
)

SELF_EFFICACY_DECREASE: tuple[str, ...] = (
    "没信心",
    "没有信心",
    "没把握",
    "没有把握",
    "做不到",
    "完不成",
    "不能完成",
    "无法完成",
    "不自信",
    "没自信",
    "力不从心",
    "怀疑自己",
    "not sure I can",
    "can't handle",
    "cannot handle",
    "not confident",
    "no confidence",
    "doubt myself",
)

PROCRASTINATION: tuple[str, ...] = (
    "拖延",
    "拖延症",
    "逃避",
    "回避",
    "一直拖",
    "拖着不做",
    "不想开始",
    "明知该做",
    "procrastinate",
    "procrastinated",
    "procrastinating",
    "procrastination",
    "avoid",
    "avoided",
    "avoiding",
    "put off",
    "putting it off",
    "kept putting it off",
    "kept postponing",
    "didn't want to start",
    "did not want to start",
    "don't want to start",
)

INTERRUPTION: tuple[str, ...] = (
    "临时开会",
    "突然开会",
    "被叫去开会",
    "开会",
    "会议",
    "被叫走",
    "被叫去",
    "叫走",
    "家里有急事",
    "家里有事",
    "临时有事",
    "急事",
    "电话",
    "接电话",
    "来电",
    "被打断",
    "打断",
    "中断",
    "临时安排",
    "突发事件",
    "emergency",
    "urgent",
    "meeting",
    "interrupted",
    "interruption",
    "called away",
    "was called",
    "phone call",
    "phone rang",
    "got a call",
    "unexpected visit",
    "pulled away",
    "had to leave",
)

#: Illness / plan-change wording also blocks a procrastination label, because
#: the schema treats these as external causes.
EXTERNAL_CAUSE_GUARD: tuple[str, ...] = (
    "生病",
    "发烧",
    "感冒",
    "不舒服",
    "计划取消",
    "计划变了",
    "ill",
    "sick",
    "unwell",
    "plan changed",
    "schedule changed",
)

NONVOLUNTARY_MARKERS: tuple[str, ...] = (
    "不知不觉",
    "无意识",
    "不自觉",
    "不是故意",
    "并非故意",
    "unintentionally",
    "without realizing",
    "without meaning to",
    "didn't mean to",
    "did not mean to",
)

AVOIDANCE_MARKERS: tuple[str, ...] = (
    "逃避",
    "回避",
    "躲避",
    "escape",
    "avoid",
    "avoidance",
)

DISTRACTION_MARKERS: tuple[str, ...] = (
    "分心",
    "走神",
    "刷手机",
    "刷视频",
    "看视频",
    "玩游戏",
    "刷剧",
    "distraction",
    "distracted",
    "scrolling",
    "social media",
)

VOLITION_MARKERS: tuple[str, ...] = (
    "不想开始",
    "不想做",
    "明知该做",
    "没动力",
    "懒得",
    "kept postponing",
)

STATE_LEXICON: dict[EvidenceType, tuple[tuple[str, ...], tuple[str, ...]]] = {
    EvidenceType.FATIGUE: (FATIGUE_INCREASE, FATIGUE_DECREASE),
    EvidenceType.STRESS: (STRESS_INCREASE, STRESS_DECREASE),
    EvidenceType.SELF_EFFICACY: (
        SELF_EFFICACY_INCREASE,
        SELF_EFFICACY_DECREASE,
    ),
}

# ---------------------------------------------------------------------------
# Sentence segmentation, matching helpers
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;])|(?<=[.])\s+|\n+")

_ZH_NEGATION = re.compile(
    r"(不是|没有|并没|并未|并非|未曾|从不|绝非|不太|不怎么|不|没|无|未)"
    r"(?:觉得|那么|太|怎么|很|是)?$"
)
_EN_NEGATION = re.compile(r"\b(not|no|never|without|hardly)\b[^.!?;]{0,10}$")

_ZH_PROCRASTINATION_NEGATION: tuple[str, ...] = (
    "不是",
    "没有",
    "并没",
    "并未",
    "并非",
    "未曾",
    "从不",
    "绝非",
    "才不是",
    "不算",
)
_EN_PROCRASTINATION_NEGATION = re.compile(
    r"\b(not|no|never|didn't|did not|wasn't|was not|isn't|is not|without)\b"
)
_CONTRAST_MARKERS: tuple[str, ...] = ("而是", "但是", "可是", "不过", "反而")
_EN_CONTRAST_MARKERS: tuple[str, ...] = ("but", "however", "instead")

_STRONG_MARKERS: tuple[str, ...] = (
    "崩溃",
    "精疲力尽",
    "精疲力竭",
    "彻底",
    "极度",
    "非常",
    "特别",
    "完全",
    "受不了",
    "扛不住",
    "太",
    "extremely",
    "completely",
    "totally",
    "absolutely",
    "exhausted",
    "overwhelmed",
    "can't",
)
_WEAK_MARKERS: tuple[str, ...] = (
    "有点",
    "稍微",
    "有些",
    "还好",
    "一点点",
    "不太",
    "不怎么",
    "没那么",
    "a bit",
    "slightly",
    "a little",
    "somewhat",
)

_PERIOD_MARKERS: tuple[tuple[Period, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        Period.NIGHT,
        ("半夜", "深夜", "凌晨", "午夜", "夜里", "夜间"),
        ("middle of the night", "late at night", "at night", "night"),
    ),
    (
        Period.EVENING,
        ("晚上", "今晚", "傍晚", "晚饭后"),
        ("tonight", "this evening", "evening"),
    ),
    (
        Period.MORNING,
        ("早上", "上午", "早晨", "清晨", "一早"),
        ("this morning", "in the morning", "morning"),
    ),
    (
        Period.AFTERNOON,
        ("下午", "中午", "午后"),
        ("this afternoon", "in the afternoon", "afternoon"),
    ),
)


def _is_ascii(phrase: str) -> bool:
    return all(ord(char) < 128 for char in phrase)


def _find_all(text: str, phrase: str) -> list[tuple[int, int]]:
    """Return all spans of ``phrase`` in ``text`` (word-bounded for English)."""
    if _is_ascii(phrase):
        pattern = re.compile(
            r"(?<![A-Za-z])" + re.escape(phrase) + r"(?![A-Za-z])",
            re.IGNORECASE,
        )
        return [(match.start(), match.end()) for match in pattern.finditer(text)]
    spans: list[tuple[int, int]] = []
    start = text.find(phrase)
    while start != -1:
        spans.append((start, start + len(phrase)))
        start = text.find(phrase, start + 1)
    return spans


def _overlaps(span: tuple[int, int], others: list[tuple[int, int]]) -> bool:
    return any(span[0] < other[1] and other[0] < span[1] for other in others)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    """Match Chinese markers as substrings and English markers as whole words."""
    lowered = text.lower()
    for marker in markers:
        if _is_ascii(marker):
            pattern = (
                r"(?<![A-Za-z])" + re.escape(marker.lower()) + r"(?![A-Za-z])"
            )
            if re.search(pattern, lowered):
                return True
        elif marker in text:
            return True
    return False


def _blocked_match(text: str, span: tuple[int, int], phrase: str) -> bool:
    """Reject known lexical false friends (e.g. 累积 for the word 累)."""
    if phrase == "累":
        before = text[max(0, span[0] - 1) : span[0]]
        return before in {"积", "连"}
    return False


def _negated_short(text: str, start: int) -> bool:
    """Negation window immediately before a state keyword."""
    zh_window = text[max(0, start - 8) : start]
    if _ZH_NEGATION.search(zh_window):
        return True
    en_window = text[max(0, start - 18) : start].lower()
    return _EN_NEGATION.search(en_window) is not None


def _split_sentences(text: str) -> list[str]:
    units: list[str] = []
    for chunk in _SENTENCE_SPLIT.split(text):
        cleaned = chunk.strip()
        if cleaned:
            units.append(cleaned)
    return units


def _infer_period(text: str) -> Period:
    lowered = text.lower()
    for period, zh_phrases, en_phrases in _PERIOD_MARKERS:
        if any(phrase in text for phrase in zh_phrases):
            return period
        for phrase in en_phrases:
            if re.search(r"\b" + re.escape(phrase) + r"\b", lowered):
                return period
    return Period.UNSPECIFIED


def _infer_strength(text: str) -> Strength:
    if _contains_any(text, _WEAK_MARKERS):
        return Strength.WEAK
    if _contains_any(text, _STRONG_MARKERS):
        return Strength.STRONG
    return Strength.MODERATE


class RuleBasedEvidenceExtractor:
    """Small deterministic extractor used as an auditable offline fallback."""

    name = "rule_based_evidence"
    version = "1.0"

    def __init__(self, config: DDSRConfig | None = None) -> None:
        self.config = config if config is not None else DDSRConfig()

    # -- public API ---------------------------------------------------------

    def extract(
        self, reflection: ReflectionInput, context: ExtractionContext
    ) -> ExtractionResult:
        min_quote_chars = max(
            1, self.config.min_quote_chars, context.min_quote_chars
        )
        items: list[EvidenceItem] = []
        for field in ReflectionField:
            text = reflection.text_for(field)
            if not text:
                continue
            items.extend(self._extract_field(text, field, min_quote_chars))

        deduped: list[EvidenceItem] = []
        seen: set[tuple[EvidenceType, Direction, str]] = set()
        for item in items:
            key = (item.evidence_type, item.direction, item.evidence_text)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        result = ExtractionResult(evidence=deduped)
        return validate_extraction(result, reflection, context)

    # -- internals ----------------------------------------------------------

    def _extract_field(
        self,
        text: str,
        field: ReflectionField,
        min_quote_chars: int,
    ) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        for sentence in _split_sentences(text):
            items.extend(
                self._extract_sentence(sentence, field, min_quote_chars)
            )
        return items

    def _extract_sentence(
        self,
        sentence: str,
        field: ReflectionField,
        min_quote_chars: int,
    ) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        period = _infer_period(sentence)
        strength = _infer_strength(sentence)

        # Area D is about tomorrow.  Only confidence/capability language is
        # today's evidence there; a predicted "tomorrow meeting" or "tomorrow I
        # may be tired" must not become today's interruption/fatigue evidence.
        allow_today_behavior = field is not ReflectionField.TOMORROW_OUTLOOK
        interruption_span = (
            self._interruption_span(sentence) if allow_today_behavior else None
        )
        if interruption_span is not None:
            quote = self._quote(sentence, interruption_span, min_quote_chars)
            if quote is not None:
                items.append(
                    EvidenceItem(
                        evidence_type=EvidenceType.INTERRUPTION,
                        direction=Direction.INCREASE,
                        strength=strength,
                        period=period,
                        task_id=None,
                        cause_category=CauseCategory.EXTERNAL_INTERRUPTION,
                        voluntary=False,
                        evidence_text=quote,
                        source_field=field,
                    )
                )

        for evidence_type, (increase, decrease) in STATE_LEXICON.items():
            if not allow_today_behavior and evidence_type is not EvidenceType.SELF_EFFICACY:
                continue
            hits = self._state_hits(sentence, increase, decrease)
            for direction, span in hits:
                quote = self._quote(sentence, span, min_quote_chars)
                if quote is None:
                    continue
                items.append(
                    EvidenceItem(
                        evidence_type=evidence_type,
                        direction=direction,
                        strength=strength,
                        period=period,
                        task_id=None,
                        cause_category=None,
                        voluntary=None,
                        evidence_text=quote,
                        source_field=field,
                    )
                )

        # External interruption or illness/plan change wins over procrastination.
        if (
            allow_today_behavior
            and interruption_span is None
            and not self._has_external_cause(sentence)
        ):
            procrastination_span = self._procrastination_span(sentence)
            if procrastination_span is not None:
                quote = self._quote(
                    sentence, procrastination_span, min_quote_chars
                )
                if quote is not None:
                    items.append(
                        EvidenceItem(
                            evidence_type=EvidenceType.PROCRASTINATION,
                            direction=Direction.INCREASE,
                            strength=strength,
                            period=period,
                            task_id=None,
                            cause_category=self._procrastination_cause(sentence),
                            voluntary=True,
                            evidence_text=quote,
                            source_field=field,
                        )
                    )
        return items

    def _state_hits(
        self,
        sentence: str,
        increase: tuple[str, ...],
        decrease: tuple[str, ...],
    ) -> list[tuple[Direction, tuple[int, int]]]:
        decrease_spans: list[tuple[int, int]] = []
        for phrase in decrease:
            for span in _find_all(sentence, phrase):
                if _blocked_match(sentence, span, phrase):
                    continue
                decrease_spans.append(span)

        hits: dict[Direction, tuple[int, int]] = {}
        for span in decrease_spans:
            current = hits.get(Direction.DECREASE)
            if current is None or span[0] < current[0]:
                hits[Direction.DECREASE] = span

        for phrase in increase:
            for span in _find_all(sentence, phrase):
                if _blocked_match(sentence, span, phrase):
                    continue
                if _overlaps(span, decrease_spans):
                    continue
                direction = (
                    Direction.DECREASE
                    if _negated_short(sentence, span[0])
                    else Direction.INCREASE
                )
                current = hits.get(direction)
                if current is None or span[0] < current[0]:
                    hits[direction] = span

        ordered = [Direction.INCREASE, Direction.DECREASE]
        return [(direction, hits[direction]) for direction in ordered if direction in hits]

    def _interruption_span(self, sentence: str) -> tuple[int, int] | None:
        best: tuple[int, int] | None = None
        for phrase in INTERRUPTION:
            for span in _find_all(sentence, phrase):
                if _negated_short(sentence, span[0]):
                    continue
                if best is None or span[0] < best[0]:
                    best = span
        return best

    def _has_external_cause(self, sentence: str) -> bool:
        return _contains_any(sentence, EXTERNAL_CAUSE_GUARD)

    def _procrastination_span(self, sentence: str) -> tuple[int, int] | None:
        candidates: list[tuple[int, int]] = []
        for phrase in PROCRASTINATION:
            for span in _find_all(sentence, phrase):
                if self._procrastination_negated(sentence, span):
                    continue
                if self._nonvoluntary(sentence):
                    continue
                candidates.append(span)
        if not candidates:
            return None
        return min(candidates, key=lambda span: span[0])

    def _procrastination_negated(
        self, sentence: str, span: tuple[int, int]
    ) -> bool:
        before = sentence[max(0, span[0] - 16) : span[0]]
        for marker in _ZH_PROCRASTINATION_NEGATION:
            position = before.rfind(marker)
            if position == -1:
                continue
            tail = before[position + len(marker) :]
            if not any(contrast in tail for contrast in _CONTRAST_MARKERS):
                return True

        lowered_before = before.lower()
        last_match = None
        for match in _EN_PROCRASTINATION_NEGATION.finditer(lowered_before):
            last_match = match
        if last_match is not None:
            tail = lowered_before[last_match.end() :]
            if not any(marker in tail for marker in _EN_CONTRAST_MARKERS):
                return True

        after = sentence[span[1] : span[1] + 12]
        if any(marker in after for marker in _ZH_PROCRASTINATION_NEGATION):
            return True
        return re.match(r"\s*(not|no)\b", after.lower()) is not None

    def _nonvoluntary(self, sentence: str) -> bool:
        return _contains_any(sentence, NONVOLUNTARY_MARKERS)

    def _procrastination_cause(self, sentence: str) -> CauseCategory:
        if _contains_any(sentence, AVOIDANCE_MARKERS):
            return CauseCategory.AVOIDANCE
        if _contains_any(sentence, DISTRACTION_MARKERS):
            return CauseCategory.DISTRACTION
        if _contains_any(sentence, VOLITION_MARKERS):
            return CauseCategory.MOTIVATION_VOLITION
        return CauseCategory.AVOIDANCE

    def _quote(
        self,
        sentence: str,
        span: tuple[int, int],
        min_quote_chars: int,
    ) -> str | None:
        max_chars = 460
        if len(sentence) <= max_chars:
            quote = sentence
        else:
            keyword_length = span[1] - span[0]
            start = max(0, span[0] - (max_chars - keyword_length) // 2)
            end = min(len(sentence), start + max_chars)
            start = max(0, end - max_chars)
            quote = sentence[start:end].strip()
        if len(quote) < min_quote_chars:
            return None
        return quote
