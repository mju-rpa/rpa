"""consult 수집 결과 → Agentic AI 인계용 자연어·JSON."""
import json
from typing import Any

from app.agentic_ai.schema.models import AnalyzeRequest
from app.demo1.consult_collect import ConsultCollectResult, SttCollectResult


def stt_to_dialogue_text(stt: SttCollectResult) -> str:
    if stt.segments:
        return "\n".join(
            f"{seg.get('speaker', 'unknown')}: {seg.get('text', '')}"
            for seg in stt.segments
            if seg.get("text")
        )
    return stt.text


def build_handoff_natural(collected: ConsultCollectResult) -> str:
    """사람·LLM이 읽기 쉬운 단일 문서."""
    lines = [
        f"# Consult handoff (sample={collected.sample}, source={collected.source})",
        "",
        "## STT (진료 대화)",
        stt_to_dialogue_text(collected.stt) or "(없음)",
        "",
        "## OCR (약봉투)",
        collected.ocr_natural or "(없음)",
    ]
    return "\n".join(lines)


def build_handoff_json(collected: ConsultCollectResult) -> dict[str, Any]:
    """구조화 인계 — OcrResponse·STT segments 보존."""
    return {
        "meta": {
            "sample": collected.sample,
            "source": collected.source,
            "patient_name": collected.patient_name,
        },
        "consult": {
            "stt": {
                "text": collected.stt.text,
                "language": collected.stt.language,
                "duration_sec": collected.stt.duration_sec,
                "segments": collected.stt.segments,
                "source": collected.stt.source,
            },
            "ocr": collected.ocr.model_dump(),
        },
        "agentic_flat": {
            "stt_text": stt_to_dialogue_text(collected.stt),
            "ocr_text": collected.ocr_natural,
        },
    }


def build_analyze_request(
    collected: ConsultCollectResult,
    *,
    patient_id: str = "",
    환자명: str = "",
    알림매체: str = "none",
    hidl_enabled: bool = False,
    hidl_approved: bool | None = None,
) -> AnalyzeRequest:
    """Agentic AI POST /analyze 와 동일 스키마."""
    return AnalyzeRequest(
        patient_id=patient_id,
        환자명=환자명 or collected.patient_name,
        알림매체=알림매체,  # type: ignore[arg-type]
        stt_text=stt_to_dialogue_text(collected.stt),
        ocr_text=collected.ocr_natural,
        hidl_enabled=hidl_enabled,
        hidl_approved=hidl_approved,
    )


def handoff_json_pretty(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)
