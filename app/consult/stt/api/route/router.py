import logging

from fastapi import APIRouter, HTTPException, UploadFile

from app.consult.stt.api.schema.schema import SpeakerSegment, TranscribeResponse
from app.consult.stt.service import transcribe_upload_raw

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stt", tags=["[개발 테스트용 - 사용 X] STT"])


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(file: UploadFile):
    try:
        result = await transcribe_upload_raw(file)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("전사 실패: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="전사 중 오류가 발생했습니다")
    return TranscribeResponse(
        text=result.text,
        language=result.language,
        duration=result.duration,
        segments=[
            SpeakerSegment(speaker=s.speaker, text=s.text, start=s.start, end=s.end)
            for s in result.segments
        ],
    )
