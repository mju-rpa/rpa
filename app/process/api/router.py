import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.params import File

from app.pipeline import run_pipeline
from app.schemas import AnalyzeRequest, ContactInfo
from app.ocr.api.schemas import ALLOWED_EXTENSIONS as OCR_EXTENSIONS
from app.ocr.core.config import ocr_config
from app.ocr.core.extractor import GeminiExtractor
from app.stt.api.schemas import ALLOWED_EXTENSIONS as STT_EXTENSIONS
from app.stt.core.config import stt_config
from app.stt.core.transcriber import (
    ClovaSpeechTranscriber,
    OpenAIWhisperTranscriber,
    RemoteWhisperTranscriber,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/process", tags=["process"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output"

_ocr_extractor = GeminiExtractor(
    api_key=ocr_config.gemini_api_key,
    model=ocr_config.gemini_model,
)

_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}

if stt_config.transcriber_type == "openai":
    _stt_transcriber = OpenAIWhisperTranscriber(
        api_key=stt_config.openai_api_key,
        language=stt_config.language,
    )
elif stt_config.transcriber_type == "clova":
    _stt_transcriber = ClovaSpeechTranscriber(
        invoke_url=stt_config.clova_invoke_url,
        secret_key=stt_config.clova_secret_key,
        speaker_count_min=stt_config.clova_speaker_count_min,
        speaker_count_max=stt_config.clova_speaker_count_max,
    )
else:
    _stt_transcriber = RemoteWhisperTranscriber(
        server_url=stt_config.whisper_server_url,
        language=stt_config.language,
    )


def _ocr_to_text(result) -> str:
    lines = []
    if result.patient_name:
        lines.append(f"환자명: {result.patient_name}")
    if result.prescribed_date:
        lines.append(f"처방일자: {result.prescribed_date}")
    if result.hospital_name:
        lines.append(f"병원명: {result.hospital_name}")
    for i, m in enumerate(result.medicines, start=1):
        parts = [p for p in [m.dosage, m.frequency, m.timing] if p]
        detail = " ".join(parts)
        line = f"약품 {i}: {m.name}"
        if detail:
            line += f" - {detail}"
        if m.caution:
            line += f"  ※ {m.caution}"
        lines.append(line)
    if result.general_caution:
        lines.append(f"일반주의사항: {result.general_caution}")
    return "\n".join(lines)


async def _run_stt(file: UploadFile) -> str:
    ext = Path(file.filename).suffix.lower()
    if ext not in STT_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"STT: 지원하지 않는 파일 형식 {ext}")
    contents = await file.read()
    if len(contents) > stt_config.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="STT: 파일 크기 초과")
    suffix = ext if ext else ".wav"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(contents)
        tmp.close()
        result = await asyncio.to_thread(_stt_transcriber.transcribe, tmp.name)
    finally:
        os.unlink(tmp.name)
    logger.info("STT 완료 - %d자", len(result.text))
    return result.text


async def _run_ocr(file: UploadFile) -> str:
    ext = Path(file.filename).suffix.lower()
    if ext not in OCR_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"OCR: 지원하지 않는 파일 형식 {ext}")
    contents = await file.read()
    if len(contents) > ocr_config.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="OCR: 파일 크기 초과")
    result = await asyncio.to_thread(_ocr_extractor.extract, contents, _MIME_MAP[ext])
    logger.info("OCR 완료 - 환자: %s, 약품 수: %d", result.patient_name, len(result.medicines))
    return _ocr_to_text(result)


@router.post("/")
async def process(
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    patient_id: str = Form(""),
    환자명: str = Form(""),
    알림매체: Literal["kakao", "google_calendar", "sms", "none"] = Form("none"),
):
    """STT + OCR 병렬 처리 후 Agentic AI 분석까지 원스톱."""
    if not audio and not image:
        raise HTTPException(status_code=400, detail="audio 또는 image 중 하나 이상 필요합니다")

    tasks = {}
    if audio:
        tasks["stt"] = _run_stt(audio)
    if image:
        tasks["ocr"] = _run_ocr(image)

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    result_map = dict(zip(tasks.keys(), results))

    for key, val in result_map.items():
        if isinstance(val, Exception):
            raise val

    req = AnalyzeRequest(
        patient_id=patient_id,
        환자명=환자명,
        알림매체=알림매체,
        stt_text=result_map.get("stt", ""),
        ocr_text=result_map.get("ocr", ""),
    )

    return await asyncio.to_thread(run_pipeline, req, OUTPUT_DIR)
