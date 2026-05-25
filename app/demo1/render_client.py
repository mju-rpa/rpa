"""
로컬 PC → Render 배포 FastAPI 로 HTTP 요청.

.env:
  RENDER_SERVICE_URL=https://YOUR-SERVICE.onrender.com
  RENDER_LOG_INGEST_KEY=...  (Render Environment와 동일)

※ 로그가 Render 대시보드로 날아가는 경로는 HTTP API가 아니라 logging 입니다.
   demo1_log() → app/log/workflow_log.py → logging root
   → app/log/configure.py 의 RenderForwardHandler
   → app/log/render_forward.py POST /log/ingest  ← 여기서 로그 전송
   (run_cli --target render 실행 전 setup_logging() 호출 필요)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

import requests

from app.demo1.log_helper import demo1_log

SampleName = Literal["normal", "high_risk"]
SourceName = Literal["fixture", "input_json", "api"]


def render_base_url() -> str:
    url = os.getenv("RENDER_SERVICE_URL", "").strip().rstrip("/")
    if not url:
        raise ValueError(
            "RENDER_SERVICE_URL 이 비어 있습니다. .env 에 Render Web Service URL을 넣으세요."
        )
    return url


def _timeout_sec() -> int:
    return int(os.getenv("DEMO1_RENDER_TIMEOUT_SEC", "180"))


def post_demo1_collect(
    sample: SampleName = "normal",
    source: SourceName = "fixture",
    *,
    image_path: Path | None = None,
    audio_path: Path | None = None,
) -> dict[str, Any]:
    """
    Render 에 배포된 POST /demo1/collect 호출.
    (이 HTTP 응답 본문은 API 결과이며, workflow 로그와는 별개입니다.)
    """
    url = f"{render_base_url()}/demo1/collect"
    params = {"sample": sample, "source": source}
    demo1_log("SUCCESS", "render/api", f"POST {url} params={params}")

    files = None
    if image_path and image_path.is_file():
        files = files or {}
        files["image"] = (image_path.name, image_path.read_bytes(), "application/octet-stream")
    if audio_path and audio_path.is_file():
        files = files or {}
        files["audio"] = (audio_path.name, audio_path.read_bytes(), "application/octet-stream")

    resp = requests.post(url, params=params, files=files, timeout=_timeout_sec())
    if resp.status_code != 200:
        demo1_log("ERROR", "render/api", f"collect status={resp.status_code} body={resp.text[:400]}")
        resp.raise_for_status()
    data = resp.json()
    demo1_log("SUCCESS", "render/api", f"collect ok patient={data.get('patient_name')}")
    return data


def post_demo1_pipeline(
    sample: SampleName = "normal",
    source: SourceName = "fixture",
    *,
    run_agentic: bool = True,
) -> dict[str, Any]:
    """Render 에 배포된 POST /demo1/pipeline 호출."""
    url = f"{render_base_url()}/demo1/pipeline"
    params = {
        "sample": sample,
        "source": source,
        "run_agentic": str(run_agentic).lower(),
    }
    demo1_log("SUCCESS", "render/api", f"POST {url} params={params}")

    resp = requests.post(url, params=params, timeout=_timeout_sec())
    if resp.status_code != 200:
        demo1_log("ERROR", "render/api", f"pipeline status={resp.status_code} body={resp.text[:400]}")
        resp.raise_for_status()
    data = resp.json()
    stage = (data.get("pipeline") or {}).get("workflow_stage", "no_pipeline")
    demo1_log("SUCCESS", "render/api", f"pipeline ok stage={stage}")
    return data


def post_analyze_on_render(analyze_request: dict[str, Any]) -> dict[str, Any]:
    """Render POST /analyze — Agentic 전체 파이프라인(리포트 포함)."""
    url = f"{render_base_url()}/analyze"
    demo1_log("SUCCESS", "render/api", f"POST {url} patient={analyze_request.get('환자명')}")
    resp = requests.post(url, json=analyze_request, timeout=_timeout_sec())
    if resp.status_code != 200:
        demo1_log("ERROR", "render/api", f"analyze status={resp.status_code} body={resp.text[:400]}")
        resp.raise_for_status()
    return resp.json()


def save_render_api_snapshot(
    label: str,
    payload: dict[str, Any],
    *,
    subdir: str = "render_calls",
) -> Path:
    """Render API 응답을 로컬 output/demo1/ 에 백업 (Render 서버 output_dir 와 별개)."""
    from datetime import datetime

    base = Path(__file__).resolve().parent.parent.parent / "output" / "demo1" / subdir
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = base / f"{ts}_{label}"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "render_response.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    demo1_log("SUCCESS", "render/snapshot", f"saved {path}")
    return path
