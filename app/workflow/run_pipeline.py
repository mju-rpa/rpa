from pathlib import Path

from app.agentic_ai.schema.models import AnalyzeRequest
from app.workflow.step01_collect_convert import collect_convert
from app.workflow.step02_agentic_analyze_reflect_score import agentic_analyze_reflect_score
from app.workflow.step03_hidl_human_gate import hidl_human_gate
from app.workflow.step04_rpa_notify_output import build_agent_trace, rpa_notify_output


def run_pipeline(req: AnalyzeRequest, output_dir: Path) -> dict:
    """
    step01_collect_convert → step02_agentic → step03_hidl → step04_rpa_notify_output
    """
    converted = collect_convert(req)
    stt = converted["stt_text"]
    ocr = converted["ocr_text"]

    agentic = agentic_analyze_reflect_score(stt, ocr, req.환자명)
    analysis = agentic["analysis"]
    reflection_logs = agentic["reflection_logs"]
    risk = agentic["risk"]

    hidl = hidl_human_gate(req, analysis, risk)
    if hidl["blocked"]:
        agent_trace = build_agent_trace(
            stt,
            ocr,
            analysis,
            reflection_logs,
            risk,
            {"message": hidl["decision"].message},
            [],
            hidl_trace=hidl["trace"],
        )
        return {
            "workflow_stage": "hidl_pending",
            "hidl": {
                "status": hidl["decision"].status,
                "message": hidl["decision"].message,
            },
            "analysis": analysis,
            "risk_score": risk,
            "reflection_logs": reflection_logs,
            "agent_trace": agent_trace,
            "patient_name": analysis.get("환자명", ""),
            "final_score": risk["최종점수"],
            "needs_review": risk["재검토_필요"],
        }

    return rpa_notify_output(
        req,
        analysis,
        reflection_logs,
        risk,
        stt,
        ocr,
        output_dir,
        hidl_status=hidl["decision"].status,
        hidl_trace=hidl["trace"] if hidl["decision"].applied else None,
    )
