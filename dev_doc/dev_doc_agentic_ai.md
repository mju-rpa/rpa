# Agentic AI 모듈 개발 문서

> **위치:** `app/agentic_ai/`  
> **담당 단계:** `step02` — STT·OCR 결과 수신 → CrewAI 분석 → 결과 반환

---

## 1. 디렉터리 구조

```
app/agentic_ai/
├── agent/
│   ├── medical.py          # Medical Agent — 복약 초안 생성
│   ├── critic.py           # Critic Agent — Self-Reflection 검증
│   └── crewai_agents.py    # CrewAI 4개 Agent 파이프라인 (핵심)
├── self_reflection/
│   └── loop.py             # Critic 반복 실행 루프
├── scoring/
│   └── risk.py             # 위험도 점수 계산
├── hidl/
│   └── gate.py             # Human-In-The-Loop 게이트
└── schema/
    └── models.py           # Pydantic 데이터 모델
```

---

## 2. 실행 흐름

```
step02.agentic_analyze_reflect_score(stt, ocr, 환자명, 알림매체)
  │
  ├─ 1. medical.py           → analysis 초안 생성
  ├─ 2. self_reflection/loop → Critic Agent 검증 (최대 N라운드)
  ├─ 3. scoring/risk.py      → risk 위험도 계산
  │
  ├─ [mock 모드]  → analysis + risk 그대로 반환
  │
  └─ [실제 LLM]  → crewai_agents.run_crewai_pipeline(analysis, risk, 알림매체)
       ├─ MedicationAnalyzer  → analysis 재검토, 불일치 감지
       ├─ RiskEvaluator       → risk 기반 위험도 최종 판단
       ├─ GuidanceWriter      → 환자 맞춤 안내문 생성
       └─ ActionPlanner       → RPA 액션 결정
```

---

## 3. step02 반환값

```python
{
    "analysis":        dict,  # 복약 분석 결과
    "reflection_logs": list,  # Self-Reflection 라운드별 로그
    "risk":            dict,  # 위험도 점수 결과
    "action_plan":     dict,  # CrewAI ActionPlanner 결과
    "use_mock":        bool,  # mock 모드 여부
}
```

### analysis 상세

```python
{
    # medical.py + self_reflection 생성
    "환자명":          str,
    "진료요약":        str,
    "필수복약리스트": [
        {"약품명": str, "복용시간": str, "주의사항": str}
    ],
    "상호작용_경고":   str,

    # CrewAI MedicationAnalyzer 추가 (실제 LLM 모드)
    "stt_ocr_불일치": [
        {"항목": str, "내용": str, "심각도": "높음/중간/낮음"}
    ],
    "정제된_복약리스트": [...],

    # CrewAI GuidanceWriter 추가 (실제 LLM 모드)
    "환자맞춤_복약안내": str,
    "핵심_주의사항":     str,
}
```

### risk 상세

```python
{
    "기본점수":    100,
    "감점항목": [{"항목": str, "감점": int}],
    "최종점수":    int,   # 0~100
    "재검토_필요": bool,  # 70점 미만이면 True
    "재검토_사유": str,
}
```

**감점 기준:**

| 항목 | 감점 |
|------|------|
| 상호작용 경고 존재 | -30점 |
| 약품명 불일치 의심 | -20점 |
| 하루 복용 5회 초과 | -10점 |

### reflection_logs 상세

```python
[
    {
        "round":           int,   # 1, 2, 3...
        "critic_feedback": str,
        "revised":         bool,
    }
]
```

### action_plan 상세 (실제 LLM 모드)

```python
{
    "알림_우선순위": "긴급/일반/낮음",
    "권장_액션":    [str],
}
```

---

## 4. 최종 API 응답 (POST /analyze)

run_pipeline이 step02~step04를 거쳐 반환하는 최종 응답이에요.

```python
{
    # 기본 정보
    "workflow_stage":  "completed",
    "llm_provider":    str,

    # UiPath 연동용 flat 키
    "patient_name":        str,
    "final_score":         int,
    "needs_review":        bool,
    "hidl_status":         str,
    "reflection_summary":  str,
    "agent_trace_summary": str,
    "report_text":         str,
    "report_file":         str,

    # 상세 데이터
    "analysis":          dict,
    "risk_score":        dict,
    "reflection_logs":   list,
    "notification_plan": dict,
    "rpa_actions":       list,
    "action_plan":       dict,   # CrewAI ActionPlanner 결과
    "agent_trace":       list,
    "reflection_lines":  list,
    "agent_trace_lines": list,
}
```

---

## 5. 파일별 역할

| 파일 | 함수 | 역할 |
|------|------|------|
| `agent/medical.py` | `run_medical_agent()` | STT·OCR → 복약 초안 생성 |
| `agent/critic.py` | `run_critic_agent()` | 복약 초안 검증 |
| `self_reflection/loop.py` | `run_self_reflection()` | Critic 반복 실행 |
| `scoring/risk.py` | `compute_risk_score()` | 위험도 점수 계산 |
| `agent/crewai_agents.py` | `run_crewai_pipeline()` | CrewAI 4개 Agent 실행 |
| `hidl/gate.py` | `apply_hidl_gate()` | Human 승인 게이트 |

---

## 6. 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `LLM_PROVIDER` | LLM 선택 | `mock` |
| `GEMINI_API_KEY` | Gemini API 키 | - |
| `GEMINI_MODEL` | Gemini 모델명 | `gemini-2.0-flash` |
| `OPENAI_API_KEY` | OpenAI API 키 | - |
| `OPENAI_MODEL` | OpenAI 모델명 | `gpt-4o-mini` |
| `OPENAI_BASE_URL` | OpenAI 호환 엔드포인트 | `https://api.openai.com/v1` |
| `OLLAMA_MODEL` | Ollama 모델명 | `llama3.2` |
| `RISK_SCORE_REVIEW_THRESHOLD` | 재검토 기준점 | `70` |
| `MAX_REFLECTION_ROUNDS` | Self-Reflection 최대 횟수 | `3` |

---

## 7. run_pipeline.py 변경사항

```python
# 변경 전
agentic = agentic_analyze_reflect_score(stt, ocr, req.환자명)

# 변경 후
agentic = agentic_analyze_reflect_score(stt, ocr, req.환자명, req.알림매체)
action_plan = agentic.get("action_plan", {})
result["action_plan"] = action_plan
```

---

## 8. requirements.txt 추가

```
crewai>=0.80.0
```
