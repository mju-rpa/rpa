# 팀명: Atlas || Auto카지 — 복약스케줄 자동화

**(OCR + STT) consult → Agentic AI → RPA**

PyCharm / Git 루트 = **이 폴더(`진짜 정리용`)** 입니다.

## 빠른 시작

```bash
pip install -r requirements.txt
cp .env.example .env   # RENDER_* 등 팀 값 입력
python run_standalone.py
uvicorn app.main:app --reload
```

## 디렉터리

| 경로 | 역할 |
|------|------|
| `app/consult/` | 진료 상담 단계 — `ocr/`, `stt/` (팀원 원본) |
| `app/agentic_ai/` | 분석·반성·점수·HIDL |
| `app/workflow/` | `step01`~`step04` 파이프라인 |
| `app/rpa/` | Python 리포트 + UiPath JSON |
| `app/log/` | 로깅·Render 전송 |
| `input/` / `output/` | 샘플 입력 / 산출물 |
| `dev_doc/` | 개발 컨벤션 |
| `guide/` | UiPath·발표 가이드 |
| `api_doc/` | API 설계 문서 |
| `log/` | Render 로그 스냅샷 (CI) |
| `script/` | 데모 PowerShell |

규칙: `dev_doc/convention.md`  
로그 수신: `dev_doc/logging-render.md`
