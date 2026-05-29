import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.params import File

from app.agentic_ai.schema.models import AnalyzeRequest
from app.consult.ocr.service import extract_text_from_upload
from app.consult.stt.service import transcribe_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/input-process", tags=["input-process"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "input_process"


@router.post("")
async def input_process(
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    patient_id: str = Form(""),
    환자명: str = Form(""),
    알림매체: Literal["kakao", "google_calendar", "sms", "none"] = Form("none"),
):
    """STT + OCR 병렬 처리 → AnalyzeRequest JSON."""
    has_audio = bool(audio and audio.filename)
    has_image = bool(image and image.filename)
    if not has_audio and not has_image:
        raise HTTPException(status_code=400, detail="audio 또는 image 중 하나 이상 필요합니다")

    tasks = {}
    if has_audio:
        tasks["stt"] = transcribe_upload(audio)
    if has_image:
        tasks["ocr"] = extract_text_from_upload(image)

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    result_map = dict(zip(tasks.keys(), results))
    for val in result_map.values():
        if isinstance(val, Exception):
            raise val

    stt_text = result_map.get("stt", "")
    ocr_text = result_map.get("ocr", "")
    response = AnalyzeRequest(
        patient_id=patient_id,
        환자명=환자명,
        알림매체=알림매체,
        stt_text=stt_text,
        ocr_text=ocr_text,
    )
    await asyncio.to_thread(_save_results, patient_id or 환자명 or "unknown", stt_text, ocr_text, response)
    return response


def _save_results(label: str, stt_text: str, ocr_text: str, response: AnalyzeRequest) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = OUTPUT_DIR / f"{ts}_{label.replace(' ', '_')}"
    folder.mkdir(parents=True, exist_ok=True)
    if stt_text:
        (folder / "stt_raw.txt").write_text(stt_text, encoding="utf-8")
    if ocr_text:
        (folder / "ocr_raw.txt").write_text(ocr_text, encoding="utf-8")
    (folder / "response.json").write_text(
        json.dumps(response.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
