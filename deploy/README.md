# Render / CI 배포 보조

| 파일 | 용도 |
|------|------|
| 루트 `Procfile` | Render Start Command (`uvicorn app.main:app`) |
| 루트 `runtime.txt` | Python 버전 (Render) |
| 루트 `requirements.txt` | `pip install` (Render Build) |
| `env.render.example` | Render Environment + GitHub Actions Secrets |

로컬 개발은 루트 `.env.example` 만 복사하면 됩니다.
