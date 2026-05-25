"""
팀원 consult 패키지가 노출한 HTTP API만 호출 (내부 extractor/transcriber 직접 import 금지).

- POST /ocr/extract   → GeminiExtractor (consult/ocr)
- POST /stt/transcribe → Transcriber (consult/stt, TRANSCRIBER_TYPE 등 .env 반영)
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

import requests

from app.consult.ocr.api.schema.schema import OcrResponse
from app.consult.stt.api.schema.schema import TranscribeResponse
from app.demo2.log_helper import demo2_log

_OCR_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}

Mode = Literal["http", "inprocess"]


def resolve_base_url(mode: Mode, base_url: str | None) -> str:
    if mode == "inprocess":
        return "inprocess"
    if base_url:
        return base_url.rstrip("/")
    return os.getenv("DEMO2_BASE_URL", os.getenv("RENDER_SERVICE_URL", "http://127.0.0.1:8000")).rstrip(
        "/"
    )


def _timeout() -> int:
    return int(os.getenv("DEMO2_HTTP_TIMEOUT_SEC", "300"))


def _post_http(url: str, file_field: str, path: Path, mime: str) -> dict:
    demo2_log("SUCCESS", "http", f"POST {url} file={path.name}")
    with path.open("rb") as f:
        resp = requests.post(
            url,
            files={file_field: (path.name, f, mime)},
            timeout=_timeout(),
        )
    if resp.status_code != 200:
        demo2_log("ERROR", "http", f"{url} status={resp.status_code} body={resp.text[:500]}")
        resp.raise_for_status()
    return resp.json()


def _post_inprocess(path: str, file_field: str, upload_path: Path, mime: str) -> dict:
    from fastapi.testclient import TestClient

    from app.main import app

    demo2_log("SUCCESS", "inprocess", f"POST {path} file={upload_path.name}")
    data = upload_path.read_bytes()
    client = TestClient(app)
    resp = client.post(path, files={file_field: (upload_path.name, data, mime)})
    if resp.status_code != 200:
        demo2_log("ERROR", "inprocess", f"{path} status={resp.status_code} body={resp.text[:500]}")
        resp.raise_for_status()
    return resp.json()


def call_ocr_extract(image_path: Path, *, mode: Mode = "http", base_url: str = "") -> OcrResponse:
    ext = image_path.suffix.lower()
    mime = _OCR_MIME.get(ext, "application/octet-stream")
    if mode == "inprocess":
        raw = _post_inprocess("/ocr/extract", "file", image_path, mime)
    else:
        raw = _post_http(f"{base_url}/ocr/extract", "file", image_path, mime)
    return OcrResponse(**raw)


def call_stt_transcribe(audio_path: Path, *, mode: Mode = "http", base_url: str = "") -> TranscribeResponse:
    if mode == "inprocess":
        raw = _post_inprocess("/stt/transcribe", "file", audio_path, "application/octet-stream")
    else:
        raw = _post_http(f"{base_url}/stt/transcribe", "file", audio_path, "application/octet-stream")
    return TranscribeResponse(**raw)


def call_consult_parallel(
    image_path: Path,
    audio_path: Path,
    *,
    mode: Mode = "http",
    base_url: str = "",
) -> tuple[OcrResponse, TranscribeResponse]:
    """OCR·STT API 병렬 호출 (input-process 와 동일한 consult 엔드포인트)."""
    demo2_log("SUCCESS", "consult", f"parallel mode={mode} base={base_url or 'inprocess'}")
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_ocr = pool.submit(call_ocr_extract, image_path, mode=mode, base_url=base_url)
        fut_stt = pool.submit(call_stt_transcribe, audio_path, mode=mode, base_url=base_url)
        ocr = fut_ocr.result()
        stt = fut_stt.result()
    demo2_log(
        "SUCCESS",
        "consult",
        f"done ocr_meds={len(ocr.medicines)} stt_len={len(stt.text)} segments={len(stt.segments)}",
    )
    return ocr, stt
