import pytest
from app.consult.ocr.api.schema.schema import ConfidenceResult, Medicine, OcrResponse


def test_confidence_result_final_is_average():
    c = ConfidenceResult(llm_score=0.8, rule_score=0.6, final=0.7)
    assert c.final == pytest.approx(0.7)


def test_confidence_result_low_fields_default_empty():
    c = ConfidenceResult(llm_score=0.9, rule_score=0.9, final=0.9)
    assert c.low_fields == []
