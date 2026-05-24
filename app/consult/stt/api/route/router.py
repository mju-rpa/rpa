import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

# Directory 정리하면서 import 위치가 변경되었습니다.
# 아래는 기존 위치
"""
from app.stt.api.schemas import ALLOWED_EXTENSIONS, TranscribeResponse
from app.stt.core.config import stt_config
from app.stt.core.transcriber import ClovaSpeechTranscriber, OpenAIWhisperTranscriber, RemoteWhisperTranscriber, WhisperTranscriber
"""

# 이제부터 바뀐 위치
from app.consult.stt.api.schema.schema import ALLOWED_EXTENSIONS, TranscribeResponse
from app.consult.stt.core.config import stt_config
from app.consult.stt.core.transcriber import ClovaSpeechTranscriber, OpenAIWhisperTranscriber, RemoteWhisperTranscriber, WhisperTranscriber

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stt", tags=["stt"])

logger.info("Transcriber 타입: %s", stt_config.transcriber_type)
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
else:  # "local" (default)
    transcriber = WhisperTranscriber(
        model_size=stt_config.model_size,
        language=stt_config.language,
        device=stt_config.device,
        compute_type=stt_config.compute_type,
    )


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(file: UploadFile):
    logger.info("요청 수신 - 파일명: %s", file.filename)

    if not file.filename:
        logger.warning("파일명 없음 - 400 반환")
        raise HTTPException(status_code=400, detail="파일명이 필요합니다")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning("지원하지 않는 확장자: %s - 400 반환", ext)
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식: {ext}")

    contents = await file.read()
    file_size_mb = len(contents) / (1024 * 1024)
    logger.info("파일 읽기 완료 - 크기: %.2fMB", file_size_mb)

    if len(contents) > stt_config.max_file_size_bytes:
        logger.warning("파일 크기 초과: %.2fMB - 413 반환", file_size_mb)
        raise HTTPException(status_code=413, detail="파일 크기가 150MB를 초과합니다")

    suffix = ext if ext else ".wav"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(contents)
        tmp.close()
        logger.info("임시 파일 저장 완료: %s", tmp.name)
        result = transcriber.transcribe(tmp.name)
    except Exception as e:
        logger.error("전사 실패: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="전사 중 오류가 발생했습니다")
    finally:
        os.unlink(tmp.name)
        logger.debug("임시 파일 삭제: %s", tmp.name)

    logger.info("전사 성공 - 텍스트: %s", result.text)
    return TranscribeResponse(
        text=result.text,
        language=result.language,
        duration=result.duration,
        segments=[
            {"speaker": s.speaker, "text": s.text, "start": s.start, "end": s.end}
            for s in result.segments
        ],
    )