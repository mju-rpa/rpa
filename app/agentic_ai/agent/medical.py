from app.llm_client import call_llm, mock_initial_analysis

ANALYSIS_SYSTEM = """당신은 의료/복약 정보 분석 AI 에이전트입니다.
STT 진료 기록과 OCR 약봉투 기록을 분석해 아래 JSON만 출력하세요. 다른 텍스트 금지.

{
  "환자명": "이름",
  "진료요약": "1~2줄",
  "필수복약리스트": [{"약품명": "", "복용시간": "", "주의사항": ""}],
  "상호작용_경고": "주의사항"
}
"""


def run_medical_agent(stt: str, ocr: str, use_mock: bool) -> dict:
    if use_mock:
        return mock_initial_analysis(stt, ocr)
    user = f"[STT]\n{stt}\n\n[OCR]\n{ocr}"
    return call_llm(ANALYSIS_SYSTEM, user)
