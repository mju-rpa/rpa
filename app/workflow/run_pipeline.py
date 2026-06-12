from pathlib import Path

from app.agentic_ai.schema.models import AnalyzeRequest
from app.log.workflow_log import workflow_log
from app.rpa.python.report import format_report, save_report_file
from app.workflow.step01_collect_convert import collect_convert
from app.workflow.step02_agentic_analyze_reflect_score import agentic_analyze_reflect_score
from app.workflow.step03_hidl_human_gate import hidl_human_gate
from app.workflow.step04_rpa_notify_output import build_agent_trace, rpa_notify_output


def run_pipeline(req: AnalyzeRequest, output_dir: Path) -> dict:
    """
    step01 → step02 → step03(HITL) → step04
    """
    patient = req.patient_name or req.환자명 or "unknown"
    try:
        # ── step01 ────────────────────────────────────────────
        workflow_log("SUCCESS", "step01", f"collect_convert start patient={patient}")
        converted = collect_convert(req)
        stt = converted["stt_text"]
        ocr = converted["ocr_text"]
        workflow_log(
            "SUCCESS", "step01",
            f"collect_convert done stt={len(stt)}chars ocr={len(ocr)}chars",
        )

        # ── step02: Agentic AI ────────────────────────────────
        workflow_log("SUCCESS", "step02", "agentic AI start")
        agentic = agentic_analyze_reflect_score(stt, ocr, req.patient_name or req.환자명, req.알림매체, getattr(req, "diagnosis_text", ""), getattr(req, "hitl", {}))

        stt_summary = agentic.get("stt_summary", {})
        ocr_data    = agentic.get("ocr_data", {})
        mismatch    = agentic.get("mismatch", {})
        risk        = agentic.get("risk", {})
        guidance    = agentic.get("guidance", {})

        # step03·04 호환용 구성
        analysis = {
            "환자명":         guidance.get("환자명", req.환자명 or ""),
            "진료요약":        stt_summary.get("상담_맥락", ""),
            "필수복약리스트":   ocr_data.get("약품_목록", []),
            "상호작용_경고":   ", ".join(guidance.get("주의사항", [])),
            "stt_ocr_불일치":  mismatch.get("불일치_목록", []),
        }

        군집 = risk.get("군집", "일반")
        hitl = risk.get("HITL_필요", False)
        risk_score = {
            "군집":       군집,
            "최종점수":   0 if 군집 == "위험" else 70 if 군집 == "주의" else 100,
            "재검토_필요": hitl,
            "재검토_사유": risk.get("HITL_메시지", ""),
            "분류_근거":   risk.get("분류_근거", []),
            "감점항목":    [],
        }

        workflow_log(
            "SUCCESS", "step02",
            f"agentic done 군집={risk.get('군집','일반')} "
            f"HITL={risk.get('HITL_필요', False)} "
            f"use_mock={agentic.get('use_mock', True)}",
        )

        # ── step03: HITL ──────────────────────────────────────
        workflow_log("SUCCESS", "step03", "hidl gate start")
        hidl = hidl_human_gate(req, analysis, risk_score)
        decision = hidl["decision"]

        if hidl["blocked"]:
            workflow_log(
                "ADMIN", "step03",
                f"hidl blocked status={decision.status} | {decision.message}",
            )
            report_text = format_report(analysis, risk_score)
            report_path = save_report_file(analysis, report_text, output_dir)
            agent_trace = build_agent_trace(
                stt, ocr, analysis, [], risk_score,
                {"message": decision.message}, [],
                hidl_trace=hidl["trace"],
            )
            return {
                "workflow_stage": "hidl_pending",
                "hidl":          {"status": decision.status, "message": decision.message},
                "stt_summary":    stt_summary,
                "ocr_data":       ocr_data,
                "mismatch":       mismatch,
                "risk":           risk,
                "guidance":       guidance,
                "analysis":       analysis,
                "risk_score":     risk_score,
                "agent_trace":    agent_trace,
                "patient_name":   analysis.get("환자명", ""),
                "report_text":    report_text,
                "report_file":    str(report_path),
            }

        if decision.status in ("pending", "rejected"):
            workflow_log("ADMIN", "step03", decision.message)
        else:
            workflow_log("SUCCESS", "step03", f"hidl {decision.status}")

        # ── step04 ────────────────────────────────────────────
        workflow_log("SUCCESS", "step04", "rpa notify + report start")
        result = rpa_notify_output(
            req, analysis, [], risk_score, stt, ocr, output_dir,
            hidl_status=decision.status,
            hidl_trace=hidl["trace"] if hidl["decision"].applied else None,
        )

        result["stt_summary"] = stt_summary
        result["ocr_data"]    = ocr_data
        result["mismatch"]    = mismatch
        result["risk"]        = risk
        result["guidance"]    = guidance

        workflow_log(
            "SUCCESS", "step04",
            f"completed report={result.get('report_file', '')}",
        )
        return result

    except Exception as exc:
        workflow_log("ERROR", "pipeline", f"patient={patient} | {exc!s}")
        raise
