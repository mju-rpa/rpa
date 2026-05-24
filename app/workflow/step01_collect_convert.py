"""Stage 1: OCR/STT 결과 → AnalyzeRequest (RPA 수집·변환)."""

from app.agentic_ai.schema.models import AnalyzeRequest


def collect_convert(req: AnalyzeRequest) -> dict:
    return {
        "request": req,
        "stt_text": req.stt_text,
        "ocr_text": req.ocr_text,
    }
