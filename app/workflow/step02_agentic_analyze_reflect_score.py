"""Stage 2–3: Agentic AI 분석 · Self-Reflection · 위험도 점수."""

from app.agentic_ai.agent.medical import run_medical_agent
from app.agentic_ai.scoring.risk import compute_risk_score
from app.agentic_ai.self_reflection.loop import run_self_reflection
from app.config import uses_mock_llm


def agentic_analyze_reflect_score(stt: str, ocr: str, 환자명: str = "") -> dict:
    use_mock = uses_mock_llm()
    draft = run_medical_agent(stt, ocr, use_mock)
    analysis, reflection_logs = run_self_reflection(stt, ocr, draft, use_mock)
    if 환자명:
        analysis["환자명"] = 환자명
    risk = compute_risk_score(stt, ocr, analysis)
    return {
        "analysis": analysis,
        "reflection_logs": reflection_logs,
        "risk": risk,
        "use_mock": use_mock,
    }
