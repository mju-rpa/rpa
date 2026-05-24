# 2. Agentic AI — Self-Reflection & 점수 평가

## 2.1 “Agentic”을 데모에서 어떻게 보여주나?

단순 ChatGPT 한 번 호출이 아니라, 아래 **3가지가 코드에 들어가 있음**을 강조하세요.

1. **역할 분리:** Medical Agent(초안) → Critic Agent(검증)  
2. **Self-Reflection:** Critic이 거부하면 초안을 수정해 **다시** 출력 (루프)  
3. **도구 없는 자율 판단 대신** 구조화된 JSON + 규칙 기반 점수 (의료 도메인 설명 가능)

구현 위치: `demo/app/agents.py`, `demo/app/scoring.py`

---

## 2.2 Self-Reflection (Critic 루프)

### Why

LLM은 환각·시간 충돌(예: “식전” vs “우유 아침”)을 놓칠 수 있습니다.  
**Critic이 두 번째 관점**으로 검토하면 “에이전트가 스스로 고친다”는 스토리가 됩니다.

### How (데모)

1. Medical Agent가 `필수복약리스트`, `상호작용_경고` JSON 생성  
2. Critic이 검사:
   - 우유 금지 + 아침 식전 복용 겹침?
   - STT/OCR 약품명 불일치?
   - 복용 횟수 과다?
3. `approved: false` → `revised_analysis`로 복용시간을 **식후 2시간** 등으로 수정  
4. `MAX_REFLECTION_ROUNDS`(기본 2)까지 반복

### Critic 프롬프트 (실 LLM 연동 시)

```
네가 작성한 복약 스케줄에서 '우유와 함께 복용 금지' 약이
아침 식사(우유 포함)와 겹치는지 확인하라.
겹치면 복용 시간을 2시간 뒤로 수정한 revised_analysis를 출력하라.
```

### 발표 멘트

> “1차 약사 에이전트가 스케줄을 짜면, 2차 비평 에이전트가 충돌을 찾아 수정합니다. 이게 Self-Reflection입니다.”

---

## 2.3 점수 평가 기준 (복약 위험도 Risk Score)

**시작점 100점**, 아래에서 감점 (`scoring.py`):

| 조건 | 감점 | 근거 |
|------|------|------|
| 상호작용·우유/금기 등 경고 문구 | −30 | 환자 안전 리스크 |
| STT/OCR 약품명 불일치 의심 | −20 | OCR 오류·처방 불일치 |
| 복용 횟수 과다(순응도 하락) | −10 | 실무 복약 순응 이슈 |

**임계값:** `RISK_SCORE_REVIEW_THRESHOLD=70` (환경변수로 변경 가능)

- **70점 미만** → `재검토_필요: true`  
- RPA 동작: 환자 알림 대신 **담당자 메신저 플래그** (to_be_generated)

### 발표용 예시 (현재 mock 데이터)

- 우유 관련 경고 → **−30** → 최종 **70점** (경계) 또는 그 이하 → 재검토 플래그 ON

---

## 2.4 CrewAI로 갈 때 (To-Be)

데모는 파일 2개 에이전트 함수로 대체했습니다. 프로덕션에서는:

- `Medical Analyst` Agent  
- `Pharmacy Scheduler` Agent  
- `Critic` Agent + `max_iter` / reflection 설정  

**지금 데모 API 스펙(JSON in/out)은 그대로 유지**하면 UiPath·Render 배포를 바꿀 필요가 없습니다.

---

## 2.5 실 LLM 연동 (선택)

**Ollama 필수 아님.** 상세: [06_LLM_연동_선택.md](06_LLM_연동_선택.md)

| Provider | 언제 |
|----------|------|
| `mock` | 발표·UiPath (기본) |
| `ollama` | 본인 PC에 Ollama 있을 때 |
| `gemini` | API 키만 있으면 (Ollama 없음) |
| `openai_compatible` | Groq·OpenAI·LM Studio |

`/health` 에서 현재 provider 확인.
