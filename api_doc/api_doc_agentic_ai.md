# Agentic AI — API 문서

> **담당 엔드포인트:** `POST /analyze`, `POST /demo/pipeline`  
> **내부 모듈:** `app/agentic_ai/`

---

## 1. 엔드포인트 입력

### POST /analyze

```json
{
  "patient_id": "P-2026-001",
  "환자명": "김철수",
  "알림매체": "google_calendar",
  "연락처": {
    "전화번호": "010-1234-5678",
    "카카오_id": "",
    "google_calendar_email": "patient@example.com"
  },
  "stt_text": "의사: 혈압약이랑 당뇨약 같이 드세요. 우유랑은 절대 안됩니다.",
  "ocr_text": "넥시움정 1일 1회 아침 식전 / 타이레놀정 필요시",
  "hidl_enabled": false,
  "hidl_approved": null
}
```

---

## 2. 최종 응답 형식

```json
{
  "workflow_stage": "completed",
  "llm_provider": "mock (no API)",

  "patient_name": "김철수",
  "final_score": 70,
  "needs_review": false,
  "hidl_status": "skipped",
  "reflection_summary": "Round 1: 아침 식전 복용이 우유 섭취와 겹칠 수 있어 조정 필요. (revised=True)\nRound 2: 검증 통과 (revised=False)",
  "agent_trace_summary": "[1] Data Collector | STT/OCR 텍스트 수집\n[2] Medical Agent | 진료 요약 + 복약 JSON 초안 생성\n...",
  "report_text": "======================================\n[Atlas 메디케어] 맞춤형 진료/복약 리포트\n발행일시: 2026-05-25 12:00:00\n...",
  "report_file": "output/김철수_복약리포트.txt",

  "analysis": {
    "환자명": "김철수",
    "진료요약": "위산 역류 증상으로 위산억제제 + 진통제 처방",
    "필수복약리스트": [
      {
        "약품명": "넥시움정 (위산억제제)",
        "복용시간": "1일 1회 아침 식후 2시간 (우유·식사와 분리)",
        "주의사항": "매일 챙겨 드세요."
      },
      {
        "약품명": "타이레놀정 (진통제)",
        "복용시간": "두통 심할 때만",
        "주의사항": "물과 함께 복용하세요."
      }
    ],
    "상호작용_경고": "진통제는 우유와 함께 복용 금지.",
    "stt_ocr_불일치": [
      {
        "항목": "우유 금지 주의사항",
        "내용": "의사가 강조했으나 약봉투에 없음",
        "심각도": "높음"
      }
    ],
    "환자맞춤_복약안내": "넥시움은 아침 식사 후 2시간 뒤 드세요. ⚠️ 우유와 함께 드시면 절대 안 됩니다.",
    "핵심_주의사항": "우유와 함께 복용 금지"
  },

  "risk_score": {
    "기본점수": 100,
    "감점항목": [{"항목": "상호작용·복용 주의 경고", "감점": 30}],
    "최종점수": 70,
    "재검토_필요": false,
    "재검토_사유": ""
  },

  "reflection_logs": [
    {"round": 1, "critic_feedback": "아침 식전 복용이 우유 섭취와 겹칠 수 있어 조정 필요.", "revised": true},
    {"round": 2, "critic_feedback": "검증 통과", "revised": false}
  ],

  "action_plan": {
    "알림_우선순위": "일반",
    "권장_액션": [
      "[RPA] google_calendar 알림 발송",
      "[RPA] 복약 보고서 생성",
      "[RPA] Excel 복약 캘린더 저장"
    ]
  },

  "notification_plan": {
    "알림매체": "google_calendar",
    "status": "demo_scheduled",
    "message": "[김철수] Google Calendar 등록 예약 → patient@example.com",
    "calendar_events": [
      {
        "title": "[복약] 넥시움정 (위산억제제)",
        "start": "2026-05-25T08:00:00",
        "notes": "1일 1회 아침 식전 | 매일 챙겨 드세요.",
        "status": "to_be_generated"
      }
    ]
  },

  "rpa_actions": [
    "[RPA] Excel 리포트 저장 → output/김철수_복약리포트.xlsx (to_be_generated)",
    "[RPA] 텍스트 리포트 저장 → output/김철수_복약리포트.txt"
  ],

  "agent_trace": [
    {"step": 1, "role": "RPA",        "agent": "Data Collector",          "action": "STT/OCR 텍스트 수집"},
    {"step": 2, "role": "Agentic AI", "agent": "Medical Agent",           "action": "진료 요약 + 복약 JSON 초안 생성"},
    {"step": 3, "role": "Agentic AI", "agent": "Critic Agent (Self-Reflection)", "action": "복약 스케줄 검증", "revised": true},
    {"step": 4, "role": "Agentic AI", "agent": "Critic Agent (Self-Reflection)", "action": "복약 스케줄 검증", "revised": false},
    {"step": 8, "role": "Agentic AI", "agent": "Risk Scorer",             "action": "복약 위험도 점수 산출"},
    {"step": 9, "role": "HIDL",       "agent": "Human Review Gate",       "action": "HIDL skipped"},
    {"step": 11,"role": "Agentic AI", "agent": "Notification Planner",    "action": "알림·RPA 실행 계획 생성"},
    {"step": 12,"role": "RPA",        "agent": "Executor",                "action": "[RPA] Excel 리포트 저장"}
  ]
}
```

---

## 3. CrewAI Agent Task 입출력

### MedicationAnalyzer

| | |
|--|--|
| **입력** | analysis (medical.py 생성 결과) |
| **출력** | `stt_ocr_불일치` 목록 + `정제된_복약리스트` |

### RiskEvaluator

| | |
|--|--|
| **입력** | risk (risk.py 계산 결과) + MedicationAnalyzer context |
| **출력** | `위험_수준` + `핵심_위험요소` + `재검토_권고` |

### GuidanceWriter

| | |
|--|--|
| **입력** | analysis + risk + 앞 두 Agent context |
| **출력** | `환자맞춤_복약안내` + `핵심_주의사항` |

### ActionPlanner

| | |
|--|--|
| **입력** | risk + 알림매체 + 앞 세 Agent context |
| **출력** | `알림_우선순위` + `권장_액션` |

---

## 4. report_text 형식 (txt 파일)

```
======================================
[Atlas 메디케어] 맞춤형 진료/복약 리포트
발행일시: 2026-05-25 12:00:00
======================================
👤 환자명: 김철수

📋 [진료 요약]
위산 역류 증상으로 위산억제제 + 진통제 처방

💊 [복약 스케줄]
 - 넥시움정 (위산억제제) | 1일 1회 아침 식전 | 주의: 매일 챙겨 드세요.
 - 타이레놀정 (진통제) | 두통 심할 때만 | 주의: 물과 함께 복용하세요.

⚠️ [특별 주의사항]
진통제는 우유와 함께 복용 금지.

📊 [복약 위험도 점수] 70 / 100
   재검토 필요: 아니오
======================================
```

---

## 5. mock vs 실제 LLM 차이

| 항목 | mock | 실제 LLM |
|------|------|---------|
| `LLM_PROVIDER` | `mock` | `gemini` / `openai_compatible` / `ollama` |
| analysis | medical.py 고정값 | LLM 실제 분석 |
| stt_ocr_불일치 | 빈 리스트 | CrewAI 감지 결과 |
| 환자맞춤_복약안내 | 빈 문자열 | GuidanceWriter 생성 |
| action_plan | 빈 dict `{}` | ActionPlanner 결과 |
| 속도 | 즉시 | LLM 추론 시간 소요 |
