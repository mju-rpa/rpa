import logging
import os
import sys

from app.log.render_forward import RenderForwardHandler


def setup_logging(service_name: str = "atlas-medical") -> None:
    """
    - Render 배포: stdout → Render 대시보드 Logs 탭에 자동 표시
    - 로컬 PC: RENDER_SERVICE_URL 설정 시 동일 로그를 POST /log/ingest 로 전송
    """
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    root.setLevel(level)

    # 중복 핸들러 방지 (uvicorn reload)
    if getattr(root, "_atlas_configured", False):
        return
    root._atlas_configured = True  # type: ignore[attr-defined]

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    root.addHandler(stream)

    forward_url = os.getenv("RENDER_SERVICE_URL", "").strip().rstrip("/")
    if os.getenv("RENDER_LOG_FORWARD_ENABLED", "").lower() in ("1", "true", "yes"):
        if forward_url:
            # ★ [로그가 Render로 날아가도록 핸들러 등록] 이후 demo1_log/workflow_log → render_forward.emit
            root.addHandler(RenderForwardHandler(forward_url, service_name))
        else:
            print(
                "[log] RENDER_LOG_FORWARD_ENABLED=true 이지만 "
                "RENDER_SERVICE_URL=RENDER 서비스 URL 입력 이 비어 있습니다.",
                flush=True,
            )

    logging.getLogger(__name__).info(
        "logging ready (forward=%s)",
        "on" if forward_url and os.getenv("RENDER_LOG_FORWARD_ENABLED") else "off",
    )
