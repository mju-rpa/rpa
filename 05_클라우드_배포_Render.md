# 5. 무료 클라우드 배포 (AWS·OCI·로컬 제외)

## 5.1 추천 순위

| 서비스 | 적합도 | 무료 특성 | 주의 |
|--------|--------|-----------|------|
| **Render** | ★★★★★ | Web Service 1개, GitHub 자동 배포 | 15분 idle 슬립 |
| **Fly.io** | ★★★★ | 소형 VM 여러 개 | 카드 등록 필요할 수 있음 |
| **Railway** | ★★★ | Trial 크레딧 | 크레딧 소진 후 유료 |
| **PythonAnywhere** | ★★★ | Flask 무료 티어 | 외부 URL 제한 등 |
| **Vercel** | ★★ | Serverless | 장시간 FastAPI 비추 |

**팀 데모 1순위: Render** — `demo/Procfile` + `requirements.txt` 이미 포함.

---

## 5.2 Render 배포 절차

1. GitHub에 `rpa_팀프로젝트` push (루트 또는 `demo`만 repo 루트로)  
2. [render.com](https://render.com) → New **Web Service**  
3. Connect repository  
4. 설정:
   - **Root Directory:** `demo` (모노레포인 경우)  
   - **Build Command:** `pip install -r requirements.txt`  
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`  
   - **Environment:** `LLM_PROVIDER=mock` (기본)  
5. Deploy → URL 예: `https://atlas-medical-demo.onrender.com`  
6. UiPath `apiBaseUrl`을 이 URL로 변경  

---

## 5.3 왜 하이브리드인가 (한 줄)

RPA는 병원 PC·파일·UiPath 라이선스에 묶이고, AI API만 클라우드에 두면 **비용·데모·확장**이 모두 맞습니다.

---

## 5.4 Cold Start 대책

- 크론 외부 핑 (무료 제한 있음) 또는 발표 직전 수동 `/health`  
- 슬립 시 첫 분석 30~60초 — PPT에 “서버 웨이크업” 슬라이드 1장  

---

## 5.5 Fly.io (대안 요약)

```bash
cd demo
fly launch
fly deploy
```

`fly.toml`에서 internal_port = 8080, `uvicorn` 포트 맞춤.

---

## 5.6 보안 (과제 수준)

- API Key 헤더 (`X-API-Key`) — To-Be, Render Environment에 저장  
- HTTPS는 Render 기본 제공  
- 환자 실데이터 업로드 금지 — 샘플만
