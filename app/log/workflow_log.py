"""워크플로우 단계별 Render/stdout 로그 ([SUCCESS] / [ERROR] / [ADMIN])."""
import logging
from typing import Literal

WorkflowLevel = Literal["SUCCESS", "ERROR", "ADMIN"]

_logger = logging.getLogger("app.workflow")


def workflow_log(level: WorkflowLevel, step: str, message: str) -> None:
    line = f"[{level}] step={step} | {message}"
    if level == "ERROR":
        _logger.error(line)
    elif level == "ADMIN":
        _logger.warning(line)
    else:
        _logger.info(line)
