from app.consult.ocr.api.schema.schema import (
    ConfidenceResult,
    OcrPipelineResult,
    OcrResponse,
)
from app.consult.stt.api.schema.schema import SttPipelineResult, TranscribeResponse
from app.route.input_process import hitl_block


def _ocr_result(status="hitl_required", final=0.42):
    return OcrPipelineResult(
        status=status,
        data=OcrResponse(),
        confidence=ConfidenceResult(
            llm_score=0.40, rule_score=0.44, final=final, low_fields=["dosage_frequency"]
        ),
        retried=True,
    )


def _stt_result(status="ok", final=0.70):
    return SttPipelineResult(
        status=status,
        data=TranscribeResponse(text="처방전 복약 안내", language="ko", duration=10.0),
        confidence=ConfidenceResult(
            llm_score=0.50, rule_score=0.90, final=final, low_fields=[]
        ),
        retried=False,
    )


def test_hitl_block_includes_only_provided_channels():
    block = hitl_block(ocr=_ocr_result(), stt=None)

    assert "ocr" in block
    assert "stt" not in block


def test_hitl_block_maps_status_retried_and_confidence():
    block = hitl_block(ocr=_ocr_result(status="hitl_required", final=0.42), stt=None)

    assert block["ocr"] == {
        "status": "hitl_required",
        "retried": True,
        "confidence": {
            "llm_score": 0.40,
            "rule_score": 0.44,
            "final": 0.42,
            "low_fields": ["dosage_frequency"],
        },
    }


def test_hitl_block_with_both_channels():
    block = hitl_block(ocr=_ocr_result(), stt=_stt_result())

    assert block["ocr"]["status"] == "hitl_required"
    assert block["stt"]["status"] == "ok"
    assert block["stt"]["retried"] is False
