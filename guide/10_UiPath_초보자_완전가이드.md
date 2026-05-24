# UiPath 초보자 완전 가이드 (클릭·변수·Activity 값까지)

> **결론부터:** `.xaml`은 AI가 100% 대신 만들기 어렵지만,  
> **`rpa/RPA_Example` 프로젝트는 이미 수정해 두었습니다.** Studio에서 **열기 → F5**만 하면 됩니다.  
> 처음부터 직접 만들고 싶으면 **§B**를 따라하세요.

---

## §A. 가장 쉬운 방법 — 만든 프로젝트 열기 (5분)

### A-1. Python API 켜기 (먼저!)

```powershell
cd "e:\5-1\과제제출\rpa_팀프로젝트\demo"
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

브라우저: http://localhost:8000/health  
→ `"status":"ok"` 확인

### A-2. UiPath Studio에서 프로젝트 열기

1. **UiPath Studio** 실행  
2. 왼쪽 **Open** (또는 File → Open)  
3. 폴더 선택:  
   `e:\5-1\과제제출\rpa_팀프로젝트\rpa\RPA_Example`  
4. **Restore Dependencies** / 패키지 설치 창이 뜨면 → **Install**  
5. 왼쪽 **Project** 패널 → **Main.xaml** 더블클릭  

### A-3. json 경로 확인 (한 번만)

캔버스에서 **Read Text File** 클릭 → Properties:

| 속성 | 값 |
|------|-----|
| **File name** | `..\..\demo\data\sample_input.json` |

실행 시 파일 없음 오류 나면 **절대 경로**로 바꿈:

```
e:\5-1\과제제출\rpa_팀프로젝트\demo\data\sample_input.json
```

### A-4. 실행

- 상단 **▶ Run** 또는 **F5**  
- **Output** 패널(하단)에 로그 확인  
- **바탕화면**에 `김철수_복약리포트.txt` 생성  
- **Message Box** 팝업 확인  

### A-5. 성공 화면 체크

Output에 아래가 보이면 **Agentic AI 연동 성공**:

```
=== Self-Reflection ===
Round 1: 아침 식전 복용이 우유...
=== Risk Score = 70 / 100 ===
=== Agent Trace ===
[1] Data Collector | ...
```

---

## §B. 처음부터 직접 만들기 (Studio 화면 기준)

### B-0. 새 프로젝트

1. Studio 시작 화면 → **Process**  
2. 이름: `AtlasMedical_Demo`  
3. **Create**  

---

### B-1. Variables 패널 (하단 Variables 탭)

**Main Sequence** 클릭(가장 바깥 네모) → Variables에 **아래만** 추가:

| Name | Variable type | Scope | Default | 삭제할 것 |
|------|---------------|-------|---------|-----------|
| `jsonRequestBody` | String | Sequence | (비움) | |
| `jsonResponse` | String | Sequence | | |
| `resultObject` | **Newtonsoft.Json.Linq.JObject** | Sequence | | |
| `patientName` | String | Sequence | | |
| `reportContent` | String | Sequence | | |
| `riskScore` | **Int32** | Sequence | | |
| `needsReview` | **Boolean** | Sequence | | |
| `reportFilePath` | String | Sequence | | |
| ~~`item`~~ | ~~Int32~~ | | | **반드시 삭제** |

> `JObject` 타입: Variables → Create Variable → Browse → `Newtonsoft.Json.Linq.JObject`

---

### B-2. Activity 넣는 방법 (공통)

1. **Activities** 패널(왼쪽) 검색  
2. Activity 이름 드래그 → **Main Sequence** 안에 놓기  
3. 순서는 **위에서 아래로** 실행  

---

### B-3. Activity별 Properties (값 그대로 복사)

#### ① Log Message — "TASK 1"

| Property | Value |
|----------|--------|
| Message | `"=== TASK 1: RPA - Read sample JSON ==="` |
| Level | Info |

---

#### ② Read Text File

| Property | Value |
|----------|--------|
| **File name** | `e:\5-1\과제제출\rpa_팀프로젝트\demo\data\sample_input.json` |
| **Content** | `jsonRequestBody` (변수 선택) |

> Content는 **Out** — 파일 내용이 변수에 들어감

---

#### ③ Log Message — "TASK 2"

Message: `"=== TASK 2: Agentic AI - POST /analyze ==="`

---

#### ④ HTTP Request

패키지 없으면: **Manage Packages** → `UiPath.Web.Activities` 설치

| Property | Value |
|----------|--------|
| **Method** | POST |
| **EndPoint** | `http://localhost:8000/analyze` |
| **Body** | `jsonRequestBody` |
| **Body Format** | application/json |
| **Accept Format** | ANY |
| **Result** | `jsonResponse` |
| **Timeout MS** | 60000 |

---

#### ⑤ Deserialize JSON

| Property | Value |
|----------|--------|
| **JsonString** | `jsonResponse` |
| **JsonObject** | `resultObject` |
| **TypeArgument** | Newtonsoft.Json.Linq.JObject |

---

#### ⑥ Multiple Assign

**Edit Assign** 클릭 → 4줄 추가:

| To | Value (표현식) |
|----|----------------|
| `patientName` | `resultObject("patient_name").ToString` |
| `reportContent` | `resultObject("report_text").ToString` |
| `riskScore` | `CInt(resultObject("final_score"))` |
| `needsReview` | `CBool(resultObject("needs_review"))` |

