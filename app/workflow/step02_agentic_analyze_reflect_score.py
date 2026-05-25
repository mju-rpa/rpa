"""
Stage 2: Agentic AI 분석 · Self-Reflection · 위험도 점수 · CrewAI Multi-Agent

흐름:
  1. medical.py       → analysis 초안 생성
  2. self_reflection  → analysis 검증·수정
  3. risk.py          → risk 계산
  4. CrewAI           → analysis + risk 받아서 심화 분석
"""
from app.agentic_ai.agent.crewai_agents import run_crewai_pipeline
from app.agentic_ai.agent.medical import run_medical_agent
from app.agentic_ai.scoring.risk import compute_risk_score
from app.agentic_ai.self_reflection.loop import run_self_reflection
from app.config import uses_mock_llm


def agentic_analyze_reflect_score(
    stt: str,
    ocr: str,
    환자명: str = "",
    알림매체: str = "none",
) -> dict:
    use_mock = uses_mock_llm()

    # ── 1. 복약 초안 생성 ─────────────────────────────
    draft = run_medical_agent(stt, ocr, use_mock)

    # ── 2. Self-Reflection ────────────────────────────
    analysis, reflection_logs = run_self_reflection(stt, ocr, draft, use_mock)

    if 환자명:
        analysis["환자명"] = 환자명

    # ── 3. 위험도 계산 ────────────────────────────────
    risk = compute_risk_score(stt, ocr, analysis)

    if use_mock:
        # mock 모드: CrewAI 없이 analysis + risk 그대로 반환
        return {
            "analysis":        analysis,
            "reflection_logs": reflection_logs,
            "risk":            risk,
            "action_plan":     {},
            "use_mock":        True,
        }

    # ── 4. CrewAI Multi-Agent ─────────────────────────
    # analysis, risk 전달 (이미 처리된 데이터)
    crew_result = run_crewai_pipeline(
        analysis=analysis,
        risk=risk,
        알림매체=알림매체,
    )

    # CrewAI 결과로 analysis 보강
    analysis["환자맞춤_복약안내"] = crew_result["guidance"].get("환자맞춤_복약안내", "")
    analysis["핵심_주의사항"]    = crew_result["guidance"].get("핵심_주의사항", "")
    analysis["stt_ocr_불일치"]   = crew_result.get("stt_ocr_불일치", [])

    # 정제된 복약리스트가 있으면 업데이트
    if crew_result.get("정제된_복약리스트"):
        analysis["필수복약리스트"] = crew_result["정제된_복약리스트"]

    return {
        "analysis":        analysis,
        "reflection_logs": reflection_logs,
        "risk":            risk,
        "action_plan":     crew_result.get("action_plan", {}),
        "use_mock":        False,
    }
