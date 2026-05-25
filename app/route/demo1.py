"""
Demo1 HTTP: consult API 수집 → 인계 비교 → (선택) Agentic 파이프라인.

[Render에 배포된 경우 로그]
  demo1_log() → stdout → Render 대시보드 Logs (별도 forward 불필요)

[로컬 PC에서 Render API를 호출하는 경우 로그]
  app/demo1/render_client.py 가 HTTP 요청
  demo1_log() → RenderForwardHandler → POST /log/ingest (로그 전송 구간)
"""
import json
import shutil
import tempfile
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.agentic_ai.schema.models import AnalyzeRequest
from app.demo1.consult_collect import collect_consult
from app.demo1.handoff import build_analyze_request, build_handoff_json, build_handoff_natural
from app.demo1.persist import save_demo1_run
from app.demo1.log_helper import demo1_log
from app.workflow.run_pipeline import run_pipeline

router = APIRouter(prefix="/demo1", tags=["demo1"])

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_OUTPUT_DIR = _BASE_DIR / "output"
_INPUT_SAMPLES = {
    "normal": _BASE_DIR / "input" / "sample_input.json",
    "high_risk": _BASE_DIR / "input" / "sample_input_high_risk.json",
}


def _analyze_request_from_sample(collected, sample: Literal["normal", "high_risk"]) -> AnalyzeRequest:
    inp = json.loads(_INPUT_SAMPLES[sample].read_text(encoding="utf-8"))
    hidl = sample == "high_risk"
    return build_analyze_request(
        collected,
        patient_id=inp.get("patient_id", ""),
        환자명=inp.get("환자명", collected.patient_name),
        알림매체=inp.get("알림매체", "none"),
        hidl_enabled=hidl,
        hidl_approved=None if hidl else None,
    )


@router.post("/collect")
async def demo1_collect(
    sample: Literal["normal", "high_risk"] = Query("normal"),
    source: Literal["fixture", "input_json", "api"] = Query(
        "fixture",
        description="fixture=키 없이 fixtures+input, api=POST /ocr·/stt (파일 선택 업로드)",
    ),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
):
    """
    consult 단계 수집 + 자연어/JSON 인계물 생성.
    결과: output/demo1/{timestamp}_{sample}/
    """
    image_path: Path | None = None
    audio_path: Path | None = None
    tmp_dir: Path | None = None

    try:
        if source == "api" and ((image and image.filename) or (audio and audio.filename)):
            tmp_dir = Path(tempfile.mkdtemp(prefix="demo1_"))
            if image and image.filename:
                image_path = tmp_dir / image.filename
                image_path.write_bytes(await image.read())
            if audio and audio.filename:
                audio_path = tmp_dir / audio.filename
                audio_path.write_bytes(await audio.read())

        collected = collect_consult(
            sample,
            source=source,
            image_path=image_path,
            audio_path=audio_path,
        )
        req = _analyze_request_from_sample(collected, sample)
        out_dir = save_demo1_run(collected, analyze_request=req)

        return {
            "output_dir": str(out_dir),
            "sample": sample,
            "source": collected.source,
            "patient_name": collected.patient_name,
            "stt_source": collected.stt.source,
            "handoff_natural_preview": build_handoff_natural(collected)[:800],
            "handoff_json": build_handoff_json(collected),
            "analyze_request": req.model_dump(),
        }
    except Exception as e:
        demo1_log("ERROR", "collect", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        if tmp_dir and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/pipeline")
def demo1_pipeline(
    sample: Literal["normal", "high_risk"] = Query("normal"),
    source: Literal["fixture", "input_json", "api"] = Query("fixture"),
    run_agentic: bool = Query(True, description="True면 AnalyzeRequest로 run_pipeline 실행"),
):
    """
  fixture/input_json: 파일 업로드 없이 수집 후 Agentic 실행.
  api: collect와 동일하나 업로드는 /demo1/collect 에서 — pipeline은 fixture 권장.
    """
    if source == "api":
        raise HTTPException(
            status_code=400,
            detail="api 소스는 POST /demo1/collect (image/audio 업로드) 사용 후 "
            "analyze_request.json 으로 POST /analyze 하세요. 또는 source=fixture",
        )

    collected = collect_consult(sample, source=source)
    req = _analyze_request_from_sample(collected, sample)
    pipeline_result = None
    if run_agentic:
        demo1_log("SUCCESS", "pipeline", f"run_pipeline sample={sample}")
        pipeline_result = run_pipeline(req, _OUTPUT_DIR)

    out_dir = save_demo1_run(collected, analyze_request=req, pipeline_result=pipeline_result)
    body: dict = {
        "output_dir": str(out_dir),
        "sample": sample,
        "source": collected.source,
        "analyze_request": req.model_dump(),
    }
    if pipeline_result is not None:
        body["pipeline"] = pipeline_result
    return body
