"""
팀원 OCR/STT 원본 import 경로(app.ocr, app.stt) 유지용 alias.
consult/ 하위로 옮긴 뒤에도 from app.ocr.core ... 코드를 수정하지 않음.
"""
import importlib
import sys

_ALIASES = {
    "ocr": (
        "core",
        "core.config",
        "core.extractor",
        "route",
        "route.router",
        "schema",
        "schema.models",
    ),
    "stt": (
        "core",
        "core.config",
        "core.transcriber",
        "route",
        "route.router",
        "schema",
        "schema.models",
        "agents",
        "agents.base_agent",
    ),
}


def register_consult_import_alias() -> None:
    for pkg in _ALIASES:
        consult_root = importlib.import_module(f"app.consult.{pkg}")
        sys.modules[f"app.{pkg}"] = consult_root
        for sub in _ALIASES[pkg]:
            full = f"app.consult.{pkg}.{sub}"
            try:
                mod = importlib.import_module(full)
            except ImportError:
                continue
            sys.modules[f"app.{pkg}.{sub}"] = mod
