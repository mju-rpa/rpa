import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

import os
print(f"[startup] TRANSCRIBER_TYPE={os.getenv('TRANSCRIBER_TYPE')}", flush=True)

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from app.config import LLM_PROVIDER, llm_provider_label, uses_mock_llm
from app.pipeline import run_pipeline
from app.input_process.api.router import router as input_process_router
from app.schemas import AnalyzeRequest

app = FastAPI(
    title="Atlas Medical Agentic AI API (Demo)",
    description="RPA(UiPath) ↔ Agentic AI 연동 데모. STT/OCR·알림 연동 구간은 to_be_generated.",
    version="0.1.0",
)

app.include_router(input_process_router)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
SAMPLE_INPUT = BASE_DIR / "data" / "sample_input.json"


@app.get("/")
def root():
    return {
        "service": "atlas-medical-demo",
        "endpoints": {
            "health": "/health",
            "analyze": "POST /analyze",
            "analyze_file": "POST /analyze/file",
            "input_process": "POST /input-process (STT+OCR 병렬 → AnalyzeRequest 조립)",
            "sample": "GET /sample-input",
        },
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm_provider": llm_provider_label(),
        "uses_mock": uses_mock_llm(),
        "hint": "Set LLM_PROVIDER=mock|ollama|gemini|openai_compatible",
    }


@app.get("/sample-input")
def sample_input():
    if not SAMPLE_INPUT.exists():
        return JSONResponse({"error": "sample_input.json not found"}, status_code=404)
    return json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))


@app.post("/analyze")
def analyze(body: AnalyzeRequest):
    result = run_pipeline(body, OUTPUT_DIR)
    return result


@app.post("/analyze/file")
async def analyze_file(file: UploadFile = File(...)):
    """UiPath/RPA: JSON 파일 업로드 후 분석 (multipart)."""
    raw = await file.read()
    data = json.loads(raw.decode("utf-8"))
    req = AnalyzeRequest(**data)
    return run_pipeline(req, OUTPUT_DIR)
