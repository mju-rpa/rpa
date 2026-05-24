# 로그: Render 수집 + 로컬 PC 테스트

## 어디에 무엇을 넣나요? (.env)

| 변수 | 넣을 값 (Render 대시보드) |
|------|---------------------------|
| `RENDER_SERVICE_URL` | Web Service → 상단 **URL** (예: `https://xxx.onrender.com`) |
| `RENDER_LOG_INGEST_KEY` | 팀이 정한 공유 비밀문자열 (임의) — Render **Environment**에도 동일 등록 |
| `RENDER_LOG_FORWARD_ENABLED` | 로컬에서 `true`, Render 서버에서는 `false` |
| `RENDER_OWNER_ID` | GitHub Actions용 — Render **Account** API Owner ID |
| `RENDER_SERVICE_ID` | GitHub Actions용 — Web Service **Settings** → Service ID |
| `RENDER_API_KEY` | GitHub Actions용 — **Account Settings → API Keys** |

`.env.example`에 동일 항목이 `RENDER … 입력` 형태로 있습니다.

---

## 로그가 쌓이는 3가지 경로

### 1) Render에서 API 실행 (권장·시연)

- UiPath / Postman / 팀원이 **Render URL**만 호출
- `print` / `logging` → Render **Logs** 탭에 즉시 표시
- 별도 설정 없음

### 2) 로컬 PC에서 실행 + Render로 전송

1. Render에 최신 코드 배포
2. 로컬 `.env`:
   ```env
   RENDER_SERVICE_URL=https://YOUR-SERVICE.onrender.com
   RENDER_LOG_FORWARD_ENABLED=true
   RENDER_LOG_INGEST_KEY=팀공유시크릿
   ```
3. 로컬 `uvicorn app.main:app` + `POST /demo/pipeline` 또는 `/analyze`
4. 로그가 `POST {RENDER_SERVICE_URL}/log/ingest` 로 전송
5. Render **Logs**에서 `[forwarded] host=팀원PC ...` 확인

**코드 위치**

- 전송: `app/log/render_forward.py`
- 수신: `app/route/log_ingest.py` → stdout → Render Logs

### 3) GitHub Actions 스냅샷 (팀 공유·keep-alive)

- 워크플로: `.github/workflows/fetch-log.yml`
- 결과 파일: `log/render_fetch_snapshot.json`
- Secrets: `RENDER_OWNER_ID`, `RENDER_SERVICE_ID`, `RENDER_API_KEY`

---

## 팀원이 로그 “받는” 방법 요약

| 역할 | 방법 |
|------|------|
| 실시간 | Render 대시보드 → Web Service → **Logs** |
| 로컬 테스트 기여 | `.env`에 `RENDER_LOG_FORWARD_ENABLED=true` + URL/KEY |
| PR/이슈 첨부 | `log/render_fetch_snapshot.json` 최신 커밋 참고 |
| 장애 재현 | Render URL로 동일 요청 재현 (로컬 로그는 보조) |

---

## 보안

- `RENDER_LOG_INGEST_KEY` 없으면 `/log/ingest` 는 공개 POST (데모만). 과제·시연 후 키 설정 권장.
- 환자 실데이터 로그 금지 — `input/` 샘플만.

---

## 한 줄

**Render URL 하나를 팀 공통으로 쓰고, 로컬은 forward 켜면 모든 PC 로그가 Render Logs 한곳에 모입니다.**
