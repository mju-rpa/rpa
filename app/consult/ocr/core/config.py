import os
from dataclasses import dataclass, field


@dataclass
class OCRConfig:
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
    max_file_size_bytes: int = 20 * 1024 * 1024  # 20MB


ocr_config = OCRConfig()