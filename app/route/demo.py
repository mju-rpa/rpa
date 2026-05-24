"""터미널 run_standalone 대체 — FastAPI로 샘플 파이프라인 실행."""
import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.agentic_ai.schema.models import AnalyzeRequest
from app.log.workflow_log import workflow_log
from app.workflow.run_pipeline import run_pipeline

router = APIRouter(prefix="/demo", tags=["demo"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output"
_SAMPLES = {
    "normal": BASE_DIR / "input" / "sample_input.json",
    "high_risk": BASE_DIR / "input" / "sample_input_high_risk.json",
}


def _load_sample(name: Literal["normal", "high_risk"]) -> AnalyzeRequest:
    path = _SAMPLES[name]
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"sample not found: {path.name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if name == "high_risk":
        data["hidl_enabled"] = True
        data["hidl_approved"] = None
    return AnalyzeRequest(**data)


@router.post("/pipeline")
def demo_pipeline(
    sample: Literal["normal", "high_risk"] = Query(
        "normal", description="normal=김철수, high_risk=이영희+HIDL 대기"
    ),
):
    """POST /demo/pipeline?sample=normal | high_risk — run_standalone.py 대체."""
    req = _load_sample(sample)
    workflow_log("SUCCESS", "demo", f"pipeline start sample={sample} patient={req.환자명}")
    result = run_pipeline(req, OUTPUT_DIR)
    workflow_log(
        "SUCCESS",
        "demo",
        f"pipeline end stage={result.get('workflow_stage')} score={result.get('final_score', result.get('risk_score', {}).get('최종점수'))}",
    )
    return result
