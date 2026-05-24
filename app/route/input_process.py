import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.params import File

from app.agentic_ai.schema.models import AnalyzeRequest
from app.consult.ocr.core.config import ocr_config
from app.consult.ocr.core.extractor import GeminiExtractor
from app.consult.ocr.api.schema.schema import ALLOWED_EXTENSIONS as OCR_EXTENSIONS
from app.consult.stt.core.config import stt_config
from app.consult.stt.core.transcriber import (
    ClovaSpeechTranscriber,
    OpenAIWhisperTranscriber,
    RemoteWhisperTranscriber,
    WhisperTranscriber,
)
from app.consult.stt.api.schema.schema import ALLOWED_EXTENSIONS as STT_EXTENSIONS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/input-process", tags=["input-process"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "input_process"

_ocr_extractor: GeminiExtractor | None = None

_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}

_stt_transcriber = None


def _get_stt_transcriber():
    global _stt_transcriber
    if _stt_transcriber is not None:
        return _stt_transcriber
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
    elif stt_config.transcriber_type == "remote":
        _stt_transcriber = RemoteWhisperTranscriber(
            server_url=stt_config.whisper_server_url,
            language=stt_config.language,
        )
    else:
        _stt_transcriber = WhisperTranscriber(
            model_size=stt_config.model_size,
            language=stt_config.language,
            device=stt_config.device,
            compute_type=stt_config.compute_type,
        )
    return _stt_transcriber


def _get_ocr_extractor() -> GeminiExtractor:
    global _ocr_extractor
    if _ocr_extractor is None:
        _ocr_extractor = GeminiExtractor(
            api_key=ocr_config.gemini_api_key,
            model=ocr_config.gemini_model,
        )
    return _ocr_extractor


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
    print(f"[STT] 시작 - 파일명: {file.filename}", flush=True)
    logger.info("[STT] 시작 - 파일명: %s", file.filename)
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
        transcriber = _get_stt_transcriber()
        result = await asyncio.to_thread(transcriber.transcribe, tmp.name)
    finally:
        os.unlink(tmp.name)
    if result.segments:
        return "\n".join(f"{s.speaker}: {s.text}" for s in result.segments)
    return result.text


async def _run_ocr(file: UploadFile) -> str:
    ext = Path(file.filename).suffix.lower()
    if ext not in OCR_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"OCR: 지원하지 않는 파일 형식 {ext}")
    contents = await file.read()
    if len(contents) > ocr_config.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="OCR: 파일 크기 초과")
    try:
        extractor = _get_ocr_extractor()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="OCR 초기화 실패: GEMINI_API_KEY 또는 OCR 설정을 확인해주세요",
        )
    result = await asyncio.to_thread(extractor.extract, contents, _MIME_MAP[ext])
    return _ocr_to_text(result)


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
        tasks["stt"] = _run_stt(audio)
    if has_image:
        tasks["ocr"] = _run_ocr(image)

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
    _save_results(patient_id or 환자명 or "unknown", stt_text, ocr_text, response)
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
