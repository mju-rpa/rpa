# UiPath ↔ API JSON 계약

## 엔드포인트

- `POST /analyze` — body: `input/sample_input.json` 형식
- `POST /analyze/file` — multipart JSON 파일

## 응답 flat 키 (Deserialize JSON)

| 키 | 타입 | 용도 |
|----|------|------|
| `patient_name` | string | 환자명 |
| `final_score` | number | 위험도 0–100 |
| `needs_review` | bool | If 분기 (재검토) |
| `hidl_status` | string | `skipped` \| `pending` \| `approved` … |
| `reflection_summary` | string | Write Line 시연 |
| `agent_trace_summary` | string | Write Line 시연 |
| `report_text` | string | txt 저장 |
| `report_file` | string | 로컬 경로 (Python 저장 후) |

## HIDL 시연

```json
{
  "hidl_enabled": true,
  "hidl_approved": null
}
```

→ `workflow_stage: "hidl_pending"`, 환자 알림 스킵.

승인 후 동일 body에 `"hidl_approved": true` 로 재요청.

## RPA 액션

`rpa_actions[]` 문자열 배열 — For Each Write Line (To-Be: 실제 Activity 매핑).
