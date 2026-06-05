import asyncio
import logging
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.consult.ocr.api.schema.schema import ALLOWED_EXTENSIONS, DiagnosisPipelineResult, DiagnosisResponse, OcrPipelineResult, OcrResponse
from app.consult.ocr.core.config import ocr_config
from app.consult.ocr.core.extractor import GeminiDiagnosisExtractor, GeminiExtractor, OpenAIDiagnosisExtractor, OpenAIExtractor
from app.consult.ocr.core.pipeline import DiagnosisPipeline, OCRPipeline
from app.consult.ocr.agents.validator import DiagnosisLLMValidator, OcrLLMValidator

logger = logging.getLogger(__name__)

_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}

_pipeline: OCRPipeline | None = None
_diagnosis_pipeline: DiagnosisPipeline | None = None


def get_pipeline() -> OCRPipeline:
    global _pipeline
    if _pipeline is None:
        if ocr_config.extractor_type == "openai":
            extractor = OpenAIExtractor(
                api_key=ocr_config.openai_api_key,
                model=ocr_config.openai_model,
            )
        else:
            extractor = GeminiExtractor(
                api_key=ocr_config.gemini_api_key,
                model=ocr_config.gemini_model,
            )
        validator = OcrLLMValidator(api_key=ocr_config.openai_api_key, model=ocr_config.openai_model)
        _pipeline = OCRPipeline(
            extractor=extractor,
            validator=validator,
            retry_threshold=ocr_config.retry_threshold,
            hitl_threshold=ocr_config.hitl_threshold,
        )
    return _pipeline


def get_diagnosis_pipeline() -> DiagnosisPipeline:
    global _diagnosis_pipeline
    if _diagnosis_pipeline is None:
        if ocr_config.extractor_type == "openai":
            extractor = OpenAIDiagnosisExtractor(
                api_key=ocr_config.openai_api_key,
                model=ocr_config.openai_model,
            )
        else:
            extractor = GeminiDiagnosisExtractor(
                api_key=ocr_config.gemini_api_key,
                model=ocr_config.gemini_model,
            )
        diagnosis_validator = DiagnosisLLMValidator(api_key=ocr_config.openai_api_key, model=ocr_config.openai_model)
        _diagnosis_pipeline = DiagnosisPipeline(
            extractor=extractor,
            validator=diagnosis_validator,
            retry_threshold=ocr_config.retry_threshold,
            hitl_threshold=ocr_config.hitl_threshold,
        )
    return _diagnosis_pipeline


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


async def run_pipeline(file: UploadFile) -> OcrPipelineResult:
    contents = await file.read()
    ext = validate_file(file.filename, len(contents))
    try:
        pipeline = get_pipeline()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="OCR 초기화 실패: GEMINI_API_KEY 또는 OCR 설정을 확인해주세요",
        )
    result = await asyncio.to_thread(pipeline.run, contents, _MIME_MAP[ext])
    logger.info(
        "OCR 완료 - 환자: %s, 약품 수: %d, 상태: %s, 신뢰도: %.2f",
        result.data.patient_name, len(result.data.medicines),
        result.status, result.confidence.score,
    )
    return result


def to_diagnosis_text(result: DiagnosisResponse) -> str:
    lines = []
    if result.patient_name:
        lines.append(f"환자명: {result.patient_name}")
    if result.birth_date:
        lines.append(f"생년월일: {result.birth_date}")
    if result.diagnosis_name:
        lines.append(f"진단명: {result.diagnosis_name}")
    if result.department:
        lines.append(f"진료과: {result.department}")
    if result.hospital_name:
        lines.append(f"병원명: {result.hospital_name}")
    if result.doctor_name:
        lines.append(f"담당의: {result.doctor_name}")
    if result.diagnosis_date:
        lines.append(f"진단일: {result.diagnosis_date}")
    if result.purpose:
        lines.append(f"발급목적: {result.purpose}")
    return "\n".join(lines)


async def run_diagnosis_pipeline(file: UploadFile) -> DiagnosisPipelineResult:
    contents = await file.read()
    ext = validate_file(file.filename, len(contents))
    try:
        pipeline = get_diagnosis_pipeline()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="진단서 OCR 초기화 실패: GEMINI_API_KEY 또는 OCR 설정을 확인해주세요",
        )
    result = await asyncio.to_thread(pipeline.run, contents, _MIME_MAP[ext])
    logger.info(
        "진단서 OCR 완료 - 환자: %s, 진단명: %s, 상태: %s, 신뢰도: %.2f",
        result.data.patient_name, result.data.diagnosis_name,
        result.status, result.confidence.score,
    )
    return result


async def extract_from_upload(file: UploadFile) -> OcrResponse:
    """기존 호환성 — OcrResponse만 필요한 호출처에서 사용."""
    pipeline_result = await run_pipeline(file)
    return pipeline_result.data


async def extract_text_from_upload(file: UploadFile) -> str:
    result = await extract_from_upload(file)
    return to_text(result)
