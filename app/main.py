from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

# consult 하위 OCR/STT 원본 import 경로 유지
from app.consult_alias import register_consult_import_alias

register_consult_import_alias()

import os

from app.log.configure import setup_logging

setup_logging()

print(f"[startup] TRANSCRIBER_TYPE={os.getenv('TRANSCRIBER_TYPE')}", flush=True)

from fastapi import FastAPI

from app.route.analyze import router as analyze_router
from app.route.demo import router as demo_router
from app.route.demo1 import router as demo1_router
from app.route.demo2 import router as demo2_router
from app.route.health import router as health_router
from app.route.input_process import router as input_process_router
from app.route.log_ingest import router as log_ingest_router
from app.ocr.route.router import router as ocr_router
from app.stt.route.router import router as stt_router

app = FastAPI(
    title="Atlas Medical Agentic AI API (Demo)",
    description="(OCR+STT) consult → Agentic AI → RPA 복약스케줄 자동화",
    version="0.3.0",
)

app.include_router(health_router)
app.include_router(analyze_router)
app.include_router(demo_router)
app.include_router(demo1_router)
app.include_router(demo2_router)
app.include_router(input_process_router)
app.include_router(log_ingest_router)
app.include_router(ocr_router)
app.include_router(stt_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
