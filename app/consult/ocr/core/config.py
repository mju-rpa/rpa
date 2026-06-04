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


ocr_config = OCRConfig()