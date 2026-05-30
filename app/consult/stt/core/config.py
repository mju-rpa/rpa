import os
from dataclasses import dataclass, field


@dataclass
class STTConfig:
    model_size: str = "medium"
    language: str = "ko"
    device: str = "cpu"
    compute_type: str = "int8"
    max_file_size_bytes: int = 150 * 1024 * 1024  # 150MB
    whisper_server_url: str = field(default_factory=lambda: os.getenv("WHISPER_SERVER_URL", "http://localhost:8001"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    clova_invoke_url: str = field(default_factory=lambda: os.getenv("CLOVA_INVOKE_URL", ""))
    clova_secret_key: str = field(default_factory=lambda: os.getenv("CLOVA_SECRET_KEY", ""))
    clova_speaker_count_min: int = int(os.getenv("CLOVA_SPEAKER_COUNT_MIN", "2"))
    clova_speaker_count_max: int = int(os.getenv("CLOVA_SPEAKER_COUNT_MAX", "2"))
    # "local" | "remote" | "openai" | "clova"
    transcriber_type: str = field(default_factory=lambda: os.getenv("TRANSCRIBER_TYPE", "local"))
    retry_threshold: float = field(
        default_factory=lambda: float(os.getenv("STT_RETRY_THRESHOLD", "0.65"))
    )
    hitl_threshold: float = field(
        default_factory=lambda: float(os.getenv("STT_HITL_THRESHOLD", "0.5"))
    )


stt_config = STTConfig()