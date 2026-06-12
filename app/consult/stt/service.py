import asyncio
import logging
import os
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.consult.stt.api.schema.schema import ALLOWED_EXTENSIONS, SttPipelineResult, TranscribeResponse
from app.consult.stt.core.config import stt_config
from app.consult.stt.core.pipeline import STTPipeline
from app.consult.stt.core.transcriber import (
    ClovaSpeechTranscriber,
    OpenAIWhisperTranscriber,
    RemoteWhisperTranscriber,
    WhisperTranscriber,
)
from app.consult.stt.agents.validator import SttLLMValidator

logger = logging.getLogger(__name__)

_pipeline: STTPipeline | None = None


def get_pipeline() -> STTPipeline:
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    if stt_config.transcriber_type == "openai":
        transcriber = OpenAIWhisperTranscriber(
            api_key=stt_config.openai_api_key,
            language=stt_config.language,
        )
    elif stt_config.transcriber_type == "clova":
        transcriber = ClovaSpeechTranscriber(
            invoke_url=stt_config.clova_invoke_url,
            secret_key=stt_config.clova_secret_key,
            speaker_count_min=stt_config.clova_speaker_count_min,
            speaker_count_max=stt_config.clova_speaker_count_max,
        )
    elif stt_config.transcriber_type == "remote":
        transcriber = RemoteWhisperTranscriber(
            server_url=stt_config.whisper_server_url,
            language=stt_config.language,
        )
    else:
        transcriber = WhisperTranscriber(
            model_size=stt_config.model_size,
            language=stt_config.language,
            device=stt_config.device,
            compute_type=stt_config.compute_type,
        )

    validator = SttLLMValidator(api_key=stt_config.openai_api_key)
    _pipeline = STTPipeline(
        transcriber=transcriber,
        validator=validator,
        retry_threshold=stt_config.retry_threshold,
        hitl_threshold=stt_config.hitl_threshold,
    )
    return _pipeline


def validate_file(filename: str, size: int) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"STT: 지원하지 않는 파일 형식 {ext}")
    if size > stt_config.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="STT: 파일 크기 초과")
    return ext


async def run_pipeline(file: UploadFile) -> SttPipelineResult:
    logger.info("[STT] 시작 - 파일명: %s", file.filename)
    contents = await file.read()
    ext = validate_file(file.filename, len(contents))
    suffix = ext if ext else ".wav"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(contents)
        tmp.close()
        pipeline = get_pipeline()
        result = await asyncio.to_thread(pipeline.run, tmp.name)
    finally:
        os.unlink(tmp.name)
    logger.info("[STT] 완료 - 텍스트 길이: %d, 상태: %s, 신뢰도: %.2f",
                len(result.data.text), result.status, result.confidence.score)
    return result


def to_text(data: TranscribeResponse) -> str:
    if data.segments:
        return "\n".join(f"{s.speaker}: {s.text}" for s in data.segments)
    return data.text


async def transcribe_upload(file: UploadFile) -> str:
    """기존 호환성 — 텍스트만 필요한 호출처에서 사용."""
    result = await run_pipeline(file)
    return to_text(result.data)


async def transcribe_upload_raw(file: UploadFile) -> SttPipelineResult:
    """개발 테스트용 — PipelineResult 원본 반환."""
    return await run_pipeline(file)
