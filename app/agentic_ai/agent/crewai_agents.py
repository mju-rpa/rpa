"""
app/agentic_ai/agent/crewai_agents.py

CrewAI Multi-Agent Sequential Workflow
수업 실습(chapter6_multi_agent_lab) Process.sequential + context 구조 동일 적용

핵심 원칙:
  - 모든 판단은 DB 정보만 기반으로 수행
  - LLM은 텍스트 파싱/요약/비교/정리만 수행
  - LLM이 약물 효과·위험도를 임의로 판단하는 것 절대 금지
  - DB에 없는 내용은 반드시 '데이터 없음'으로 표시

Agent 5개 (Sequential):
  1. STT Summarizer            — STT 텍스트 요약, 언급 약품 추출
  2. OCR Medication Data Agent — OCR 약품 추출 + DB 조회
  3. Prescription Reviewer     — STT·OCR 불일치 체크 + Self-Reflection
  4. Risk Evaluator            — DB 건수 기반 위험/주의/일반 군집 분류
  5. Guidance Writer           — 전체 결과 보고서용 JSON 구조화
"""

import json
import re

from crewai import Agent, Crew, Process, Task

from app.config import get_crewai_llm
from app.agentic_ai.db.db_query import DrugDB


# ── JSON 파싱 헬퍼 ─────────────────────────────────────────────
def _parse(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        return json.loads(m.group()) if m else {}


# ── DB 사전 조회 ───────────────────────────────────────────────
def _fetch_db_context(drug_names: list[str]) -> tuple[str, dict]:
    """
    LLM Task 실행 전 DB에서 약품 정보를 먼저 조회.
    LLM은 이 결과만 참고하고 임의 판단 금지.
    """
    if not drug_names:
        return "약품 정보 없음", {}
    db = DrugDB()
    rag_context  = db.build_rag_context(*drug_names)
    db_warnings  = db.query_all(*drug_names).to_dict()
    db.close()
    return rag_context, db_warnings


# ── mock 결과 ──────────────────────────────────────────────────
def mock_crewai_result(stt: str, ocr: str, 알림매체: str) -> dict:
    """LLM_PROVIDER=mock 일 때 전체 CrewAI 결과 시뮬레이션."""

    stt_summary = {
        "증상_요약": "위장 불편, 두통",
        "언급_약품": ["넥시움", "타이레놀"],
        "상담_맥락": "복약 방법 및 주의사항 문의",
    }

    ocr_data = {
        "약품_목록": [
            {
                "약품명": "넥시움정 (위산억제제)",
                "복용시간": "1일 1회 아침 식전",
                "복용횟수": "1일 1회",
                "용량": "1정",
                "DB_정보": {
                    "효능": "위산 분비 억제",
                    "주의사항": "우유와 함께 복용 금지",
                    "상호작용": "메토트렉세이트와 병용 시 상의",
                },
            },
            {
                "약품명": "타이레놀정 (진통제)",
                "복용시간": "두통 심할 때만",
                "복용횟수": "필요 시",
                "용량": "1~2정",
                "DB_정보": {
                    "효능": "해열·진통",
                    "주의사항": "음주 중 복용 금지",
                    "상호작용": "데이터 없음",
                },
            },
        ]
    }

    mismatch = {
        "불일치_목록": [],
        "일치_항목": ["넥시움정", "타이레놀정"],
        "재검토_완료": True,
    }

    risk = {
        "군집": "주의",
        "주의사항_건수": 2,
        "불일치_건수": 0,
        "분류_근거": [
            "우유와 함께 복용 금지",
            "음주 중 복용 금지",
        ],
        "HITL_필요": True,   # 위험·주의이면 HITL 필요
        "HITL_메시지": "복약 주의사항 2건이 발견되었습니다. 계속 진행하시겠습니까?",
    }

    guidance = {
        "환자명": "",
        "약품_목록": ["넥시움정 (위산억제제)", "타이레놀정 (진통제)"],
        "불일치_항목": [],
        "군집": "주의",
        "주의사항": [
            "우유와 함께 복용 금지",
            "음주 중 복용 금지",
        ],
        "알림_메시지": f"복약 주의사항 2건이 확인되었습니다. [{알림매체}] 알림을 확인하세요.",
        "csv_rows": [
            {
                "약품명": "넥시움정 (위산억제제)",
                "복용시간": "1일 1회 아침 식전",
                "주의사항": "우유와 함께 복용 금지",
                "군집": "주의",
            },
            {
                "약품명": "타이레놀정 (진통제)",
                "복용시간": "두통 심할 때만",
                "주의사항": "음주 중 복용 금지",
                "군집": "주의",
            },
        ],
    }

    return {
        "stt_summary": stt_summary,
        "ocr_data":    ocr_data,
        "mismatch":    mismatch,
        "risk":        risk,
        "guidance":    guidance,
    }


# ── CrewAI 파이프라인 ───────────────────────────────────────────
def run_crewai_pipeline(
    stt: str,
    ocr: str,
    알림매체: str = "none",
    diagnosis_text: str = "",  # 진단서 OCR 텍스트 (선택)
    hitl: dict = None,         # OCR/STT 신뢰도 기반 HITL 신호
) -> dict:
    """
    CrewAI Multi-Agent Sequential Workflow 실행.
    수업 실습과 동일한 Process.sequential + context 연결 구조.

    모든 판단은 DB 정보만 기반으로 수행.
    LLM은 텍스트 파싱/요약/비교/정리만 담당.
    """
    hitl = hitl or {}

    # ── HITL 신뢰도 경고 생성 ─────────────────────────────────
    hitl_warnings = []
    stt_hitl = hitl.get("stt", {})
    ocr_hitl = hitl.get("ocr", {})

    if stt_hitl.get("status") == "hitl_required":
        score = stt_hitl.get("confidence", {}).get("score", 0)
        reason = stt_hitl.get("confidence", {}).get("response", "")
        hitl_warnings.append(
            f"⚠️ STT 신뢰도 낮음 (점수: {score:.2f}) - {reason}"
        )

    if ocr_hitl.get("status") == "hitl_required":
        score = ocr_hitl.get("confidence", {}).get("score", 0)
        reason = ocr_hitl.get("confidence", {}).get("response", "")
        hitl_warnings.append(
            f"⚠️ OCR 신뢰도 낮음 (점수: {score:.2f}) - {reason}"
        )

    hitl_warning_text = (
        "\n".join(hitl_warnings)
        if hitl_warnings
        else "STT/OCR 신뢰도 정상"
    )
    llm = get_crewai_llm()

    # ── DB 사전 조회 (LLM 실행 전) ────────────────────────────
    raw_drug_names = re.findall(r"[가-힣A-Za-z]+정|[가-힣A-Za-z]+캡슐", ocr)
    rag_context, db_warnings = _fetch_db_context(raw_drug_names)

    # ── Agent 정의 ────────────────────────────────────────────

    # Agent 1: STT Summarizer (수업: Research Agent)
    stt_summarizer = Agent(
        role="STT 텍스트 요약 에이전트",
        goal=(
            "STT 음성 인식 텍스트에서 환자의 증상, 불편사항, "
            "상담 맥락, 언급된 약품명만 추출하여 요약한다. "
            "의학적 판단 없이 텍스트에 있는 내용만 추출한다."
        ),
        backstory=(
            "의료 텍스트 분석 전문가. "
            "텍스트에 명시된 내용만 추출하며 "
            "임의로 내용을 추가하거나 판단하지 않는다."
        ),
        llm=llm,
        verbose=True,
    )

    # Agent 2: OCR Medication Data Agent (수업: Research Agent)
    ocr_agent = Agent(
        role="OCR 약품 정보 추출 에이전트",
        goal=(
            "OCR 약봉투 텍스트에서 약품명, 복용 횟수, 복용 시간, 용량을 추출하고 "
            "제공된 DB 정보를 그대로 연결하여 출력한다. "
            "DB에 없는 정보는 반드시 '데이터 없음'으로 표시하며 "
            "절대 임의로 약품 정보를 생성하지 않는다."
        ),
        backstory=(
            "약봉투 데이터 파싱 전문가. "
            "OCR 텍스트를 구조화하고 제공된 DB 원본 데이터만 연결한다. "
            "DB에 없는 내용은 절대 추측하지 않는다."
        ),
        llm=llm,
        verbose=True,
    )

    # Agent 3: Prescription Reviewer (수업: Fact Check Agent)
    reviewer = Agent(
        role="처방 불일치 검토 에이전트",
        goal=(
            "STT에서 언급된 약품이 OCR 목록에 있는지, "
            "OCR에만 있고 STT에 없는 약품이 있는지 체크한다. "
            "있다/없다만 확인하며 의학적 판단은 절대 하지 않는다. "
            "1차 체크 후 누락된 항목이 없는지 반드시 재검토한다."
        ),
        backstory=(
            "데이터 비교 검증 전문가. "
            "두 데이터 간 일치·불일치 여부만 판단하며 "
            "의학적 위험성 평가는 하지 않는다."
        ),
        llm=llm,
        verbose=True,
    )

    # Agent 4: Risk Evaluator (수업: Review Agent)
    risk_evaluator = Agent(
        role="DB 기반 위험도 군집 분류 에이전트",
        goal=(
            "제공된 DB 조회 결과의 주의사항·금기·부작용 건수를 카운트하여 "
            "위험/주의/일반으로 군집을 분류한다. "
            "위험·주의 군집이면 HITL 필요 여부를 설정한다. "
            "반드시 제공된 DB 데이터만 기반으로 분류하며 "
            "LLM이 임의로 의학적 판단을 내리는 것을 절대 금지한다."
        ),
        backstory=(
            "규칙 기반 위험도 분류 전문가. "
            "DB에서 조회된 건수와 규칙만으로 군집을 결정하며 "
            "DB에 없는 내용은 절대 판단하지 않는다."
        ),
        llm=llm,
        verbose=True,
    )

    # Agent 5: Guidance Writer (수업: Report Agent)
    guidance_writer = Agent(
        role="보고서 데이터 구조화 에이전트",
        goal=(
            "앞선 모든 Agent 결과를 RPA가 바로 사용할 수 있는 "
            "보고서용 JSON 형식으로 구조화한다. "
            "새로운 의학 정보를 생성하지 않고 "
            "앞선 결과를 정리하는 역할만 수행한다."
        ),
        backstory=(
            "의료 데이터 구조화 전문가. "
            "분석 결과를 RPA가 처리할 수 있는 형태로 변환하며 "
            "새로운 판단이나 정보 추가는 하지 않는다."
        ),
        llm=llm,
        verbose=True,
    )

    # ── Task 정의 ─────────────────────────────────────────────

    stt_task = Task(
        description=f"""
STT 텍스트에서 증상, 불편사항, 상담 맥락, 언급된 약품명을 추출하라.

[STT 텍스트]
{stt}

[진단서 텍스트 (있는 경우)]
{diagnosis_text if diagnosis_text else "없음"}

[STT/OCR 신뢰도 경고]
{hitl_warning_text}

주의:
- 텍스트에 있는 내용만 추출하라
- 의학적 판단을 내리지 마라
- 텍스트에 없는 내용은 절대 추가하지 마라
- DB에 없는 내용은 추측하지 마라

아래 JSON만 출력하라 (다른 텍스트 금지):
{{
  "증상_요약": "텍스트에서 언급된 증상",
  "언급_약품": ["약품명 목록"],
  "상담_맥락": "상담 내용 요약"
}}
""",
        expected_output="증상·언급 약품·상담 맥락 JSON",
        agent=stt_summarizer,
    )

    ocr_task = Task(
        description=f"""
OCR 텍스트에서 약품 정보를 추출하고 아래 DB 정보를 그대로 연결하라.

[OCR 텍스트]
{ocr}

[DB 원본 데이터 - 반드시 이 정보만 사용하라]
{rag_context}

주의:
- DB에 있는 정보만 그대로 연결하라
- DB에 없는 약품 정보는 반드시 "데이터 없음"으로 표시하라
- 절대 임의로 약품 정보를 생성하지 마라

아래 JSON만 출력하라 (다른 텍스트 금지):
{{
  "약품_목록": [
    {{
      "약품명": "",
      "복용시간": "",
      "복용횟수": "",
      "용량": "",
      "DB_정보": {{
        "효능": "DB 원본 또는 데이터 없음",
        "주의사항": "DB 원본 또는 데이터 없음",
        "상호작용": "DB 원본 또는 데이터 없음"
      }}
    }}
  ]
}}
""",
        expected_output="약품 목록 + DB 정보 연결 JSON",
        agent=ocr_agent,
    )

    review_task = Task(
        description=f"""
STT에서 언급된 약품과 OCR 약품 목록을 비교하여 불일치를 체크하라.

[STT 요약 결과]
(앞선 STT Summarizer 결과 참고)

[OCR 약품 목록]
(앞선 OCR Agent 결과 참고)

[STT/OCR 신뢰도 경고]
{hitl_warning_text}

체크 항목:
1. STT에서 언급된 약품이 OCR 목록에 있는가
2. OCR에만 있고 STT에서 언급되지 않은 약품이 있는가
3. STT/OCR 신뢰도 경고가 있으면 불일치 주의사항에 반드시 포함하라

주의:
- 있다/없다만 확인하라
- 불일치의 위험성을 판단하지 마라
- 의학적 평가를 내리지 마라

Self-Reflection (반드시 수행):
- 1차 체크 완료 후 놓친 항목이 없는지 반드시 재검토하라
- 재검토 완료 여부를 결과에 표시하라

아래 JSON만 출력하라 (다른 텍스트 금지):
{{
  "불일치_목록": [
    {{
      "항목": "약품명",
      "STT": "언급됨/언급안됨",
      "OCR": "있음/없음",
      "상태": "일치/불일치",
      "주의사항": "불일치 내용 (불일치 시만)"
    }}
  ],
  "일치_항목": ["일치하는 약품 목록"],
  "재검토_완료": true
}}
""",
        expected_output="불일치 목록 + 재검토 완료 JSON",
        agent=reviewer,
        context=[stt_task, ocr_task],
    )

    risk_task = Task(
        description=f"""
아래 DB 조회 결과만 기반으로 위험/주의/일반 군집을 분류하라.

[DB 사전 조회 결과 - 반드시 이 데이터만 사용하라]
심각 항목: {db_warnings.get('심각', [])}
주의 항목: {db_warnings.get('주의', [])}
참고 항목: {db_warnings.get('참고', [])}
용량초과:  {db_warnings.get('용량초과', [])}
기간초과:  {db_warnings.get('기간초과', [])}

[불일치 결과]
(앞선 Prescription Reviewer 결과 참고)

분류 규칙 (DB 데이터만 기반):
- 위험: 심각 항목 1건 이상 OR 불일치 있음
- 주의: 주의 항목 1건 이상
- 일반: 이상 없음

HITL 규칙:
- 위험·주의 → HITL_필요: true
- 일반 → HITL_필요: false

주의:
- 반드시 위 DB 데이터만 기반으로 분류하라
- LLM이 임의로 의학적 판단을 내리지 마라

아래 JSON만 출력하라 (다른 텍스트 금지):
{{
  "군집": "위험/주의/일반",
  "주의사항_건수": 0,
  "불일치_건수": 0,
  "분류_근거": ["DB에서 조회된 주의사항 목록"],
  "HITL_필요": false,
  "HITL_메시지": "위험·주의 시 사용자에게 보여줄 메시지"
}}
""",
        expected_output="DB 기반 군집 분류 + HITL 여부 JSON",
        agent=risk_evaluator,
        context=[ocr_task, review_task],
    )

    guidance_task = Task(
        description=f"""
앞선 모든 Agent 결과를 RPA가 사용할 수 있는 JSON으로 구조화하라.

알림매체: {알림매체}

주의:
- 새로운 의학 정보를 생성하지 마라
- 앞선 결과를 정리하는 역할만 수행하라
- 앞선 결과에 없는 내용은 추가하지 마라

아래 JSON만 출력하라 (다른 텍스트 금지):
{{
  "환자명": "OCR에서 추출된 환자명 또는 데이터 없음",
  "약품_목록": ["약품명 리스트"],
  "불일치_항목": ["불일치 항목 리스트"],
  "군집": "위험/주의/일반",
  "주의사항": ["DB에서 조회된 주의사항 목록"],
  "알림_메시지": "군집과 주의사항 건수 기반 알림 문구",
  "csv_rows": [
    {{
      "약품명": "",
      "복용시간": "",
      "주의사항": "DB 조회 결과",
      "군집": ""
    }}
  ]
}}
""",
        expected_output="보고서용 JSON + 알림 메시지",
        agent=guidance_writer,
        context=[stt_task, ocr_task, review_task, risk_task],
    )

    # ── Crew 실행 ─────────────────────────────────────────────
    crew = Crew(
        agents=[
            stt_summarizer,
            ocr_agent,
            reviewer,
            risk_evaluator,
            guidance_writer,
        ],
        tasks=[
            stt_task,
            ocr_task,
            review_task,
            risk_task,
            guidance_task,
        ],
        process=Process.sequential,
        verbose=True,
    )

    crew.kickoff()

    return {
        "stt_summary": _parse(str(stt_task.output     or "{}")),
        "ocr_data":    _parse(str(ocr_task.output     or "{}")),
        "mismatch":    _parse(str(review_task.output  or "{}")),
        "risk":        _parse(str(risk_task.output    or "{}")),
        "guidance":    _parse(str(guidance_task.output or "{}")),
    }
