"""
consult 공개 API(/ocr/extract, /stt/transcribe) 호출.
app/consult/* 내부 코드는 수정·직접 import 하지 않음.
"""
from pathlib import Path

from app.consult.ocr.api.schema.schema import OcrResponse
from app.consult.stt.api.schema.schema import TranscribeResponse
from app.demo1.log_helper import demo1_log

_OCR_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}


def _test_client():
    """순환 import 방지: 호출 시점에만 app.main 로드."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def post_ocr_extract(image_path: Path) -> OcrResponse:
    ext = image_path.suffix.lower()
    mime = _OCR_MIME.get(ext, "application/octet-stream")
    demo1_log("SUCCESS", "api/ocr", f"POST /ocr/extract file={image_path.name}")
    with image_path.open("rb") as f:
        data = f.read()
    client = _test_client()
    resp = client.post(
        "/ocr/extract",
        files={"file": (image_path.name, data, mime)},
    )
    if resp.status_code != 200:
        demo1_log("ERROR", "api/ocr", f"status={resp.status_code} body={resp.text[:500]}")
        resp.raise_for_status()
    return OcrResponse(**resp.json())


def post_stt_transcribe(audio_path: Path) -> TranscribeResponse:
    demo1_log("SUCCESS", "api/stt", f"POST /stt/transcribe file={audio_path.name}")
    with audio_path.open("rb") as f:
        data = f.read()
    client = _test_client()
    resp = client.post(
        "/stt/transcribe",
        files={"file": (audio_path.name, data, "application/octet-stream")},
    )
    if resp.status_code != 200:
        demo1_log("ERROR", "api/stt", f"status={resp.status_code} body={resp.text[:500]}")
        resp.raise_for_status()
    return TranscribeResponse(**resp.json())
