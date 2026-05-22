# 08. 팀원용 — UiPath + Agentic AI 전체 연동 가이드

> **목표:** 팀장 PC에서 **UiPath(간단) + Python API(Agentic AI)** 를 붙여,  
> 조원에게 **Self-Reflection → 점수 → RPA 분기**가 **눈에 보이게** 보여주기.

---

## 0. 한 장 요약 — 전체 워크플로우

```
┌─────────────────────────────────────────────────────────────────┐
│  TASK 1 [RPA]  데이터 수집                                       │
│  sample_input.json 읽기 (= 나중엔 STT API + OCR API)             │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP POST /analyze (JSON)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  TASK 2 [Agentic AI]  Python FastAPI (demo/app/)                  │
│  ① Medical Agent  → 복약 JSON 초안                               │
│  ② Critic Agent   → Self-Reflection (우유·식전 충돌 수정)       │
│  ③ Risk Scorer    → 100점 − 감점 → 재검토_필요?                  │
│  ④ Planner        → rpa_actions[] (RPA가 할 일 목록)             │
└────────────────────────────┬────────────────────────────────────┘
                             │ JSON 응답
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  TASK 3 [RPA]  실행                                              │
│  agent_trace / reflection_logs 출력 → txt 저장 → If 분기         │
│  재검토_필요=True → 담당자 알림 (Message Box)                    │
│  False → 환자 알림 매체 분기 (Message Box)                       │
└─────────────────────────────────────────────────────────────────┘
```

**과제 관점:** 입력 → **AI 판단·계획** → **RPA 실행** → **결과 파일** ✅

---

## 1. 사전 준비 (팀장 PC 1회)

### 1-1. Python API

```powershell
cd "e:\5-1\과제제출\rpa_팀프로젝트\demo"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 1-2. API 서버 켜기 (UiPath 연동 전 필수)

```powershell
cd demo
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

브라우저 확인: http://localhost:8000/health → `"status":"ok"`

### 1-3. UiPath Studio

- Community Edition 설치
- New Project → **Process** → 이름 `AtlasMedical_Demo`

---

## 2. 샘플 데이터 — 어디에, 어떻게?

| 파일 | 용도 | UiPath에서 |
|------|------|------------|
| `demo/data/sample_input.json` | **일반 케이스** (김철수, Self-Reflection 1회) | Read Text File → HTTP Body |
| `demo/data/sample_input_high_risk.json` | **고위험** (점수↓, `재검토_필요=true`) | If 분기 시연용 |

### sample_input.json 구조 (RPA가 보낼 JSON)

```json
{
  "환자명": "김철수",
  "알림매체": "google_calendar",
  "연락처": { "전화번호": "...", "google_calendar_email": "..." },
  "stt_text": "의사·환자 진료 대화 (STT 결과)",
  "ocr_text": "약봉투 OCR 텍스트"
}
```

**지금은 STT/OCR API 대신** 이 JSON이 “RPA가 모아온 데이터” 역할입니다.  
발표 멘트: *“노란 구간 = To-Be, 실제는 UiPath가 STT/OCR 호출 후 같은 JSON을 만듭니다.”*

### 샘플 바꿔보기

- `stt_text` / `ocr_text` 수정 → AI 분석 내용 변경
- `sample_input_high_risk.json` → UiPath **If (재검토_필요)** True 분기 확인

---

## 3. Agentic AI가 보이는 방법 (조원 설명용)

### 3-1. 터미널에서 (API 없이)

```powershell
cd demo
$env:PYTHONIOENCODING="utf-8"
python run_standalone.py
```

출력에서 **반드시 보여줄 3블록:**

1. **Reflection** — Critic이 “우유·식전 충돌” 지적 → 수정  
2. **Risk Score** — `최종점수`, `감점항목`  
3. **RPA Actions** — AI가 RPA에게 내린 “실행 지시”

### 3-2. Swagger (API + UiPath 동일)

http://localhost:8000/docs → `POST /analyze` → `sample_input.json` 붙여넣기

응답 JSON **필수 필드 (조원에게 설명):**

| 필드 | 의미 |
|------|------|
| `agent_trace` | **에이전트 타임라인** (Medical → Critic → Scorer → Planner → RPA) |
| `reflection_logs` | Self-Reflection 라운드별 피드백 |
| `risk_score` | 점수·재검토 여부 |
| `rpa_actions` | RPA가 할 작업 문자열 배열 |
| `report_text` | 환자용 리포트 본문 |

### 3-3. 코드 위치 (Agentic AI)

