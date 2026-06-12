import pytest
from app.consult.ocr.api.schema.schema import ConfidenceResult, Medicine, OcrResponse
from app.consult.ocr.core.scorer import OcrScorer


def test_confidence_result_final_is_average():
    c = ConfidenceResult(llm_score=0.8, rule_score=0.6, final=0.7)
    assert c.final == pytest.approx(0.7)


def test_confidence_result_low_fields_default_empty():
    c = ConfidenceResult(llm_score=0.9, rule_score=0.9, final=0.9)
    assert c.low_fields == []


def _make_response(medicines=None, hospital=None, date=None):
    return OcrResponse(
        medicines=medicines or [],
        hospital_name=hospital,
        prescribed_date=date,
    )


def test_rule_score_full():
    medicines = [Medicine(name="타이레놀", dosage="1정", frequency="1일 3회")]
    resp = _make_response(medicines=medicines, hospital="서울병원", date="2026-05-30")
    scorer = OcrScorer()
    result = scorer.score(resp, llm_score=0.9)
    assert result.final == pytest.approx(0.9 * 0.5 + 1.0 * 0.5)
    assert result.rule_score == pytest.approx(1.0)


def test_rule_score_no_medicines():
    resp = _make_response()
    scorer = OcrScorer()
    result = scorer.score(resp, llm_score=0.5)
    assert result.rule_score == pytest.approx(0.0)
    assert "medicines" in result.low_fields


def test_rule_score_medicines_no_dosage():
    medicines = [Medicine(name="타이레놀")]
    resp = _make_response(medicines=medicines, hospital="서울병원")
    scorer = OcrScorer()
    result = scorer.score(resp, llm_score=0.7)
    assert result.rule_score == pytest.approx(0.7)  # 0.4 + 0.2 + 0.1(medicines_count)
