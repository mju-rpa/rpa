import json
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from app.agentic_ai.schema.models import AnalyzeRequest
from app.workflow.run_pipeline import run_pipeline

router = APIRouter(tags=["analyze"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output"


@router.post("/analyze")
def analyze(body: AnalyzeRequest):
    return run_pipeline(body, OUTPUT_DIR)


@router.post("/analyze/file")
async def analyze_file(file: UploadFile = File(...)):
    """UiPath/RPA: JSON 파일 업로드 후 분석 (multipart)."""
    raw = await file.read()
    data = json.loads(raw.decode("utf-8"))
    req = AnalyzeRequest(**data)
    return run_pipeline(req, OUTPUT_DIR)