| 파일 | 역할 |
|------|------|
| `app/agents.py` | Medical Agent + **Critic (Self-Reflection)** |
| `app/scoring.py` | 위험도 **점수** (100 − 감점) |
| `app/notifications.py` | 알림 **계획** + `rpa_actions` |
| `app/pipeline.py` | 전체 연결 + **`agent_trace`** 생성 |

**Self-Reflection 핵심 코드 (`agents.py`):**

- 1차: Medical Agent가 `아침 식전 30분` 복약 초안 생성  
- 2차: Critic이 `우유` 경고 + `식전` 충돌 감지 → `식후 2시간`으로 **수정**  
- 3차: `검증 통과`

**점수 (`scoring.py`):**

- 우유/금기 경고 → **−30**  
- 약품명 STT/OCR 불일치 → **−20**  
- 복용 과다 → **−10**  
- **70점 미만** → `재검토_필요: true` → RPA는 환자 알림 **대신** 담당자 플래그

---

## 4. UiPath — Process / Task 구조

UiPath에서 **“Task”**는 보통 아래 둘 중 하나입니다.

| 용어 | 의미 | 우리 프로젝트 |
|------|------|----------------|
| **Process** | `.xaml` 하나 = 자동화 프로그램 전체 | `AtlasMedical_Demo` |
| **Sequence** | Process 안의 단계 블록 | Task 1~3에 해당 |
| Orchestrator **Task** | 사람 승인 대기 등 | **데모에서는 사용 안 함** |

→ 조원에게는 **“Process 1개, Sequence 3개”**라고 말하면 됩니다.

---

## 5. UiPath Process 설계 (Activity 트리)

Studio **Main.xaml** 에 아래 순서로 넣습니다.

```
Main (Sequence)
│
├─ [Task 1] RPA — 데이터 수집
│   ├─ Log Message: "=== TASK 1: RPA Data Collect ==="
│   ├─ Read Text File
│   │     File: E:\...\demo\data\sample_input.json
│   │     Output: jsonRequestBody (String)
│   └─ Log Message: "Collected STT/OCR (mock JSON)"
│
├─ [Task 2] Agentic AI — HTTP 호출
│   ├─ Log Message: "=== TASK 2: Agentic AI Analyze ==="
│   ├─ HTTP Request  (UiPath.Web.Activities)
│   │     Method: POST
│   │     EndPoint: http://localhost:8000/analyze
│   │     Body: jsonRequestBody
│   │     ContentType: application/json
│   │     Result: jsonResponse (String)
│   ├─ Deserialize JSON
│   │     JsonString: jsonResponse
│   │     JsonObject: resultObject (Newtonsoft.Json.Linq.JObject)
│   └─ Assign (변수 추출)
│         patientName = resultObject("analysis")("환자명").ToString
│         reportContent = resultObject("report_text").ToString
│         riskScore = CInt(resultObject("risk_score")("최종점수"))
│         needsReview = CBool(resultObject("risk_score")("재검토_필요"))
│
├─ [Task 2b] Agentic AI — Self-Reflection / 점수 (눈에 보이게)
│   ├─ Log Message: "=== Agentic AI: Self-Reflection ==="
│   ├─ For Each  item In resultObject("reflection_logs")
│   │     Write Line: item("round").ToString + " " + item("critic_feedback").ToString
│   ├─ Log Message: "=== Agentic AI: Risk Score = " + riskScore.ToString
│   └─ For Each  step In resultObject("agent_trace")
│         Write Line: step("agent").ToString + " | " + step("action").ToString
│
├─ [Task 3] RPA — 분기 + 파일 저장
│   ├─ If  needsReview = True
│   │     Message Box: "담당자 재검토 필요 (점수 미달)"
│   │   Else
│   │     Message Box: "환자 알림 채널로 진행 (데모)"
│   ├─ Write Text File
│   │     File: Environment.GetFolderPath(Desktop) + "\" + patientName + "_복약리포트.txt"
│   │     Text: reportContent
│   └─ Log Message: "=== TASK 3 Done ==="
```

---

## 6. UiPath 변수 표 (Variables 패널)

| 변수명 | 타입 | Scope | 기본값/설명 |
|--------|------|-------|-------------|
| `jsonRequestBody` | String | Main | Read Text File 결과 |
| `jsonResponse` | String | Main | HTTP Response |
| `resultObject` | JObject | Main | Deserialize 결과 |
| `patientName` | String | Main | |
| `reportContent` | String | Main | |
| `riskScore` | Int32 | Main | |
| `needsReview` | Boolean | Main | **If 분기 핵심** |
| `apiUrl` | String | Main | `http://localhost:8000/analyze` |

