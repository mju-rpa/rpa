"""
app/agentic_ai/agent/crewai_agents.py

CrewAI Multi-Agent Sequential Workflow
수업 실습(chapter6_multi_agent_lab) Process.sequential + context 구조 동일하게 적용

입력:
  - analysis : medical.py + self_reflection 결과 (이미 처리된 데이터)
  - risk     : risk.py 결과 (이미 계산된 위험도)
  - 알림매체  : 알림 매체 설정

Agent 4개:
  1. MedicationAnalyzer — analysis 기반 불일치 추가 감지 + 정제
  2. RiskEvaluator      — risk 기반 위험도 판단
  3. GuidanceWriter     — analysis + risk 기반 환자 맞춤 안내문
  4. ActionPlanner      — risk 기반 RPA 액션 결정
"""
import json
import re

from crewai import Agent, Crew, Process, Task

from app.config import RISK_SCORE_REVIEW_THRESHOLD, get_crewai_llm


# ── JSON 파싱 ────────────────────────────────────────────────────
def _parse(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        return json.loads(m.group()) if m else {}


# ── CrewAI 실행 ──────────────────────────────────────────────────
def run_crewai_pipeline(
    analysis: dict,
    risk: dict,
    알림매체: str = "none",
) -> dict:
    """
    CrewAI Multi-Agent Sequential Workflow 실행.

    Args:
        analysis : medical.py + self_reflection이 생성한 복약 분석 결과
        risk     : risk.py가 계산한 위험도 점수 결과
        알림매체  : 알림 매체 (kakao / google_calendar / sms / none)

    Returns:
        guidance, action_plan 포함 dict
        (analysis, risk는 이미 계산된 값이므로 그대로 반환)
    """
    llm = get_crewai_llm()

    score = risk.get("최종점수", 100)
    needs_review = risk.get("재검토_필요", False)
    deductions = risk.get("감점항목", [])
    meds = analysis.get("필수복약리스트", [])
    warning = analysis.get("상호작용_경고", "")

    # ── Agent 정의 ────────────────────────────────────
    # 수업 실습: Research → FactCheck → Review → Report 구조 동일 적용

    medication_analyzer = Agent(
        role="복약 정보 검증 에이전트",
        goal=(
            "medical Agent가 생성한 복약 분석 결과를 검토하여 "
            "STT·OCR 간 불일치·누락 항목을 추가로 감지하고 정제한다."
        ),
        backstory=(
            "10년 경력 임상 약사. "
            "이미 추출된 복약 데이터를 재검토하여 "
            "의사 발언과 약봉투 내용의 불일치를 정밀하게 찾아낸다."
        ),
        llm=llm,
        verbose=True,
    )

    risk_evaluator = Agent(
        role="위험도 판단 에이전트",
        goal=(
            "이미 계산된 위험도 점수를 바탕으로 "
            "재검토 필요 여부와 위험 수준을 최종 판단한다."
        ),
        backstory=(
            f"의료 위험도 평가 전문가. "
            f"위험도 점수 기준({RISK_SCORE_REVIEW_THRESHOLD}점)을 적용하여 "
            "환자 안전에 필요한 조치를 판단한다."
        ),
        llm=llm,
        verbose=True,
    )

    guidance_writer = Agent(
        role="환자 맞춤형 복약 안내문 작성 에이전트",
        goal=(
            "검증된 복약 정보와 위험도를 바탕으로 "
            "환자가 이해하기 쉬운 복약 안내문을 작성한다."
        ),
        backstory="의료 커뮤니케이션 전문가. 쉬운 말로 2~5문장 이내로 안내한다.",
        llm=llm,
        verbose=True,
    )

    action_planner = Agent(
        role="RPA 액션 계획 수립 에이전트",
        goal=(
            f"위험도 판단 결과와 알림매체({알림매체})를 고려하여 "
            "RPA가 실행할 액션 목록을 결정한다."
        ),
        backstory=(
            "의료 워크플로우 자동화 전문가. "
            f"위험도 {score}점 기준으로 "
            "담당자 재검토 여부와 알림 방식을 설계한다."
        ),
        llm=llm,
        verbose=True,
    )

    # ── Task 정의 ─────────────────────────────────────

    analyze_task = Task(
        description=f"""
이미 추출된 복약 분석 결과를 검토하여 불일치·누락을 감지하라.

[복약 분석 결과]
- 환자명: {analysis.get('환자명')}
- 진료요약: {analysis.get('진료요약')}
- 필수복약리스트: {json.dumps(meds, ensure_ascii=False)}
- 상호작용_경고: {warning}

확인 항목:
1. 상호작용 경고와 복용시간 충돌 여부
2. 복용시간이 불명확한 항목
3. 금기사항 누락 의심 항목

아래 JSON만 출력하라 (다른 텍스트 금지):
{{
  "stt_ocr_불일치": [
    {{"항목": "", "내용": "", "심각도": "높음/중간/낮음"}}
  ],
  "정제된_복약리스트": [
    {{"약품명": "", "복용시간": "", "주의사항": "", "금기사항": ""}}
  ]
}}
""",
        expected_output="불일치 목록 + 정제된 복약리스트 JSON",
        agent=medication_analyzer,
    )

    risk_task = Task(
        description=f"""
이미 계산된 위험도 점수를 바탕으로 최종 판단을 내려라.

[위험도 점수]
- 최종점수: {score}점
- 감점항목: {json.dumps(deductions, ensure_ascii=False)}
- 재검토_필요: {needs_review}

기준: {RISK_SCORE_REVIEW_THRESHOLD}점 미만 → 긴급, 이상 → 일반

아래 JSON만 출력하라 (다른 텍스트 금지):
{{
  "위험_수준": "긴급/주의/정상",
  "핵심_위험요소": "가장 중요한 위험 요소 1가지",
  "재검토_권고": true/false
}}
""",
        expected_output="위험도 최종 판단 JSON",
        agent=risk_evaluator,
        context=[analyze_task],
    )

    guidance_task = Task(
        description=f"""
복약 분석 결과와 위험도를 바탕으로 환자 맞춤 복약 안내문을 작성하라.

[참고 정보]
- 위험도 점수: {score}점
- 상호작용 경고: {warning}
- 필수복약리스트: {json.dumps(meds, ensure_ascii=False)}

작성 기준:
- 불일치 발견 시 올바른 정보로 수정하여 안내
- 상호작용 경고가 있으면 반드시 강조
- 전문 용어 대신 쉬운 말 사용
- 2~5문장 이내

아래 JSON만 출력하라 (다른 텍스트 금지):
{{
  "환자맞춤_복약안내": "2~5문장 안내문",
  "핵심_주의사항": "가장 중요한 주의사항 1가지"
}}
""",
        expected_output="환자 맞춤 복약 안내문 JSON",
        agent=guidance_writer,
        context=[analyze_task, risk_task],
    )

    action_task = Task(
        description=f"""
위험도 판단 결과를 바탕으로 RPA 실행 액션을 결정하라.

[위험도 판단]
- 최종점수: {score}점
- 재검토_필요: {needs_review}
- 알림매체: {알림매체}

기준:
- 재검토_필요 = true → 담당자 재검토 알림을 최우선으로 추가
- 알림매체에 따라 적절한 RPA 액션 추가

아래 JSON만 출력하라 (다른 텍스트 금지):
{{
  "알림_우선순위": "긴급/일반/낮음",
  "권장_액션": ["RPA 실행 액션 목록"]
}}
""",
        expected_output="RPA 액션 계획 JSON",
        agent=action_planner,
        context=[analyze_task, risk_task, guidance_task],
    )

    # ── Crew 실행 ─────────────────────────────────────
    crew = Crew(
        agents=[medication_analyzer, risk_evaluator, guidance_writer, action_planner],
        tasks=[analyze_task, risk_task, guidance_task, action_task],
        process=Process.sequential,
        verbose=True,
    )

    crew.kickoff()

    analyze_result  = _parse(str(analyze_task.output  or "{}"))
    risk_result     = _parse(str(risk_task.output     or "{}"))
    guidance_result = _parse(str(guidance_task.output or "{}"))
    action_result   = _parse(str(action_task.output   or "{}"))

    return {
        "stt_ocr_불일치":    analyze_result.get("stt_ocr_불일치", []),
        "정제된_복약리스트":   analyze_result.get("정제된_복약리스트", meds),
        "위험_판단":          risk_result,
        "guidance":          guidance_result,
        "action_plan":       action_result,
    }