> 표현식 입력: `=` 키 또는 fx 버튼 → **Visual Basic** 모드

---

#### ⑦ Write Line × 3 (TASK 2b — For Each 대신!)

**1번 Write Line — Text:**

```
"=== Self-Reflection ===" + Environment.NewLine + resultObject("reflection_summary").ToString
```

**2번 Write Line — Text:**

```
"=== Risk Score = " + riskScore.ToString + " / 100 ==="
```

**3번 Write Line — Text:**

```
"=== Agent Trace ===" + Environment.NewLine + resultObject("agent_trace_summary").ToString
```

---

#### ⑧ Assign — 리포트 경로

| Property | Value |
|----------|--------|
| To | `reportFilePath` |
| Value | `Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Desktop), patientName + "_복약리포트.txt")` |

---

#### ⑨ Write Text File

| Property | Value |
|----------|--------|
| **File name** | `reportFilePath` |
| **Text** | `reportContent` |

---

#### ⑩ If

| Property | Value |
|----------|--------|
| **Condition** | `needsReview` |

**Then** 안에 → **Message Box**:

- Text: `"담당자 재검토 필요" + Environment.NewLine + "위험도: " + riskScore.ToString + "점"`

**Else** 안에 → **Message Box**:

- Text: `"환자 알림 진행 (데모)" + Environment.NewLine + reportFilePath`

> Then/Else 넣는 법: If 블록 안 **Then** / **Else** 에 Activity 드래그

---

#### ⑪ Log Message — 완료

Message: `"=== ALL TASKS DONE ==="`

---

### B-4. 완성된 Activity 트리

```
Main Sequence
├── Log Message          (TASK 1)
├── Read Text File
├── Log Message          (TASK 2)
├── HTTP Request
├── Deserialize JSON
├── Multiple Assign
├── Write Line           (Self-Reflection)
├── Write Line           (Risk Score)
├── Write Line           (Agent Trace)
├── Assign               (report path)
├── Write Text File
├── If
│   ├── Then → Message Box (재검토)
│   └── Else → Message Box (환자)
└── Log Message          (Done)
```

---

## §C. UiPath 화면 설명 (초보용)

| 화면 | 위치 | 용도 |
|------|------|------|
| **Designer** | 가운데 | Activity 블록 |
| **Activities** | 왼쪽 | Activity 검색·드래그 |
| **Properties** | 오른쪽 | 선택한 Activity 값 입력 |
| **Variables** | 하단 | 변수 이름·타입 |
| **Output** | 하단 | Write Line, Log 결과 |
| **Errors** | 하단 | 빨간 오류 (클릭하면 해당 Activity) |

**표현식 편집:** Properties 값 칸에서 `Ctrl+K` 또는 `fx` → VB 코드 입력

---

## §D. 자주 나는 오류

| 오류 | 원인 | 해결 |
|------|------|------|
| BC30690 Integer 인덱싱 | `item` Int32 + `item("round")` | `item` 변수 **삭제**, Write Line 3개 방식(§B-3⑦) |
| HTTP 실패 | API 안 켜짐 | uvicorn 먼저 실행 |
| Deserialize 실패 | 응답이 HTML | URL·포트 확인 |
| riskScore 타입 오류 | String 변수에 Int 할당 | `riskScore` → **Int32** |
| 파일 없음 | json 경로 틀림 | 절대 경로로 Read Text File |
| `patient_name` 없음 | API 구버전 | uvicorn 재시작, Swagger에서 필드 확인 |

---

## §E. Agentic AI가 UiPath에서 보이는 위치

| 단계 | UiPath에서 보이는 것 | 의미 |
|------|----------------------|------|
| HTTP Request | `jsonResponse` 긴 문자열 | AI가 분석 시작 |
| Deserialize | `resultObject` | JSON 객체 |
| Write Line 1 | `reflection_summary` | **Self-Reflection** |
| Write Line 2 | `riskScore` | **점수 평가** |
| Write Line 3 | `agent_trace_summary` | **에이전트 타임라인** |
| If | Message Box 분기 | **AI 판단 → RPA 실행** |

---

## §F. UiPath가 너무 어려울 때 (백업)

Python만으로 **RPA가 한 일과 동일**하게 보여주기:

```powershell
cd demo
.\scripts\simulate_uipath_rpa.ps1
```

조원에게: *“UiPath는 이 스크립트와 같은 흐름입니다. 발표는 UiPath F5 + 이 로그.”*

---

## §G. 조원에게 줄 말 (30초)

1. **RPA**가 `sample_input.json` 읽고 API 호출  
2. **Agentic AI**가 Self-Reflection·점수 계산  
3. **RPA**가 JSON 보고 txt 저장·재검토 분기  

---

## §H. 체크리스트 (팀장)

- [ ] uvicorn 실행 중  
- [ ] `rpa/RPA_Example` Studio에서 열림  
- [ ] Main.xaml 오류 0개 (Errors 패널)  
- [ ] F5 → Output에 Self-Reflection  
- [ ] 바탕화면 txt 생성  
- [ ] high_risk json → 재검토 Message Box  

---

**프로젝트 파일:** `rpa/RPA_Example/Main.xaml` (수정 완료)  
**표현식만 복사:** `rpa/RPA_Example/표현식_복사용.txt`
