import logging

from fastapi import APIRouter, UploadFile

from app.consult.ocr.api.schema.schema import OcrResponse
from app.consult.ocr.service import extract_from_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr", tags=["[개발 테스트용 - 사용 X] OCR"])


@router.post("/extract", response_model=OcrResponse)
async def extract_medicine(file: UploadFile):
    return await extract_from_upload(file)
