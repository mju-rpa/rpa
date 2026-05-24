import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from app.ocr.schema.models import ALLOWED_EXTENSIONS, OcrResponse
from app.ocr.core.config import ocr_config
from app.ocr.core.extractor import GeminiExtractor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["ocr"])

extractor: GeminiExtractor | None = None

_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}


@router.post("/extract", response_model=OcrResponse)
async def extract_medicine(file: UploadFile):
    logger.info("요청 수신 - 파일명: %s", file.filename)
    global extractor

    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 필요합니다")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식: {ext}")

    contents = await file.read()
    file_size_mb = len(contents) / (1024 * 1024)
    logger.info("파일 읽기 완료 - 크기: %.2fMB", file_size_mb)

    if len(contents) > ocr_config.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="파일 크기가 20MB를 초과합니다")

    try:
        if extractor is None:
            logger.info("GeminiExtractor 초기화 중 (model=%s)", ocr_config.gemini_model)
            try:
                extractor = GeminiExtractor(
                    api_key=ocr_config.gemini_api_key,
                    model=ocr_config.gemini_model,
                )
            except Exception:
                raise HTTPException(
                    status_code=503,
                    detail="OCR 초기화 실패: GEMINI_API_KEY 또는 OCR 설정을 확인해주세요",
                )
        result = extractor.extract(contents, _MIME_MAP[ext])
    except Exception as e:
        logger.error("OCR 실패: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="OCR 처리 중 오류가 발생했습니다")

    logger.info("OCR 성공 - 환자: %s, 약품 수: %d", result.patient_name, len(result.medicines))
    return result
