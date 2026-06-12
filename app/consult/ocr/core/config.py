import os
from dataclasses import dataclass, field


@dataclass
class OCRConfig:
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.getenv("OCR_OPENAI_MODEL", "gpt-4o-mini"))
    # "gemini" | "openai"
    extractor_type: str = field(default_factory=lambda: os.getenv("OCR_EXTRACTOR_TYPE", "gemini"))
    max_file_size_bytes: int = 20 * 1024 * 1024  # 20MB
    retry_threshold: float = field(
        default_factory=lambda: float(os.getenv("OCR_RETRY_THRESHOLD", "0.65"))
    )
    hitl_threshold: float = field(
        default_factory=lambda: float(os.getenv("OCR_HITL_THRESHOLD", "0.5"))
    )
    # 흔들림(라플라시안 분산) 정규화 임계값 — 해상도/조명에 민감하므로 샘플로 보정 권장.
    # blur_min 이하=완전 흔들림(선명도 0점), blur_good 이상=선명(만점), 사이는 선형.
    blur_min: float = field(default_factory=lambda: float(os.getenv("OCR_BLUR_MIN", "60")))
    blur_good: float = field(default_factory=lambda: float(os.getenv("OCR_BLUR_GOOD", "300")))


ocr_config = OCRConfig()