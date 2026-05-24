import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import llm_provider_label, uses_mock_llm

router = APIRouter(tags=["health"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SAMPLE_INPUT = BASE_DIR / "input" / "sample_input.json"


@router.get("/")
def root():
    return {
        "service": "atlas-medical-demo",
        "endpoints": {
            "health": "/health",
            "analyze": "POST /analyze",
            "analyze_file": "POST /analyze/file",
            "input_process": "POST /input-process (STT+OCR 병렬 → AnalyzeRequest)",
            "sample": "GET /sample-input",
            "ocr": "POST /ocr/extract",
            "stt": "POST /stt/transcribe",
        },
    }


@router.get("/health")
def health():
    return {
        "status": "ok",
        "llm_provider": llm_provider_label(),
        "uses_mock": uses_mock_llm(),
        "hint": "Set LLM_PROVIDER=mock|ollama|gemini|openai_compatible",
    }


@router.get("/sample-input")
def sample_input():
    if not SAMPLE_INPUT.exists():
        return JSONResponse({"error": "sample_input.json not found"}, status_code=404)
    return json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
