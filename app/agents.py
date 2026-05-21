from app.config import MAX_REFLECTION_ROUNDS
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

CRITIC_SYSTEM = """당신은 Critic(비평) 에이전트입니다. Pharmacy Agent가 만든 복약 JSON을 검토합니다.
- 우유/식사와 복용 시간 충돌 여부
- STT와 OCR 약품명 불일치
- 하루 복용 횟수 과다(5회 초과) 여부
문제가 있으면 JSON으로 {"approved": false, "feedback": "구체적 수정 지시", "revised_analysis": {동일스키마}}
문제 없으면 {"approved": true, "feedback": "검증 통과", "revised_analysis": null}
"""


def run_medical_agent(stt: str, ocr: str, use_mock: bool) -> dict:
    if use_mock:
        return mock_initial_analysis(stt, ocr)
    user = f"[STT]\n{stt}\n\n[OCR]\n{ocr}"
    return call_llm(ANALYSIS_SYSTEM, user)


def run_critic_agent(stt: str, ocr: str, draft: dict, use_mock: bool) -> dict:
    if use_mock:
        # 데모: 1회차에 우유-식전 충돌 지적 → 2회차 수정 시뮬레이션
        warnings = draft.get("상호작용_경고", "")
        if "우유" in warnings and any(
            "식전" in m.get("복용시간", "") for m in draft.get("필수복약리스트", [])
        ):
            revised = {**draft}
            for med in revised.get("필수복약리스트", []):
                if "식전" in med.get("복용시간", ""):
                    med["복용시간"] = "아침 식후 2시간 (우유·식사와 분리)"
            revised["상호작용_경고"] = (
                "진통제는 우유와 함께 복용 금지. 위산억제제는 우유 섭취 후 2시간 뒤 복용 권장."
            )
            return {
                "approved": False,
                "feedback": "아침 식전 복용이 우유 섭취와 겹칠 수 있어 식후 2시간으로 조정 필요.",
                "revised_analysis": revised,
            }
        return {"approved": True, "feedback": "검증 통과", "revised_analysis": None}

    user = f"[STT]\n{stt}\n\n[OCR]\n{ocr}\n\n[Draft]\n{draft}"
    return call_llm(CRITIC_SYSTEM, user)


def run_self_reflection(stt: str, ocr: str, initial: dict, use_mock: bool) -> tuple[dict, list[dict]]:
    current = initial
    logs: list[dict] = []

    for round_idx in range(1, MAX_REFLECTION_ROUNDS + 1):
        critic = run_critic_agent(stt, ocr, current, use_mock)
        revised = critic.get("revised_analysis")
        logs.append(
            {
                "round": round_idx,
                "critic_feedback": critic.get("feedback", ""),
                "revised": revised is not None,
            }
        )
        if critic.get("approved") or not revised:
            break
        current = revised

    return current, logs
