import logging
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/log", tags=["log"])


class LogIngestBody(BaseModel):
    service: str = "atlas-medical"
    host: str = ""
    level: str = "INFO"
    logger: str = ""
    message: str
    timestamp: str = ""


@router.post("/ingest")
def log_ingest(
    body: LogIngestBody,
    x_log_ingest_key: str | None = Header(default=None, alias="X-Log-Ingest-Key"),
) -> dict[str, Any]:
    """
    로컬 PC에서 전달된 로그를 Render stdout으로 남김 → 대시보드 Logs에서 확인.
    """
    expected = os.getenv("RENDER_LOG_INGEST_KEY", "").strip()
    if expected and x_log_ingest_key != expected:
        raise HTTPException(status_code=401, detail="Invalid log ingest key")

    line = (
        f"[forwarded] host={body.host} level={body.level} "
        f"logger={body.logger} | {body.message}"
    )
    level = body.level.upper()
    if level in ("ERROR", "CRITICAL"):
        logger.error(line)
    elif level == "WARNING":
        logger.warning(line)
    else:
        logger.info(line)

    print(line, flush=True)
    return {"status": "ok"}
