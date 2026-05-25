"""demo1 실행 결과를 output/demo1/ 에 저장."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.agentic_ai.schema.models import AnalyzeRequest
from app.demo1.consult_collect import ConsultCollectResult
from app.demo1.final_report import build_final_report
from app.demo1.handoff import (
    build_analyze_request,
    build_handoff_json,
    build_handoff_natural,
    handoff_json_pretty,
)
from app.demo1.log_helper import demo1_log

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_ROOT = _BASE_DIR / "output" / "demo1"


def save_demo1_run(
    collected: ConsultCollectResult,
    *,
    analyze_request: AnalyzeRequest | None = None,
    pipeline_result: dict[str, Any] | None = None,
) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = OUTPUT_ROOT / f"{ts}_{collected.sample}"
    folder.mkdir(parents=True, exist_ok=True)

    handoff_natural = build_handoff_natural(collected)
    handoff_json = build_handoff_json(collected)
    (folder / "handoff_natural.txt").write_text(handoff_natural, encoding="utf-8")
    (folder / "handoff_json.json").write_text(
        handoff_json_pretty(handoff_json),
        encoding="utf-8",
    )

    req = analyze_request or build_analyze_request(
        collected,
        patient_id="",
        환자명=collected.patient_name,
        hidl_enabled=collected.sample == "high_risk",
        hidl_approved=None if collected.sample == "high_risk" else None,
    )
    (folder / "analyze_request.json").write_text(
        json.dumps(req.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary: dict[str, Any] = {
        "sample": collected.sample,
        "source": collected.source,
        "output_dir": str(folder),
        "patient_name": collected.patient_name,
        "stt_source": collected.stt.source,
        "ocr_medicine_count": len(collected.ocr.medicines),
        "handoff_files": [
            "handoff_natural.txt",
            "handoff_json.json",
            "analyze_request.json",
        ],
    }
    if pipeline_result is not None:
        summary["pipeline"] = {
            "workflow_stage": pipeline_result.get("workflow_stage"),
            "final_score": pipeline_result.get("final_score")
            or (pipeline_result.get("risk_score") or {}).get("최종점수"),
            "report_file": pipeline_result.get("report_file"),
        }
        (folder / "pipeline_result.json").write_text(
            json.dumps(pipeline_result, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        summary["handoff_files"].append("pipeline_result.json")

    final_text = build_final_report(collected, pipeline_result)
    (folder / "final_report.txt").write_text(final_text, encoding="utf-8")
    summary["handoff_files"].append("final_report.txt")
    if pipeline_result and pipeline_result.get("report_text"):
        summary["final_report"] = {
            "workflow_stage": pipeline_result.get("workflow_stage"),
            "risk_score": (pipeline_result.get("risk_score") or {}).get("최종점수"),
            "report_file": pipeline_result.get("report_file"),
        }

    (folder / "demo1_result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    demo1_log("SUCCESS", "persist", f"saved {folder}")
    return folder
