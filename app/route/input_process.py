import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.params import File

from app.agentic_ai.schema.models import AnalyzeRequest
from app.consult.ocr.api.schema.schema import DiagnosisPipelineResult, OcrPipelineResult
from app.consult.ocr.service import run_diagnosis_pipeline, run_pipeline as ocr_run_pipeline, to_diagnosis_text, to_text as ocr_to_text
from app.consult.stt.api.schema.schema import SttPipelineResult
from app.consult.stt.service import run_pipeline as stt_run_pipeline, to_text as stt_to_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/input-process", tags=["input-process"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "input_process"


@router.post("")
async def input_process(
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    diagnosis: Optional[UploadFile] = File(None),
    patient_id: str = Form(""),
    환자명: str = Form(""),
    알림매체: Literal["kakao", "google_calendar", "sms", "none"] = Form("none"),
):
    """STT + OCR(약봉투) + OCR(진단서) 병렬 처리 → AnalyzeRequest JSON."""
    has_audio = bool(audio and audio.filename)
    has_image = bool(image and image.filename)
    has_diagnosis = bool(diagnosis and diagnosis.filename)
    if not has_audio and not has_image and not has_diagnosis:
        raise HTTPException(status_code=400, detail="audio, image, diagnosis 중 하나 이상 필요합니다")

    stt_result, ocr_result, diagnosis_result = await asyncio.gather(
        stt_run_pipeline(audio) if has_audio else asyncio.sleep(0, result=None),
        ocr_run_pipeline(image) if has_image else asyncio.sleep(0, result=None),
        run_diagnosis_pipeline(diagnosis) if has_diagnosis else asyncio.sleep(0, result=None),
    )

    stt_text = stt_to_text(stt_result.data) if stt_result else ""
    ocr_text = ocr_to_text(ocr_result.data) if ocr_result else ""
    diagnosis_text = to_diagnosis_text(diagnosis_result.data) if diagnosis_result else ""
    response = AnalyzeRequest(
        patient_id=patient_id,
        환자명=환자명,
        알림매체=알림매체,
        stt_text=stt_text,
        ocr_text=ocr_text,
        diagnosis_text=diagnosis_text,
        hitl=_hitl_block(stt_result, ocr_result, diagnosis_result),
    )
    await asyncio.to_thread(_save_results, patient_id or 환자명 or "unknown", stt_text, ocr_text, diagnosis_text, response)
    return response


# ── helpers ──────────────────────────────────────────────────────────────────

def _hitl_block(
    stt: SttPipelineResult | None,
    ocr: OcrPipelineResult | None,
    diagnosis: DiagnosisPipelineResult | None,
) -> dict:
    return {
        key: {"status": r.status, "retried": r.retried, "confidence": asdict(r.confidence)}
        for key, r in (("stt", stt), ("ocr", ocr), ("diagnosis", diagnosis))
        if r is not None
    }


def _save_results(label: str, stt_text: str, ocr_text: str, diagnosis_text: str, response: AnalyzeRequest) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = OUTPUT_DIR / f"{ts}_{label.replace(' ', '_')}"
    folder.mkdir(parents=True, exist_ok=True)
    if stt_text:
        (folder / "stt_raw.txt").write_text(stt_text, encoding="utf-8")
    if ocr_text:
        (folder / "ocr_raw.txt").write_text(ocr_text, encoding="utf-8")
    if diagnosis_text:
        (folder / "diagnosis_raw.txt").write_text(diagnosis_text, encoding="utf-8")
    (folder / "response.json").write_text(
        json.dumps(response.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
