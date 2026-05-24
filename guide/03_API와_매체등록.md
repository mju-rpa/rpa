# 3. API & 사용자 매체(캘린더·카톡) 등록

## 3.1 API 설계 (Why REST?)

UiPath ↔ Python 결합도를 낮추기 위해 **JSON over HTTP**만 사용합니다.  
RPA는 “HTTP Request” 하나로 두뇌를 바꿀 수 있습니다.

Base URL (로컬): `http://localhost:8000`  
Base URL (Render): `https://<your-app>.onrender.com`

---

## 3.2 엔드포인트

| Method | Path | 용도 |
|--------|------|------|
| GET | `/health` | UiPath 연결 테스트 |
| GET | `/sample-input` | 예제 payload 확인 |
| POST | `/analyze` | JSON body 분석 (UiPath 권장) |
| POST | `/analyze/file` | JSON 파일 multipart 업로드 |

---

## 3.3 요청 Body (알림 매체 포함)

`demo/data/sample_input.json` 참고:

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
  "stt_text": "...",
  "ocr_text": "..."
}
```

**`알림매체` enum:** `kakao` | `google_calendar` | `sms` | `none`

---

## 3.4 응답에서 RPA가 쓸 필드

```json
{
  "analysis": { "환자명", "진료요약", "필수복약리스트", "상호작용_경고" },
  "risk_score": { "최종점수", "재검토_필요", "재검토_사유" },
  "reflection_logs": [ { "round", "critic_feedback", "revised" } ],
  "notification_plan": {
    "알림매체", "message", "calendar_events": [ { "title", "start", "notes", "status": "to_be_generated" } ]
  },
  "rpa_actions": [ "문자열 목록 — UiPath If/Else 분기 설계용" ],
  "report_text": "txt 내용",
  "report_file": "로컬 저장 경로 (서버 측)"
}
```

---

## 3.5 사용자 매체 정보는 **어디서** 받나?

### 데모 (지금)

- `sample_input.json` 또는 UiPath **Input Dialog**로 `알림매체` + 연락처 입력  
- API가 `notification_plan`만 생성 → **실 발송은 RPA to_be**

### To-Be (운영)

1. **최초 접수:** 구글 폼 / 병원 웹 → `환자_DB.xlsx`  
   - 열: `patient_id`, `알림매체`, `전화번호`, `google_calendar_email`, `카카오_id`  
2. **매일 배치:** UiPath가 DB 읽기 → STT/OCR 수집 → `/analyze`에 DB 행 merge  
3. **분기:**  
   - `재검토_필요` → 담당자 채널  
   - `kakao` → Kakao 비즈메시지 API  
   - `google_calendar` → Google Calendar API (OAuth2 서비스 계정 또는 사용자 동의)  
   - `sms` → SMS 게이트웨이  

### 개인정보

데모·과제에서는 **가짜 번호·이메일**만 사용. 실서비스는 병원 정책·개인정보도 동의 필요.

---

## 3.6 PowerShell 테스트 (발표 전 리허설)

```powershell
$body = Get-Content demo\data\sample_input.json -Raw -Encoding UTF8
Invoke-RestMethod -Uri "http://localhost:8000/analyze" -Method Post -Body $body -ContentType "application/json; charset=utf-8"
```

---

## 3.7 UiPath가 받을 JSON 파일로 저장

HTTP Request 응답 → `Assign` → `Newtonsoft.Json` Deserialize →  
`risk_score.재검토_필요` If → Write Text File / Send Email.

상세는 `04_UiPath_데모_가이드.md`.
