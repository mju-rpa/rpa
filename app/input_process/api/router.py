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

from app.schemas import AnalyzeRequest
from app.ocr.api.schemas import ALLOWED_EXTENSIONS as OCR_EXTENSIONS
from app.ocr.core.config import ocr_config
from app.ocr.core.extractor import GeminiExtractor
from app.stt.api.schemas import ALLOWED_EXTENSIONS as STT_EXTENSIONS
from app.stt.core.config import stt_config
from app.stt.core.transcriber import (
    ClovaSpeechTranscriber,
    OpenAIWhisperTranscriber,
    RemoteWhisperTranscriber,
    WhisperTranscriber,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/input-process", tags=["input-process"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "input_process"

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
elif stt_config.transcriber_type == "remote":
    _stt_transcriber = RemoteWhisperTranscriber(
        server_url=stt_config.whisper_server_url,
        language=stt_config.language,
    )
else:  # "local" (default)
    _stt_transcriber = WhisperTranscriber(
        model_size=stt_config.model_size,
        language=stt_config.language,
        device=stt_config.device,
        compute_type=stt_config.compute_type,
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
    print(f"[STT] 시작 - 파일명: {file.filename}", flush=True)
    logger.info("[STT] 시작 - 파일명: %s", file.filename)
    ext = Path(file.filename).suffix.lower()
    if ext not in STT_EXTENSIONS:
        logger.warning("[STT] 지원하지 않는 확장자: %s", ext)
        raise HTTPException(status_code=400, detail=f"STT: 지원하지 않는 파일 형식 {ext}")
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    print(f"[STT] 파일 읽기 완료 - {size_mb:.2f}MB", flush=True)
    if len(contents) > stt_config.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="STT: 파일 크기 초과")
    suffix = ext if ext else ".wav"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(contents)
        tmp.close()
        print(f"[STT] 변환 중 (transcriber={stt_config.transcriber_type})...", flush=True)
        result = await asyncio.to_thread(_stt_transcriber.transcribe, tmp.name)
    except Exception as e:
        print(f"[STT] 예외 발생: {type(e).__name__}: {e}", flush=True)
        raise
    finally:
        os.unlink(tmp.name)
    if result.segments:
        text = "\n".join(f"{s.speaker}: {s.text}" for s in result.segments)
    else:
        text = result.text
    print(f"[STT] 완료 - {len(text)}자, 언어={result.language}", flush=True)
    return text


async def _run_ocr(file: UploadFile) -> str:
    logger.info("[OCR] 시작 - 파일명: %s", file.filename)
    ext = Path(file.filename).suffix.lower()
    if ext not in OCR_EXTENSIONS:
        logger.warning("[OCR] 지원하지 않는 확장자: %s", ext)
        raise HTTPException(status_code=400, detail=f"OCR: 지원하지 않는 파일 형식 {ext}")
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    logger.info("[OCR] 파일 읽기 완료 - %.2fMB", size_mb)
    if len(contents) > ocr_config.max_file_size_bytes:
        logger.warning("[OCR] 파일 크기 초과: %.2fMB", size_mb)
        raise HTTPException(status_code=413, detail="OCR: 파일 크기 초과")
    logger.info("[OCR] Gemini 추출 중 (model=%s)...", ocr_config.gemini_model)
    result = await asyncio.to_thread(_ocr_extractor.extract, contents, _MIME_MAP[ext])
    logger.info("[OCR] 완료 - 환자=%s, 약품 수=%d", result.patient_name, len(result.medicines))
    ocr_text = _ocr_to_text(result)
    logger.debug("[OCR] 변환 텍스트:\n%s", ocr_text)
    return ocr_text


@router.post("")
async def input_process(
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    patient_id: str = Form(""),
    환자명: str = Form(""),
    알림매체: Literal["kakao", "google_calendar", "sms", "none"] = Form("none"),
):
    """STT + OCR 병렬 처리 → AnalyzeRequest 형태로 반환 (sample_input.json 포맷)."""
    audio_filename = audio.filename if audio else None
    image_filename = image.filename if image else None
    print(f"[input-process] 요청 수신 - 환자={환자명}, audio={audio_filename!r}, image={image_filename!r}", flush=True)
    logger.info("[input-process] 요청 수신 - 환자=%s, audio=%s, image=%s",
                환자명 or "(미입력)", audio_filename, image_filename)

    has_audio = bool(audio and audio.filename)
    has_image = bool(image and image.filename)
    print(f"[input-process] has_audio={has_audio}, has_image={has_image}", flush=True)
    logger.info("[input-process] 파일 감지 - has_audio=%s, has_image=%s", has_audio, has_image)

    if not has_audio and not has_image:
        logger.warning("[input-process] audio/image 모두 없음 - 400 반환")
        raise HTTPException(status_code=400, detail="audio 또는 image 중 하나 이상 필요합니다")

    tasks = {}
    if has_audio:
        print(f"[input-process] STT 태스크 등록: {audio_filename}", flush=True)
        tasks["stt"] = _run_stt(audio)
    if has_image:
        print(f"[input-process] OCR 태스크 등록: {image_filename}", flush=True)
        tasks["ocr"] = _run_ocr(image)

    print(f"[input-process] 병렬 처리 시작 - 작업: {list(tasks.keys())}", flush=True)
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    result_map = dict(zip(tasks.keys(), results))

    for key, val in result_map.items():
        print(f"[input-process] {key} 결과 타입={type(val).__name__}, 값={repr(val)[:200]}", flush=True)
        if isinstance(val, Exception):
            print(f"[input-process] {key.upper()} 실패: {val}", flush=True)
            raise val

    stt_text = result_map.get("stt", "")
    ocr_text = result_map.get("ocr", "")
    logger.info("[input-process] 완료 - stt=%d자, ocr=%d자", len(stt_text), len(ocr_text))

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
    safe_label = label.replace(" ", "_")
    folder = OUTPUT_DIR / f"{ts}_{safe_label}"
    folder.mkdir(parents=True, exist_ok=True)

    if stt_text:
        (folder / "stt_raw.txt").write_text(stt_text, encoding="utf-8")
        logger.info("[input-process] STT 원본 저장: %s", folder / "stt_raw.txt")

    if ocr_text:
        (folder / "ocr_raw.txt").write_text(ocr_text, encoding="utf-8")
        logger.info("[input-process] OCR 원본 저장: %s", folder / "ocr_raw.txt")

    response_path = folder / "response.json"
    response_path.write_text(
        json.dumps(response.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("[input-process] 응답 바디 저장: %s", response_path)
