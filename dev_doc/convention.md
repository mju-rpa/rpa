# 개발 컨벤션 (dev_doc)

> **(OCR + STT) consult → Agentic AI → RPA** 복약스케줄 자동화  
> Git / PyCharm 루트 = 저장소 루트 (`진짜 정리용`)

---

## 1. 디렉터리 명명 (필수)

| 규칙 | 예 |
|------|-----|
| **항상 단수형** | `input`, `output`, `log`, `script`, `guide`, `route`, `schema` |
| 복수 `s` 금지 | ~~`logs`~~ → `log`, ~~`scripts`~~ → `script` |
| `data` 금지 | 샘플·원본 → **`input/`** (`output/` 과 대칭) |

### 문서 분리

| 디렉터리 | 내용 |
|----------|------|
| `dev_doc/` | 팀 개발 규칙·로깅·컨벤션 (본 문서) |
| `api_doc/` | API·모듈 설계 노트 |
| `guide/` | UiPath·발표·배포 가이드 (01~10) |

---

## 2. 저장소 루트

```
진짜 정리용/                 ← Git + PyCharm 루트
├── app/
├── input/
├── output/
├── log/                     ← Render 스냅샷 (CI)
├── script/                  ← 데모 스크립트
├── guide/
├── dev_doc/
├── api_doc/
├── .env.example
├── deploy/env.render.example
└── Procfile
```

---

## 3. `app/` — 워크플로우별 패키지

| 경로 | 워크플로우 단계 | 설명 |
|------|-----------------|------|
| `app/consult/ocr/` | consult | 약봉투 OCR (팀원 원본, **내부 수정 최소**) |
| `app/consult/stt/` | consult | 진료 음성 STT (팀원 원본) |
| `app/route/` | API | FastAPI HTTP (`input_process`, `analyze`, `log_ingest` …) |
| `app/workflow/` | orchestration | step01~04 + `run_pipeline.py` |
| `app/agentic_ai/` | Agentic AI | `agent/`, `self_reflection/`, `scoring/`, `hidl/`, `schema/` |
| `app/rpa/python/` | RPA | txt 리포트 저장 |
| `app/rpa/uipath/` | RPA | flat JSON·액션 문자열 |
| `app/notification/` | 알림 | 알림 **계획** JSON |
| `app/log/` | observability | stdout + Render forward |

### consult + import alias

- 물리 경로: `app/consult/ocr`, `app/consult/stt`
- 코드 import: 팀원 원본은 `from app.ocr...`, `from app.stt...` 유지
- `app/consult_alias.py`가 시작 시 `app.ocr` → `app.consult.ocr` 로 매핑

---

## 4. `app/workflow/` 파일명 규칙

파일명만 보고 단계를 알 수 있게 **`stepNN_역할`** 형식.

| 파일 | 함수 | 단계 |
|------|------|------|
| `step01_collect_convert.py` | `collect_convert` | RPA 수집·AnalyzeRequest |
| `step02_agentic_analyze_reflect_score.py` | `agentic_analyze_reflect_score` | Medical + Reflection + Score |
| `step03_hidl_human_gate.py` | `hidl_human_gate` | HIDL |
| `step04_rpa_notify_output.py` | `rpa_notify_output` | 알림·리포트·UiPath JSON |
| `run_pipeline.py` | `run_pipeline` | 위 단계 연결 |

---

## 5. OCR/STT 모듈 내부

| 하위 | 용도 |
|------|------|
| `route/` | FastAPI 라우터 (~~api~~) |
| `schema/` | Pydantic 모델 (~~schemas~~) |
| `core/` | 추론·설정 |

---

## 6. 환경 변수 (.env)

`.env.example`의 `RENDER … 입력` 주석을 그대로 따라 채웁니다.  
상세: `dev_doc/logging-render.md`

---

## 7. import 치트시트

```python
from app.workflow.run_pipeline import run_pipeline
from app.agentic_ai.schema.models import AnalyzeRequest
from app.consult_alias import register_consult_import_alias  # app/main.py 최상단
```

---

## 8. PyCharm

- **.idea/** — 프로젝트 루트에 **1개만** (하위 `rpa/.idea` 제거됨)
- **Sources Root:** 프로젝트 루트
- **Working directory:** `$ProjectFileDir$`
