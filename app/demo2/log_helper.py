"""demo2 로그 — forward 시 Render /log/ingest (app/log/render_forward.py emit)."""
from app.log.workflow_log import workflow_log


def demo2_log(level: str, step: str, message: str) -> None:
    workflow_log(level, f"demo2/{step}", message)
