from unittest.mock import MagicMock
import pytest
from app.consult.ocr.api.schema.schema import Medicine, OcrResponse
from app.consult.ocr.core.pipeline import OCRPipeline


def _make_ocr_response(with_medicines=True):
    medicines = [Medicine(name="타이레놀", dosage="1정", frequency="1일 3회")] if with_medicines else []
    return OcrResponse(medicines=medicines, hospital_name="서울병원", prescribed_date="2026-05-30")


def test_pipeline_ok_high_confidence():
    extractor = MagicMock()
    extractor.extract.return_value = (_make_ocr_response(), 0.9)

    pipeline = OCRPipeline(extractor=extractor, retry_threshold=0.65, hitl_threshold=0.5)
    result = pipeline.run(b"fake_image", "image/jpeg")

    assert result.status == "ok"
    assert result.retried is False
    extractor.extract.assert_called_once_with(b"fake_image", "image/jpeg", retry=False)


def test_pipeline_retries_on_low_confidence():
    good_response = _make_ocr_response()
    extractor = MagicMock()
    extractor.extract.side_effect = [
        (_make_ocr_response(with_medicines=False), 0.3),
        (good_response, 0.85),
    ]

    pipeline = OCRPipeline(extractor=extractor, retry_threshold=0.65, hitl_threshold=0.5)
    result = pipeline.run(b"fake_image", "image/jpeg")

    assert result.retried is True
    assert extractor.extract.call_count == 2


def test_pipeline_hitl_when_retry_still_low():
    extractor = MagicMock()
    extractor.extract.return_value = (_make_ocr_response(with_medicines=False), 0.2)

    pipeline = OCRPipeline(extractor=extractor, retry_threshold=0.65, hitl_threshold=0.5)
    result = pipeline.run(b"fake_image", "image/jpeg")

    assert result.status == "hitl_required"
    assert result.retried is True
