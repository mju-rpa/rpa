# 팀명: Atlas || Auto카지 — 복약스케줄 자동화



**(OCR + STT) consult → Agentic AI → RPA**



## 빠른 시작



```bash

pip install -r requirements.txt

cp .env.example .env

uvicorn app.main:app --reload --port 8000

```



- Swagger: http://localhost:8000/docs  

- 샘플 파이프라인: `POST /demo/pipeline?sample=normal` 또는 `?sample=high_risk`  

- UiPath/RPA: `POST /analyze` 또는 `POST /analyze/file`



### 팀원: 개인 PC에서 실행 + Render Logs + 리포트

1. `cp .env.example .env` — `RENDER_SERVICE_URL`, `RENDER_LOG_FORWARD_ENABLED=true`, `RENDER_LOG_INGEST_KEY` 입력  
2. Render 대시보드 **Environment**에 같은 `RENDER_LOG_INGEST_KEY` 등록  
3. 로컬: `uvicorn app.main:app --reload --port 8000` → Swagger는 **http://localhost:8000/docs** (Render `/docs` 아님)  
4. `POST /demo/pipeline` 실행 → 로그는 Render **Logs** (`[forwarded] host=...`), 리포트는 응답 `report_text` + `output/` 폴더  

한 번에: `.\script\run_team_demo.ps1`  

상세: `dev_doc/logging-render.md`



## 디렉터리



| 경로 | 역할 |

|------|------|

| `app/main.py` | FastAPI 진입점 (유일한 실행 구조) |

| `app/consult/` | OCR·STT (팀원 원본) |

| `app/agentic_ai/` | 분석·반성·점수·HIDL (`for_demo/`는 병합 전 스텁 표시) |

| `app/workflow/` | step01~04 + `run_pipeline.py` |

| `app/log/` | `[SUCCESS]`/`[ERROR]`/`[ADMIN]` + Render forward |

| `deploy/` | Render·CI용 env 예시 (루트는 `.env.example`만) |

| `input/` / `output/` | 샘플 / 산출물 |



규칙: `dev_doc/convention.md`

