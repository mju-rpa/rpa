"""
팀원 OCR/STT 원본 import 경로(app.ocr, app.stt) 유지용 alias.
물리 경로는 app/consult/ocr|stt 이지만 코드는 from app.ocr... 를 그대로 씁니다.
"""
import importlib
import sys

# legacy import 이름 → 실제 모듈 경로
_MODULE_MAP: dict[str, str] = {
    "app.ocr": "app.consult.ocr",
    "app.ocr.core": "app.consult.ocr.core",
    "app.ocr.core.config": "app.consult.ocr.core.config",
    "app.ocr.core.extractor": "app.consult.ocr.core.extractor",
    "app.ocr.schema": "app.consult.ocr.api.schema",
    "app.ocr.schema.models": "app.consult.ocr.api.schema.models",
    "app.ocr.route": "app.consult.ocr.api.route",
    "app.ocr.route.router": "app.consult.ocr.api.route.router",
    "app.stt": "app.consult.stt",
    "app.stt.core": "app.consult.stt.core",
    "app.stt.core.config": "app.consult.stt.core.config",
    "app.stt.core.transcriber": "app.consult.stt.core.transcriber",
    "app.stt.schema": "app.consult.stt.api.schema",
    "app.stt.schema.models": "app.consult.stt.api.schema.models",
    "app.stt.route": "app.consult.stt.api.route",
    "app.stt.route.router": "app.consult.stt.api.route.router",
    "app.stt.agents": "app.consult.stt.agents",
    "app.stt.agents.base_agent": "app.consult.stt.agents.base_agent",
}


def register_consult_import_alias() -> None:
    for legacy, target in _MODULE_MAP.items():
        try:
            mod = importlib.import_module(target)
        except ImportError:
            continue
        sys.modules[legacy] = mod
