"""
app/workflow/step02_agentic_analyze_reflect_score.py

Stage 2: Agentic AI 분석

Agent 5개:
  1. STT Summarizer            — STT 요약, 언급 약품 추출
  2. OCR Medication Data Agent — OCR 추출 + DB 조회
  3. Prescription Reviewer     — 불일치 체크 + Self-Reflection
  4. Risk Evaluator            — DB 건수 기반 군집 분류 + HITL 여부
  5. Guidance Writer           — 보고서용 JSON 구조화
"""
from app.agentic_ai.agent.crewai_agents import mock_crewai_result, run_crewai_pipeline
from app.config import uses_mock_llm


def agentic_analyze_reflect_score(
    stt: str,
    ocr: str,
    환자명: str = "",
    알림매체: str = "none",
) -> dict:
    use_mock = uses_mock_llm()

    if use_mock:
        result = mock_crewai_result(stt, ocr, 알림매체)
    else:
        result = run_crewai_pipeline(stt, ocr, 알림매체)

    # 환자명 오버라이드 (요청값 우선)
    if 환자명 and result.get("guidance"):
        result["guidance"]["환자명"] = 환자명

    return {
        "stt_summary": result.get("stt_summary", {}),
        "ocr_data":    result.get("ocr_data", {}),
        "mismatch":    result.get("mismatch", {}),
        "risk":        result.get("risk", {}),
        "guidance":    result.get("guidance", {}),
        "use_mock":    use_mock,
    }
