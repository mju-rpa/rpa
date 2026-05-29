import asyncio
import logging
import os
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.consult.stt.api.schema.schema import ALLOWED_EXTENSIONS
from app.consult.stt.core.config import stt_config
from app.consult.stt.core.transcriber import (
    ClovaSpeechTranscriber,
    OpenAIWhisperTranscriber,
    RemoteWhisperTranscriber,
    WhisperTranscriber,
)

logger = logging.getLogger(__name__)

_transcriber = None


def get_transcriber():
    global _transcriber
    if _transcriber is not None:
        return _transcriber
    if stt_config.transcriber_type == "openai":
        _transcriber = OpenAIWhisperTranscriber(
            api_key=stt_config.openai_api_key,
            language=stt_config.language,
        )
    elif stt_config.transcriber_type == "clova":
        _transcriber = ClovaSpeechTranscriber(
            invoke_url=stt_config.clova_invoke_url,
            secret_key=stt_config.clova_secret_key,
            speaker_count_min=stt_config.clova_speaker_count_min,
            speaker_count_max=stt_config.clova_speaker_count_max,
        )
    elif stt_config.transcriber_type == "remote":
        _transcriber = RemoteWhisperTranscriber(
            server_url=stt_config.whisper_server_url,
            language=stt_config.language,
        )
    else:
        _transcriber = WhisperTranscriber(
            model_size=stt_config.model_size,
            language=stt_config.language,
            device=stt_config.device,
            compute_type=stt_config.compute_type,
        )
    return _transcriber


def validate_file(filename: str, size: int) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"STT: 지원하지 않는 파일 형식 {ext}")
    if size > stt_config.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="STT: 파일 크기 초과")
    return ext


async def transcribe_upload_raw(file: UploadFile):
    """TranscribeResult 원본 반환 (개발 테스트용 라우터에서 사용)."""
    logger.info("[STT] 시작 - 파일명: %s", file.filename)
    contents = await file.read()
    ext = validate_file(file.filename, len(contents))
    suffix = ext if ext else ".wav"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(contents)
        tmp.close()
        transcriber = get_transcriber()
        result = await asyncio.to_thread(transcriber.transcribe, tmp.name)
    finally:
        os.unlink(tmp.name)
    logger.info("[STT] 성공 - 텍스트 길이: %d", len(result.text))
    return result


async def transcribe_upload(file: UploadFile) -> str:
    logger.info("[STT] 시작 - 파일명: %s", file.filename)
    contents = await file.read()
    ext = validate_file(file.filename, len(contents))
    suffix = ext if ext else ".wav"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(contents)
        tmp.close()
        transcriber = get_transcriber()
        result = await asyncio.to_thread(transcriber.transcribe, tmp.name)
    finally:
        os.unlink(tmp.name)
    logger.info("[STT] 성공 - 텍스트 길이: %d", len(result.text))
    if result.segments:
        return "\n".join(f"{s.speaker}: {s.text}" for s in result.segments)
    return result.text
