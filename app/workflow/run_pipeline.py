from pathlib import Path

from app.agentic_ai.schema.models import AnalyzeRequest
from app.log.workflow_log import workflow_log
from app.workflow.step01_collect_convert import collect_convert
from app.workflow.step02_agentic_analyze_reflect_score import agentic_analyze_reflect_score
from app.workflow.step03_hidl_human_gate import hidl_human_gate
from app.workflow.step04_rpa_notify_output import build_agent_trace, rpa_notify_output


def run_pipeline(req: AnalyzeRequest, output_dir: Path) -> dict:
    """
    step01_collect_convert → step02_agentic → step03_hidl → step04_rpa_notify_output
    """
    patient = req.환자명 or req.patient_id or "unknown"
    try:
        workflow_log("SUCCESS", "step01", f"collect_convert start patient={patient}")
        converted = collect_convert(req)
        stt = converted["stt_text"]
        ocr = converted["ocr_text"]
        workflow_log(
            "SUCCESS",
            "step01",
            f"collect_convert done stt={len(stt)}chars ocr={len(ocr)}chars",
        )

        workflow_log("SUCCESS", "step02", "agentic analyze + reflection + score start")
        agentic = agentic_analyze_reflect_score(stt, ocr, req.환자명)
        analysis = agentic["analysis"]
        reflection_logs = agentic["reflection_logs"]
        risk = agentic["risk"]
        workflow_log(
            "SUCCESS",
            "step02",
            f"agentic done score={risk['최종점수']} needs_review={risk['재검토_필요']}",
        )

        workflow_log("SUCCESS", "step03", "hidl gate start")
        hidl = hidl_human_gate(req, analysis, risk)
        decision = hidl["decision"]
        if hidl["blocked"]:
            workflow_log(
                "ADMIN",
                "step03",
                f"hidl blocked status={decision.status} | {decision.message}",
            )
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

        if decision.status in ("pending", "rejected"):
            workflow_log("ADMIN", "step03", decision.message)
        else:
            workflow_log("SUCCESS", "step03", f"hidl {decision.status}")

        workflow_log("SUCCESS", "step04", "rpa notify + report start")
        result = rpa_notify_output(
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
        workflow_log(
            "SUCCESS",
            "step04",
            f"completed report={result.get('report_file', '')}",
        )
        return result
    except Exception as exc:
        workflow_log("ERROR", "pipeline", f"patient={patient} | {exc!s}")
        raise
