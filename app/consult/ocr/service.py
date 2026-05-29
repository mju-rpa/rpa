import asyncio
import logging
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.consult.ocr.api.schema.schema import ALLOWED_EXTENSIONS, OcrResponse
from app.consult.ocr.core.config import ocr_config
from app.consult.ocr.core.extractor import GeminiExtractor

logger = logging.getLogger(__name__)

_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}

_extractor: GeminiExtractor | None = None


def get_extractor() -> GeminiExtractor:
    global _extractor
    if _extractor is None:
        _extractor = GeminiExtractor(
            api_key=ocr_config.gemini_api_key,
            model=ocr_config.gemini_model,
        )
    return _extractor


def to_text(result: OcrResponse) -> str:
    lines = []
    if result.patient_name:
        lines.append(f"환자명: {result.patient_name}")
    if result.prescribed_date:
        lines.append(f"처방일자: {result.prescribed_date}")
    if result.hospital_name:
        lines.append(f"병원명: {result.hospital_name}")
    for i, m in enumerate(result.medicines, start=1):
        parts = [p for p in [m.dosage, m.frequency, m.timing] if p]
        line = f"약품 {i}: {m.name}"
        if parts:
            line += f" - {' '.join(parts)}"
        if m.caution:
            line += f"  ※ {m.caution}"
        lines.append(line)
    if result.general_caution:
        lines.append(f"일반주의사항: {result.general_caution}")
    return "\n".join(lines)


def validate_file(filename: str, size: int) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"OCR: 지원하지 않는 파일 형식 {ext}")
    if size > ocr_config.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="OCR: 파일 크기 초과")
    return ext


async def extract_from_upload(file: UploadFile) -> OcrResponse:
    contents = await file.read()
    ext = validate_file(file.filename, len(contents))
    try:
        extractor = get_extractor()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="OCR 초기화 실패: GEMINI_API_KEY 또는 OCR 설정을 확인해주세요",
        )
    result = await asyncio.to_thread(extractor.extract, contents, _MIME_MAP[ext])
    logger.info("OCR 성공 - 환자: %s, 약품 수: %d", result.patient_name, len(result.medicines))
    return result


async def extract_text_from_upload(file: UploadFile) -> str:
    result = await extract_from_upload(file)
    return to_text(result)