---

## 7. HTTP Request 설정 (스크린샷 대신 체크리스트)

1. **Manage Packages** → `UiPath.Web.Activities` 설치  
2. Activity **HTTP Request** 드래그  
3. 속성:

| Property | Value |
|----------|--------|
| Method | POST |
| EndPoint | `apiUrl` 또는 `http://localhost:8000/analyze` |
| Body | `jsonRequestBody` |
| Headers | Content-Type: application/json |
| Result | `jsonResponse` |

4. F5 전 **반드시** 터미널에서 `uvicorn` 실행 중인지 확인

---

## 8. Deserialize JSON (UiPath)

**방법 A — Deserialize JSON Activity (권장)**

- JsonString: `jsonResponse`  
- JsonObject: `resultObject`  

**방법 B — Assign + Newtonsoft**

```
patientName = resultObject("analysis")("환자명").ToString
```

한글 키(`환자명`, `재검토_필요`) 그대로 사용 가능.

---

## 9. If 분기 두 가지 시연

| JSON 파일 | 예상 `재검토_필요` | Message Box |
|-----------|-------------------|-------------|
| `sample_input.json` | false (70점) | 환자 알림 진행 |
| `sample_input_high_risk.json` | true (50점 등) | 담당자 재검토 |

Read Text File 경로만 바꿔서 F5 두 번 돌리면 **Agentic AI 판단 → RPA 분기**가 보입니다.

---

## 10. 조원에게 줄 “역할·Task” 표

| Task | 담당 기술 | 담당자(예) | 산출물 |
|------|-----------|------------|--------|
| Task 1 수집 | RPA / UiPath | [ ] | STT·OCR → JSON |
| Task 2 분석 | Agentic AI | [ ] | `agents.py`, API |
| Task 2b 검증 | Agentic AI | [ ] | Self-Reflection |
| Task 3 점수 | Agentic AI | [ ] | `scoring.py` |
| Task 4 실행 | RPA / UiPath | [ ] | txt, Excel, 알림 |
| API·배포 | Backend | [ ] | FastAPI, Render |

---

## 11. 과제(13주 설계 코칭) 설정 — 이렇게 말하면 됨

| 과제 항목 | 우리 답 |
|-----------|---------|
| 프로젝트 주제 | 진료 STT + 약봉투 OCR → 복약 안내 자동화 |
| RPA 역할 | JSON 수집, HTTP 호출, 리포트 저장, **점수 기반 If 분기** |
| Agentic AI 역할 | 요약, Self-Reflection, 위험도 점수, **rpa_actions 계획** |
| 연결 구조 | `POST /analyze` JSON → UiPath 변수 → Write File / If |
| 입력 데이터 | JSON (→ Excel DB, STT/OCR API) |
| 예외 처리 | `재검토_필요`, HTTP 실패 Try/Catch, 로그 |
| 결과물 | txt 리포트, Output 패널 로그, Swagger JSON |

---

## 12. 팀장 데모 당일 순서 (10분)

1. **터미널:** `uvicorn app.main:app --port 8000`  
2. **브라우저:** `/docs` → analyze → **`agent_trace`** 보여주기  
3. **UiPath F5:** Read JSON → HTTP → **For Each reflection_logs** → If → Desktop txt  
4. **high_risk JSON**으로 If True 한 번 더  
5. PPT: 노란색 To-Be (STT/OCR, 카톡, Excel)

---

## 13. 한 번에 실행 스크립트

```powershell
cd demo
.\scripts\run_team_demo.ps1
```

일반 + 고위험 샘플 순서로 돌려줍니다.

---

## 14. 자주 하는 실수

| 문제 | 해결 |
|------|------|
| HTTP 연결 실패 | uvicorn 켜져 있는지, URL `localhost:8000` |
| Deserialize 오류 | Response가 HTML이면 서버 안 켜진 것 |
| 한글 깨짐 | Read Text File Encoding UTF-8 |
| If 항상 False | `sample_input_high_risk.json` 사용 |
| Agentic AI 안 보임 | **`agent_trace`**, **`reflection_logs`** For Each 추가 |

---

## 15. 다음 단계 (14주)

- [ ] STT/OCR API 1개 실연동  
- [ ] Excel Write Range  
- [ ] Orchestrator 로그  
- [ ] 카톡 또는 캘린더 1채널  

**13주는 “설계 + mock 연동 증명”이면 충분합니다.**
