# UiPath TASK 2b — Self-Reflection / 점수 (오류 해결)

스크린샷 오류 `BC30690: Integer 구조체는 인덱싱될 수 없습니다` 원인과 해결입니다.

---

## 오류 원인 (3가지)

### ① `item` 변수 타입이 Int32

Variables 패널에 **`item` = Int32** 로 되어 있으면  
Write Line에서 `item("round")` 를 쓸 때 **숫자에 ["round"]를 붙인 것**처럼 처리되어 오류 납니다.

**해결:** Variables에서 **`item` 변수 삭제**

### ② For Each 루프 변수 이름 불일치

For Each 안 iterator 이름은 **`currentjToken`** 인데  
Write Line에서는 **`item`** 을 쓰고 있습니다 → 다른 변수를 가리킴.

**해결:** Write Line에서 **For Each에 보이는 이름 그대로** 사용  
예: `currentjToken("round")` 또는 아래 §방법 A

### ③ JSON 키 이름이 API와 다름

API는 **한글·중첩 구조**입니다. 스크린샷의 Assign은 영문 키라 값이 비거나 타입이 깨집니다.

| ❌ 스크린샷 (틀림) | ✅ API 실제 키 |
|-------------------|----------------|
| `("patient_name")` | `resultObject("patient_name").ToString` ← **flat (추가됨)** |
| `("report_content")` | `resultObject("report_text").ToString` |
| `CInt(resultObject("risk_score"))` | `resultObject("final_score")` ← **flat (추가됨)** |
| `("needs_review")` | `resultObject("needs_review")` ← **flat (추가됨)** |

**API 서버 재시작** 후 (`uvicorn`) flat 필드가 응답에 포함됩니다.

---

## ★ 방법 A — 가장 쉬움 (For Each 없음, 추천)

TASK 2b를 **Write Line 3개**만으로 끝냅니다.

### Multiple Assign (수정)

```
patientName   = resultObject("patient_name").ToString
reportContent = resultObject("report_text").ToString
riskScore     = CInt(resultObject("final_score"))
needsReview   = CBool(resultObject("needs_review"))
```

변수 타입: `patientName` String, `reportContent` String, **`riskScore` Int32**, **`needsReview` Boolean**

### Write Line 3개

| # | Text (표현식) |
|---|----------------|
| 1 | `"=== Self-Reflection ===" + Environment.NewLine + resultObject("reflection_summary").ToString` |
| 2 | `"=== Risk Score = " + riskScore.ToString` |
| 3 | `"=== Agent Trace ===" + Environment.NewLine + resultObject("agent_trace_summary").ToString` |

**For Each 불필요** — 조원 시연용으로 이 방법이 가장 안정적입니다.

---

## 방법 B — For Each (JToken) 정확한 설정

For Each를 꼭 쓰려면:

### 1) Variables 정리

- **`item` (Int32) 삭제**
- **`currentjToken`** 은 For Each가 만들도록 두거나, 타입을 **JToken**으로

### 2) For Each — reflection_logs

| 속성 | 값 |
|------|-----|
| **Values** | `resultObject("reflection_logs")` |
| **TypeArgument** | `Newtonsoft.Json.Linq.JToken` |
| **Body 변수명** | `reflectionLog` (Properties에서 이름 변경) |

**Write Line Text:**

```
"Round " + reflectionLog("round").ToString + " " + reflectionLog("critic_feedback").ToString
```

TypeArgument가 **Int32 / Object** 이면 다시 같은 오류가 납니다.  
반드시 **Newtonsoft.Json.Linq.JToken** 선택.

### 3) For Each — agent_trace

| 속성 | 값 |
|------|-----|
| **Values** | `resultObject("agent_trace")` |
| **TypeArgument** | `Newtonsoft.Json.Linq.JToken` |
| **Body 변수명** | `traceStep` |

**Write Line Text:**

```
traceStep("agent").ToString + " | " + traceStep("action").ToString
```

### 4) JToken 캐스팅이 필요할 때 (Studio 버전에 따라)

```
CType(reflectionLog, Newtonsoft.Json.Linq.JObject)("round").ToString
```

---

## 방법 C — For Each (문자열 배열, 중간 난이도)

API 응답의 **`reflection_lines`** (문자열 배열) 사용:

| 속성 | 값 |
|------|-----|
| **Values** | `resultObject("reflection_lines")` |
| **TypeArgument** | `String` |

**Write Line:** `line` (루프 변수 그대로)

`agent_trace_lines` 도 동일.

---

## Deserialize JSON 확인

HTTP Request 다음에:

- Activity: **Deserialize JSON**
- JsonString: `jsonResponse`
- JsonObject: `resultObject`
- Type: **Newtonsoft.Json.Linq.JObject**

---

## 체크리스트

- [ ] Variables에서 **`item` (Int32) 삭제**
- [ ] `riskScore` → **Int32**, `needsReview` → **Boolean**
- [ ] Assign에 **`final_score`**, **`needs_review`**, **`patient_name`** 사용
- [ ] API 재시작 후 Swagger에서 `reflection_summary` 필드 확인
- [ ] 방법 A Write Line 3개로 Output 패널에 로그 출력 확인

---

## Swagger로 응답 미리 보기

http://localhost:8000/docs → POST /analyze

응답에 아래가 있어야 UiPath Assign이 동작합니다:

```json
{
  "patient_name": "김철수",
  "final_score": 70,
  "needs_review": false,
  "reflection_summary": "Round 1: ...\nRound 2: ...",
  "agent_trace_summary": "[1] Data Collector | ...",
  "reflection_lines": ["Round 1: ...", "Round 2: ..."]
}
```
