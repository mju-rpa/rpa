"""Stage 5–6: 알림 계획 · RPA 리포트 · UiPath flat 응답."""

from pathlib import Path

from app.config import llm_provider_label
from app.notification.plan import build_notification_plan
from app.rpa.python.report import format_report, save_report_file
from app.rpa.uipath.actions import build_rpa_actions
from app.rpa.uipath.response import flatten_for_uipath


def build_agent_trace(
    stt: str,
    ocr: str,
    analysis: dict,
    reflection_logs: list[dict],
    risk: dict,
    notification: dict,
    rpa_actions: list[str],
    hidl_trace: dict | None = None,
) -> list[dict]:
    trace = [
        {
            "step": 1,
            "role": "RPA",
            "agent": "Data Collector",
            "action": "STT/OCR 텍스트 수집",
            "detail": f"stt {len(stt)}자, ocr {len(ocr)}자",
        },
        {
            "step": 2,
            "role": "Agentic AI",
            "agent": "Medical Agent",
            "action": "진료 요약 + 복약 JSON 초안 생성",
            "detail": analysis.get("진료요약", ""),
        },
    ]
    for log in reflection_logs:
        trace.append(
            {
                "step": 2 + log["round"],
                "role": "Agentic AI",
                "agent": "Critic Agent (Self-Reflection)",
                "action": "복약 스케줄 검증",
                "detail": log["critic_feedback"],
                "revised": log["revised"],
            }
        )
    trace.append(
        {
            "step": 8,
            "role": "Agentic AI",
            "agent": "Risk Evaluator",
            "action": "DB 기반 위험도 군집 분류",
            "detail": f"군집={risk.get('군집', '일반')}, HITL={risk.get('HITL_필요', False)}",
        }
    )
    if hidl_trace:
        trace.append(hidl_trace)
    trace.append(
        {
            "step": 11,
            "role": "Agentic AI",
            "agent": "Notification Planner",
            "action": "알림·RPA 실행 계획 생성",
            "detail": notification.get("message", ""),
        }
    )
    for i, action in enumerate(rpa_actions, start=1):
        trace.append(
            {
                "step": 11 + i,
                "role": "RPA",
                "agent": "Executor",
                "action": action,
                "detail": "Python 리포트 저장 완료 · UiPath 액션은 actions 목록 참고",
            }
        )
    return trace


def rpa_notify_output(
    req,
    analysis: dict,
    reflection_logs: list[dict],
    risk: dict,
    stt: str,
    ocr: str,
    output_dir: Path,
    hidl_status: str = "skipped",
    hidl_trace: dict | None = None,
) -> dict:
    contact = req.연락처.model_dump()
    notification = build_notification_plan(req.알림매체, analysis, contact, risk)
    rpa_actions = build_rpa_actions(req.알림매체, risk, str(output_dir))
    report_text = format_report(analysis, risk)
    report_path = save_report_file(analysis, report_text, output_dir)

    agent_trace = build_agent_trace(
        stt,
        ocr,
        analysis,
        reflection_logs,
        risk,
        notification,
        rpa_actions,
        hidl_trace=hidl_trace,
    )
    reflection_lines = [
        f"Round {log['round']}: {log['critic_feedback']} (revised={log['revised']})"
        for log in reflection_logs
    ]
    agent_trace_lines = [f"[{t['step']}] {t['agent']} | {t['action']}" for t in agent_trace]
    flat = flatten_for_uipath(
        analysis,
        risk,
        reflection_lines,
        agent_trace_lines,
        report_text,
        str(report_path),
        hidl_status=hidl_status,
    )

    return {
        "workflow_stage": "completed",
        "llm_provider": llm_provider_label(),
        **flat,
        "reflection_lines": reflection_lines,
        "agent_trace_lines": agent_trace_lines,
        "agent_trace": agent_trace,
        "analysis": analysis,
        "risk_score": risk,
        "reflection_logs": reflection_logs,
        "notification_plan": notification,
        "rpa_actions": rpa_actions,
        "report_text": report_text,
        "report_file": str(report_path),
    }
