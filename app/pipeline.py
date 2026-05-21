from pathlib import Path

from app.agents import run_medical_agent, run_self_reflection
from app.config import llm_provider_label, uses_mock_llm
from app.notifications import (
    build_notification_plan,
    build_rpa_actions,
    format_report,
)
from app.scoring import compute_risk_score
from app.schemas import AnalyzeRequest


def run_pipeline(req: AnalyzeRequest, output_dir: Path) -> dict:
    use_mock = uses_mock_llm()

    # Step 1 — RPA 수집 (to_be: UiPath STT/OCR)
    stt = req.stt_text
    ocr = req.ocr_text

    # Step 2 — Agentic AI 분석
    draft = run_medical_agent(stt, ocr, use_mock)

    # Step 2b — Self-Reflection (Critic 루프)
    analysis, reflection_logs = run_self_reflection(stt, ocr, draft, use_mock)

    if req.환자명:
        analysis["환자명"] = req.환자명

    # Step 3 — 점수 평가
    risk = compute_risk_score(stt, ocr, analysis)

    contact = req.연락처.model_dump()
    notification = build_notification_plan(req.알림매체, analysis, contact, risk)
    rpa_actions = build_rpa_actions(req.알림매체, risk, str(output_dir))
    report_text = format_report(analysis, risk)

    # UiPath·조원 시연용 — Agentic AI 단계가 눈에 보이는 타임라인
    agent_trace = [
        {
            "step": 1,
            "role": "RPA",
            "agent": "Data Collector",
            "action": "STT/OCR 텍스트 수집 (데모: JSON 파일)",
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
        agent_trace.append(
            {
                "step": 2 + log["round"],
                "role": "Agentic AI",
                "agent": "Critic Agent (Self-Reflection)",
                "action": "복약 스케줄 검증",
                "detail": log["critic_feedback"],
                "revised": log["revised"],
            }
        )
    agent_trace.append(
        {
            "step": 10,
            "role": "Agentic AI",
            "agent": "Risk Scorer",
            "action": "복약 위험도 점수 산출",
            "detail": f"{risk['최종점수']}점, 재검토={risk['재검토_필요']}",
        }
    )
    agent_trace.append(
        {
            "step": 11,
            "role": "Agentic AI",
            "agent": "Notification Planner",
            "action": "RPA 실행 계획 생성",
            "detail": notification.get("message", ""),
        }
    )
    for i, action in enumerate(rpa_actions, start=1):
        agent_trace.append(
            {
                "step": 11 + i,
                "role": "RPA",
                "agent": "Executor (planned)",
                "action": action,
                "detail": "to_be: UiPath가 JSON 기반 실행",
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = analysis.get("환자명", "patient").replace(" ", "_")
    report_path = output_dir / f"{safe_name}_복약리포트.txt"
    report_path.write_text(report_text, encoding="utf-8")

    reflection_lines = [
        f"Round {log['round']}: {log['critic_feedback']} (revised={log['revised']})"
        for log in reflection_logs
    ]
    agent_trace_lines = [
        f"[{t['step']}] {t['agent']} | {t['action']}"
        for t in agent_trace
    ]

    return {
        "workflow_stage": "completed",
        "llm_provider": llm_provider_label(),
        # UiPath For Each 없이 Write Line만으로 시연 가능 (영문 flat 키)
        "patient_name": analysis.get("환자명", ""),
        "final_score": risk["최종점수"],
        "needs_review": risk["재검토_필요"],
        "reflection_summary": "\n".join(reflection_lines),
        "agent_trace_summary": "\n".join(agent_trace_lines),
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
