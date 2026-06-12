import pytest
from app.consult.stt.core.scorer import SttScorer
from app.consult.stt.core.transcriber import TranscriptionResult


def _make_result(text: str, duration: float = 10.0) -> TranscriptionResult:
    return TranscriptionResult(text=text, language="ko", duration=duration)


def test_rule_score_high_quality():
    result = _make_result("타이레놀 1정 식후 30분 복용하세요. 항생제도 함께 드세요.", duration=15.0)
    scorer = SttScorer()
    confidence = scorer.score(result, llm_score=0.8)
    assert confidence.rule_score == pytest.approx(1.0)
    assert confidence.final == pytest.approx(0.9)


def test_rule_score_short_text():
    result = _make_result("네.", duration=5.0)
    scorer = SttScorer()
    confidence = scorer.score(result, llm_score=0.5)
    assert "text_length" in confidence.low_fields
    assert confidence.rule_score < 0.5


def test_rule_score_no_medical_keywords():
    result = _make_result("안녕하세요 오늘 날씨가 좋네요 정말 좋습니다", duration=10.0)
    scorer = SttScorer()
    confidence = scorer.score(result, llm_score=0.7)
    assert "medical_keywords" in confidence.low_fields
