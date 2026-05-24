# 4. UiPath 데모 구현 가이드 (팀장 직접 작업)

> Cursor/AI는 `.xaml`을 대신 만들 수 없습니다. 아래 순서대로 Studio에서 따라 하시면 **5~15분 데모**가 완성됩니다.

## 4.1 사전 준비

- [UiPath Studio](https://www.uipath.com/) Community 설치  
- Python API 실행 중 (`uvicorn` 또는 Render URL)  
- `demo/data/sample_input.json` 내용 확인  

---

## 4.2 프로젝트 생성

1. Studio → **New Project** → **Process**  
2. 이름: `AtlasMedical_Demo`  
3. .NET 대상: **Windows** (커뮤니티 기본)

---

## 4.3 Variables (변수) 정의

**Variables 패널**에 추가:

| 이름 | 타입 | 기본값 |
|------|------|--------|
| `apiBaseUrl` | String | `http://localhost:8000` |
| `jsonRequestBody` | String | (비움) |
| `jsonResponse` | String | (비움) |
| `patientName` | String | (비움) |
| `reportPath` | String | `C:\Users\<본인>\Desktop\` |
| `needsReview` | Boolean | False |

---

## 4.4 Sequence 1 — 입력 (RPA 수집 시뮬레이션)

**Activities:**

1. **Input Dialog** (2개 또는 1개에 합침)  
   - Label: `환자명` → Output: `patientName`  
   - Label: `알림매체 (kakao / google_calendar / sms / none)` → 변수 `alertChannel`  

2. **Read Text File**  
   - File: `demo\data\sample_input.json` 전체 경로  
   - Output: `jsonRequestBody`  

3. **Assign** (선택) — 환자명·알림매체만 덮어쓰려면:  
   - 방법 A: 간단 데모는 **Read Text File만** 사용 (JSON에 이미 있음)  
   - 방법 B: `jsonRequestBody`를 Deserialize → 필드 수정 → Serialize (고급)

**발표 멘트:** “실제는 UiPath가 STT/OCR API를 호출해 이 JSON 자리를 채웁니다. 지금은 To-Be Generated 구간입니다.”

---

## 4.5 Sequence 2 — HTTP로 Agentic AI 호출

**Activity: HTTP Request** (UiPath.Web.Activities)

| 속성 | 값 |
|------|-----|
| Method | POST |
| EndPoint | `apiBaseUrl + "/analyze"` → `http://localhost:8000/analyze` |
| Body | `jsonRequestBody` |
| Content-Type | `application/json` |
| Accept | `application/json` |
| Result | `jsonResponse` |

**테스트:** F5 전에 브라우저에서 `/health` 확인.

**Deserialize JSON** (UiPath.Core.Activities 또는 Newtonsoft):

- JsonString: `jsonResponse`  
- JsonObject: `resultObject` (JObject)

**Extract (Assign 예시):**

```
patientName = resultObject("analysis")("환자명").ToString
needsReview = CBool(resultObject("risk_score")("재검토_필요"))
reportContent = resultObject("report_text").ToString
```

*(실제 Studio에서는 **Json Deserialization Activities** 마법사 사용 권장)*

---

## 4.6 Sequence 3 — Self-Reflection / 점수 로그 (시연용)

**Write Line** 여러 개:

```
"=== Self-Reflection ==="
For Each reflection in resultObject("reflection_logs")
  Write Line: round + feedback
"=== Risk Score ===" + resultObject("risk_score")("최종점수")
```

**If** `needsReview = True`:

- **Message Box:** `담당자 재검토 필요 (to_be: 사내 메신저)`  
- Else: **Message Box:** `환자 알림 채널로 진행 (데모)`

---

## 4.7 Sequence 4 — RPA 실행 (리포트·Excel)

### A. 텍스트 리포트 (필수, 쉬움)

**Write Text File**

- File name: `reportPath + patientName + "_복약리포트.txt"`  
- Text: `reportContent`  

### B. Excel (데모용 간단)

**Write Cell** (Workbook 없이 빠르게):

1. **Use Excel Application Scope** 또는 **Workbook Activities**  
2. Create file: `reportPath + patientName + "_복약리포트.xlsx"`  
3. A1: 환자명, A2: 진료요약, A4부터: 복약 리스트 For Each  

또는 **Copy/Paste** from generated txt for minimal demo.

**발표 멘트:** “Excel 템플릿 자동 채우기는 To-Be; 오늘은 HTTP로 받은 JSON을 파일로 증명합니다.”

---

## 4.8 Sequence 5 — 알림 매체 분기 (to_be 연출)

**If Else** on `alertChannel` (또는 response의 `notification_plan.알림매체`):

| 분기 | 데모 동작 |
|------|-----------|
| kakao | Message Box: `카카오 API 예약 (to_be_generated)` |
| google_calendar | Message Box: `캘린더 일정 N건 등록 예약` + Write Line events |
| sms | Message Box: `SMS 발송 예약` |
| else | 리포트만 |

실연동 시: **HTTP Request** to Kakao/Google은 별도 Credential + Orchestrator Asset.

---

## 4.9 Invoke Python (대안 — HTTP 대신)

HTTP가 막히면:

1. **Python Scope** + **Run Python Script**  
2. Script: `demo/run_standalone.py` 경로 실행  
3. stdout 파싱 (비추천 — HTTP가 발표 스토리에 유리)

**권장:** HTTP Request → “RPA와 AI가 분리된 MSA” 설명이 쉬움.

---

## 4.10 Orchestrator 없이 데모 Run

1. Studio에서 **Debug** (F5)  
2. Input Dialog 입력 → HTTP → Desktop에 txt 생성 → Message Box  

Render 배포 시 `apiBaseUrl`만 `https://xxx.onrender.com`으로 변경.

---

## 4.11 Cold Start 대비 (Render)

무료 Render는 15분 idle 후 슬립 → 첫 요청 30~60초 지연.

- 발표 5분 전: 브라우저에서 `/health` 한 번 호출  
- UiPath 첫 HTTP 전 **Delay 60s** (선택) 또는 “AI 서버 기동 중” Message Box

---

## 4.12 체크리스트

- [ ] `/health` 200  
- [ ] `POST /analyze` Swagger에서 성공  
- [ ] UiPath HTTP Result에 `reflection_logs` 보임  
- [ ] Desktop txt 파일 생성  
- [ ] `재검토_필요` True/False 분기 메시지 확인  
- [ ] PPT에 노란색 “To-Be Generated” 라벨
