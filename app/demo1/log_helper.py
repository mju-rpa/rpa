"""
demo1 전용 로그 — workflow_log와 동일 포맷, consult 모듈 비침범.

[로그가 Render 대시보드로 날아가는 구간]
  demo1_log()  ← 이 함수 호출
    → workflow_log()  (app/log/workflow_log.py)
    → logging.getLogger("app.workflow").info/error(...)
    → root logger handlers:
         1) stdout (로컬 터미널)
         2) RenderForwardHandler  (app/log/configure.py 에서 등록)
              → emit() in app/log/render_forward.py
              → POST {RENDER_SERVICE_URL}/log/ingest  ← ★ 로그 전송 HTTP
    → Render 서버 app/route/log_ingest.py 가 수신 후 stdout → Render Logs 탭

전제: run_cli / uvicorn 시작 시 app.log.configure.setup_logging() 이 호출되어야 함.
      .env: RENDER_LOG_FORWARD_ENABLED=true, RENDER_SERVICE_URL, RENDER_LOG_INGEST_KEY
"""
from app.log.workflow_log import workflow_log


def demo1_log(level: str, step: str, message: str) -> None:
    # ↓ 이 한 줄이 위 체인을 타며, forward 켜져 있으면 Render Logs 로 전송됩니다.
    workflow_log(level, f"demo1/{step}", message)