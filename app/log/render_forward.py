import json
import logging
import os
import socket
from datetime import datetime, timezone

import requests


class RenderForwardHandler(logging.Handler):
    """로컬 실행 로그를 Render Web Service /log/ingest 로 전송."""

    def __init__(self, render_service_url: str, service_name: str) -> None:
        super().__init__()
        self.ingest_url = f"{render_service_url.rstrip('/')}/log/ingest"
        self.service_name = service_name
        self.hostname = socket.gethostname()
        self.ingest_key = os.getenv("RENDER_LOG_INGEST_KEY", "").strip()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = {
                "service": self.service_name,
                "host": self.hostname,
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            headers = {"Content-Type": "application/json"}
            if self.ingest_key:
                headers["X-Log-Ingest-Key"] = self.ingest_key
            requests.post(self.ingest_url, json=payload, headers=headers, timeout=3)
        except Exception:
            # 로깅 실패가 본 요청을 깨지 않도록 무시
            pass
